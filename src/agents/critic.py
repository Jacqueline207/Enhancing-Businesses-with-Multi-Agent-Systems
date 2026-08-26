"""Critic / Editor agent."""

import json
import os
from typing import Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from src.prompts.critic_prompt import CRITIC_SYSTEM_PROMPT


EXPECTED_CHECKS = {
    "K1": "factual_grounding",
    "K2": "source_fidelity",
    "K3": "unsupported_claims",
    "K4": "client_requirements",
    "K5": "internal_consistency",
    "K6": "publication_risk",
    "K7": "research_uncertainty",
    "K8": "conflicting_evidence",
}

ALLOWED_CHECK_STATUSES = {"PASS", "FAIL", "WARNING"}


def _empty_critic_output(message: str) -> dict:
    return {
        "verdict": "FAIL",
        "checks": [],
        "issues": [message],
        "evidence": [],
        "revision_instructions": [],
        "severity": "major",
        "warnings": [message],
        "retry": False,
    }


def _validate_checks(checks) -> Optional[list]:
    if not isinstance(checks, list) or len(checks) != 8:
        return None

    seen_ids = set()
    validated_checks = []

    for check in checks:
        if not isinstance(check, dict):
            return None

        check_id = check.get("check_id")
        check_name = check.get("check_name")
        status = check.get("status")
        notes = check.get("notes", "")

        if check_id not in EXPECTED_CHECKS:
            return None

        if check_id in seen_ids:
            return None

        if check_name != EXPECTED_CHECKS[check_id]:
            return None

        if status not in ALLOWED_CHECK_STATUSES:
            return None

        if not isinstance(notes, str):
            notes = str(notes)

        seen_ids.add(check_id)

        validated_checks.append(
            {
                "check_id": check_id,
                "check_name": check_name,
                "status": status,
                "notes": notes,
            }
        )

    if seen_ids != set(EXPECTED_CHECKS):
        return None

    validated_checks.sort(
        key=lambda item: int(item["check_id"][1:])
    )

    return validated_checks


def _validate_critic_output(output: dict) -> dict:
    if not isinstance(output, dict):
        return _empty_critic_output(
            "Critic returned invalid output: expected a dictionary."
        )

    checks = _validate_checks(output.get("checks"))

    if checks is None:
        return _empty_critic_output(
            "Critic returned invalid checks: expected K1 through K8 exactly once."
        )

    verdict = output.get("verdict", "FAIL")
    issues = output.get("issues", [])
    revision_instructions = output.get("revision_instructions", [])
    warnings = output.get("warnings", [])

    if verdict not in {"PASS", "FAIL"}:
        verdict = "FAIL"

    if not isinstance(issues, list):
        issues = []

    if not isinstance(revision_instructions, list):
        revision_instructions = []

    if not isinstance(warnings, list):
        warnings = []

    evidence = []

    for issue in issues:
        if not isinstance(issue, dict):
            continue

        issue_evidence = issue.get("evidence", [])

        if not isinstance(issue_evidence, list):
            continue

        for evidence_item in issue_evidence:
            if evidence_item not in evidence:
                evidence.append(evidence_item)

    if not evidence:
        legacy_evidence = output.get("evidence", [])

        if isinstance(legacy_evidence, list):
            evidence = legacy_evidence

    severity_rank = {
        "minor": 1,
        "major": 2,
        "critical": 3,
    }

    severity = None

    for issue in issues:
        if not isinstance(issue, dict):
            continue

        issue_severity = issue.get("severity")

        if issue_severity not in severity_rank:
            continue

        if (
            severity is None
            or severity_rank[issue_severity] > severity_rank[severity]
        ):
            severity = issue_severity

    legacy_severity = output.get("severity")

    if severity is None and legacy_severity in {
        "minor",
        "major",
        "critical",
    }:
        severity = legacy_severity

    return {
        "verdict": verdict,
        "checks": checks,
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