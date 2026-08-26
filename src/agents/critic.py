"""Critic / Editor agent."""

import json
import os
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.prompts.critic_prompt import CRITIC_SYSTEM_PROMPT


def _empty_critic_output(message: str) -> dict:
    return {
        "verdict": "FAIL",
        "issues": [message],
        "evidence": [],
        "revision_instructions": [],
        "severity": "major",
        "warnings": [message],
        "retry": False,
    }


def _validate_critic_output(output: dict) -> dict:
    if not isinstance(output, dict):
        return _empty_critic_output(
            "Critic returned invalid output: expected a dictionary."
        )

    verdict = output.get("verdict", "FAIL")
    issues = output.get("issues", [])
    evidence = output.get("evidence", [])
    revision_instructions = output.get("revision_instructions", [])
    severity = output.get("severity")
    warnings = output.get("warnings", [])

    if verdict not in {"PASS", "FAIL"}:
        verdict = "FAIL"

    if not isinstance(issues, list):
        issues = []

    if not isinstance(evidence, list):
        evidence = []

    if not isinstance(revision_instructions, list):
        revision_instructions = []

    if severity not in {"minor", "major", "critical", None}:
        severity = "major"

    if not isinstance(warnings, list):
        warnings = []

    return {
        "verdict": verdict,
        "issues": issues,
        "evidence": evidence,
        "revision_instructions": revision_instructions,
        "severity": severity,
        "warnings": warnings,
        "retry": verdict == "FAIL",
    }


def _call_model(critic_input: dict) -> Optional[dict]:
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("OPENAI_MODEL")

    if not api_key or not model:
        return None

    api_url = os.getenv(
        "OPENAI_API_URL",
        "https://api.openai.com/v1/chat/completions",
    )

    messages = [
        {
            "role": "system",
            "content": CRITIC_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": json.dumps(critic_input, ensure_ascii=False),
        },
    ]

    payload = {
        "model": model,
        "messages": messages,
        "response_format": {"type": "json_object"},
    }

    request = Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=60) as response:
            response_data = json.loads(response.read().decode("utf-8"))
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError):
        return None

    try:
        content = response_data["choices"][0]["message"]["content"]
        return json.loads(content)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError):
        return None


def run_critic(
    critic_input: dict,
    model_output: Optional[dict] = None,
) -> dict:
    if not isinstance(critic_input, dict):
        return _empty_critic_output(
            "Invalid critic_input: expected a dictionary."
        )

    required_inputs = (
        "client_brief",
        "source_research",
        "context_research",
        "writer_output",
    )

    missing_inputs = [
        name
        for name in required_inputs
        if name not in critic_input
    ]

    if missing_inputs:
        return _empty_critic_output(
            "Critic input is missing: " + ", ".join(missing_inputs)
        )

    if model_output is None:
        model_output = _call_model(critic_input)

    if model_output is None:
        return _empty_critic_output(
            "Critic model is not configured or did not return valid JSON."
        )

    return _validate_critic_output(model_output)