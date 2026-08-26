"""Writer agent."""

import json
import os
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.prompts.writer_prompt import WRITER_SYSTEM_PROMPT


def _empty_writer_output(message: str) -> dict:
    return {
        "article": "",
        "source_claim_ids_used": [],
        "claim_trace": [],
        "requirements_self_check": [],
        "unsupported_or_missing_information": [message],
        "revision_summary": [],
    }


def _validate_writer_output(output: dict) -> dict:
    if not isinstance(output, dict):
        return _empty_writer_output(
            "Writer returned invalid output: expected a dictionary."
        )

    article = output.get("article", "")
    source_claim_ids_used = output.get("source_claim_ids_used", [])
    claim_trace = output.get("claim_trace", [])
    requirements_self_check = output.get("requirements_self_check", [])
    unsupported_or_missing_information = output.get(
        "unsupported_or_missing_information",
        [],
    )
    revision_summary = output.get("revision_summary", [])

    if not isinstance(article, str):
        article = ""

    if not isinstance(source_claim_ids_used, list):
        source_claim_ids_used = []

    if not isinstance(claim_trace, list):
        claim_trace = []

    if not isinstance(requirements_self_check, list):
        requirements_self_check = []

    if not isinstance(unsupported_or_missing_information, list):
        unsupported_or_missing_information = []

    if not isinstance(revision_summary, list):
        revision_summary = []

    return {
        "article": article,
        "source_claim_ids_used": source_claim_ids_used,
        "claim_trace": claim_trace,
        "requirements_self_check": requirements_self_check,
        "unsupported_or_missing_information": unsupported_or_missing_information,
        "revision_summary": revision_summary,
    }


def _call_model(writer_input: dict) -> Optional[dict]:
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
            "content": WRITER_SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": json.dumps(writer_input, ensure_ascii=False),
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


def run_writer(
    writer_input: dict,
    model_output: Optional[dict] = None,
) -> dict:
    if not isinstance(writer_input, dict):
        return _empty_writer_output(
            "Invalid writer_input: expected a dictionary."
        )

    required_inputs = (
        "client_brief",
        "source_research",
        "context_research",
    )

    missing_inputs = [
        name
        for name in required_inputs
        if name not in writer_input
    ]

    if missing_inputs:
        return _empty_writer_output(
            "Writer input is missing: " + ", ".join(missing_inputs)
        )

    if model_output is None:
        model_output = _call_model(writer_input)

    if model_output is None:
        return _empty_writer_output(
            "Writer model is not configured or did not return valid JSON."
        )

    return _validate_writer_output(model_output)