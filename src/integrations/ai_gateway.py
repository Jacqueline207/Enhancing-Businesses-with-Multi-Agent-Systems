"""Central LLM gateway used by all agents.

every agent sends:
- its system prompt
- a JSON-compatible input payload

the gateway:
- loads environment variables
- calls the configured LLM
- requires JSON output
- parses the response
- raises a clear GatewayError when something goes wrong
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import asdict, is_dataclass
from typing import Any

import requests
from dotenv import load_dotenv


# Load variables from a local .env file.
load_dotenv()


DEFAULT_MODEL = os.getenv(
    "LLM_MODEL",
    "deepseek-chat",
)

DEFAULT_BASE_URL = os.getenv(
    "LLM_API_BASE_URL",
    "https://api.deepseek.com/v1",
)


class GatewayError(Exception):
    """raised when an LLM request or response fails."""

    def __init__(
        self,
        status: int,
        message: str,
    ):
        super().__init__(message)

        self.status = status

        # useful later if the orchestrator needs
        # to decide whether an API failure can retry.
        self.retryable = (
            status == 429
            or status >= 500
            or status == 0
        )


def _serialize(value: Any) -> Any:
    """
    convert dataclasses and nested Python objects
    into JSON-compatible values.
    """

    if is_dataclass(value):
        return {
            key: _serialize(item)
            for key, item in asdict(value).items()
        }

    if isinstance(value, dict):
        return {
            str(key): _serialize(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [
            _serialize(item)
            for item in value
        ]

    return value


def _strip_fences(text: str) -> str:
    """
    remove Markdown code fences if the model returns:

    ```json
    {...}
    ```
    """

    cleaned = text.strip()

    if not cleaned.startswith("```"):
        return cleaned

    cleaned = re.sub(
        r"^```(?:json)?\s*",
        "",
        cleaned,
        flags=re.IGNORECASE,
    )

    cleaned = re.sub(
        r"```\s*$",
        "",
        cleaned,
    )

    return cleaned.strip()


def _extract_json(text: str) -> str:
    """
    attempt to isolate the JSON object from
    surrounding model text.
    """

    cleaned = _strip_fences(text)

    first = cleaned.find("{")
    last = cleaned.rfind("}")

    if (
        first == -1
        or last == -1
        or last <= first
    ):
        return cleaned

    return cleaned[first:last + 1]


def call_agent_json(
    system_prompt: str,
    input_payload: Any,
    model: str | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """
    call the configured LLM and require a JSON response.

    agents should use this function rather than
    creating their own API requests.
    """

    api_key = os.getenv("LLM_API_KEY")

    if not api_key:
        raise GatewayError(
            401,
            "LLM_API_KEY is not configured. "
            "Add it to your .env file.",
        )

    payload = _serialize(input_payload)

    try:
        response = requests.post(
            f"{DEFAULT_BASE_URL}/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}",
            },
            json={
                "model": model or DEFAULT_MODEL,
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt,
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            payload,
                            indent=2,
                            ensure_ascii=False,
                        ),
                    },
                ],
                "response_format": {
                    "type": "json_object"
                },
            },
            timeout=timeout,
        )

    except requests.RequestException as exc:
        raise GatewayError(
            0,
            f"LLM request failed: {exc}",
        ) from exc

    if not response.ok:
        raise GatewayError(
            response.status_code,
            (
                "LLM gateway request failed "
                f"[{response.status_code}]: "
                f"{response.text}"
            ),
        )

    try:
        response_payload = response.json()

    except ValueError as exc:
        raise GatewayError(
            502,
            "LLM returned a non-JSON HTTP response.",
        ) from exc

    try:
        content = (
            response_payload["choices"][0]
            ["message"]["content"]
        )

    except (
        KeyError,
        IndexError,
        TypeError,
    ) as exc:
        raise GatewayError(
            502,
            "LLM response did not contain "
            "choices[0].message.content.",
        ) from exc

    if not content:
        raise GatewayError(
            502,
            "LLM returned an empty response.",
        )

    try:
        parsed = json.loads(
            _extract_json(content)
        )

    except json.JSONDecodeError as exc:
        raise GatewayError(
            502,
            (
                "Agent returned invalid JSON. "
                f"Response began with: {content[:500]}"
            ),
        ) from exc

    if not isinstance(parsed, dict):
        raise GatewayError(
            502,
            "Agent JSON response must be an object.",
        )

    return parsed