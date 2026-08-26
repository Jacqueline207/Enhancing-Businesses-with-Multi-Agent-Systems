"""
the llm gateway integration

every agent goes through call_agent_json(), which sends the agents system promts
plus it's JSON input payload and parses the JSON input payload and parses the
JSON response

python port targets chat completions endpoint from our DeepSeek backend

LLM_API_KEY -our DeepSeek API Key

also, gateway failures are surfaced exactly (the status and body), so its 
not hidden as a generic error
"""

from __future__ import annotations

import json
import os
import re
from typing import Any

import requests

DEFAULT_MODEL = os.environ.get("LLM_MODEL", "deepseek-chat")
DEFAULT_BASE_URL = os.environ.get("LLM_API_BASE_URL", "https://api.deepseek.com/v1")


class GatewayError(Exception):
    """Raised whenever the LLM call fails or returns something unusable."""

    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status = status
        self.retryable = status == 429 or status >= 500


def _strip_fences(text: str) -> str:
    trimmed = text.strip()
    if not trimmed.startswith("```"):
        return trimmed
    trimmed = re.sub(r"^```(?:json)?\s*", "", trimmed, flags=re.IGNORECASE)
    trimmed = re.sub(r"```\s*$", "", trimmed)
    return trimmed.strip()


def _extract_json(text: str) -> str:
    cleaned = _strip_fences(text)
    first = cleaned.find("{")
    last = cleaned.rfind("}")
    if first == -1 or last == -1 or last <= first:
        return cleaned
    return cleaned[first:last + 1]


def call_agent_json(
    system_prompt: str,
    input_payload: Any,
    model: str | None = None,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """
    Sends system_prompt + input_payload to the configured LLM and parses
    the JSON response. Raises GatewayError on any failure (missing API
    key, network/HTTP error, empty response, or invalid JSON) - callers
    should let this propagate up to the Orchestrator, which already
    wraps agent calls in a try/except and converts any exception into a
    FAILED_MAX_RETRIES run outcome instead of crashing.
    """
    api_key = os.environ.get("LLM_API_KEY")
    if not api_key:
        raise GatewayError(401, "LLM_API_KEY is not configured on the server.")

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
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(input_payload, indent=2, default=str)},
                ],
                "response_format": {"type": "json_object"},
            },
            timeout=timeout,
        )
    except requests.RequestException as exc:
        raise GatewayError(0, f"LLM request failed: {exc}") from exc

    if not response.ok:
        raise GatewayError(
            response.status_code,
            f"LLM gateway request failed [{response.status_code}]: {response.text}",
        )

    try:
        payload = response.json()
    except ValueError as exc:
        raise GatewayError(502, "LLM gateway returned a non-JSON HTTP response.") from exc

    content = (
        payload.get("choices", [{}])[0]
        .get("message", {})
        .get("content")
    )
    if not content:
        raise GatewayError(502, "LLM gateway returned an empty response.")

    try:
        return json.loads(_extract_json(content))
    except json.JSONDecodeError as exc:
        raise GatewayError(
            502,
            f"Agent returned output that is not valid JSON: {content[:800]}",
        ) from exc
