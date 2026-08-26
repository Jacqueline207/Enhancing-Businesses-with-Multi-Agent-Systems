"""Critic / Editor agent

runs checks k1-k8 and returns exactly pass or fail. judges quality only
routing, retry_count, escalation, and final_status belong to the Orchestrator

the severity rule enforced in code. any major or critical issue can never come back
as pass. even if the LLM returns a pass verdict
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.prompts.critic_prompt import CRITIC_SYSTEM_PROMPT
from src.integrations.ai_gateway import call_agent_json
from src.state import (
    ClientBrief,
    ContextResearch,
    CriticCheck,
    CriticIssue,
    CriticOutput,
    ISSUE_TYPES,
    RevisionInstruction,
    SourceResearch,
    WriterOutput,
)

CHECK_NAMES: dict[str, str] = {
    "K1": "factual_grounding",
    "K2": "source_fidelity",
    "K3": "unsupported_claims",
    "K4": "client_requirements",
    "K5": "internal_consistency",
    "K6": "publication_risk",
    "K7": "research_uncertainty",
    "K8": "conflicting_evidence",
}


@dataclass
class CriticInput:
    client_brief: ClientBrief
    source_research: Optional[SourceResearch]
    context_research: Optional[ContextResearch]
    writer_output: Optional[WriterOutput]


def _normalize_issue(raw: dict, index: int) -> CriticIssue:
    severity = raw.get("severity")
    if severity not in ("critical", "major"):
        severity = "minor"

    issue_type = raw.get("issue_type")
    if issue_type not in ISSUE_TYPES:
        issue_type = "unsupported_claim"

    return CriticIssue(
        issue_id=raw.get("issue_id") or f"I-{index + 1:03d}",
        check_ids=raw.get("check_ids", []),
        issue_type=issue_type,
        severity=severity,
        draft_excerpt=raw.get("draft_excerpt", ""),
        evidence=raw.get("evidence", []),
        explanation=raw.get("explanation", ""),
    )


def _normalize_checks(raw_checks: list[dict], issues: list[CriticIssue]) -> list[CriticCheck]:
    checks: list[CriticCheck] = []
    for check_id, check_name in CHECK_NAMES.items():
        supplied = next((c for c in raw_checks if c.get("check_id") == check_id), None)
        related = [i for i in issues if check_id in i.check_ids]
        blocking = any(i.severity in ("major", "critical") for i in related)

        if blocking:
            status = "FAIL"
        elif related:
            status = "WARNING"
        else:
            status = (supplied or {}).get("status", "PASS")

        checks.append(CriticCheck(
            check_id=check_id,
            check_name=check_name,
            status=status,
            notes=(supplied or {}).get("notes", ""),
        ))
    return checks

def run_critic(critic_input: CriticInput) -> CriticOutput:
    result = call_agent_json(
        system_prompt=CRITIC_SYSTEM_PROMPT,
        input_payload=critic_input,
    )

    raw_issues = result.get("issues", [])
    issues = [_normalize_issue(raw, i) for i, raw in enumerate(raw_issues)]
    blocking = any(i.severity in ("major", "critical") for i in issues)

    # Enforced locally: a major or critical issue is never a PASS,
    # regardless of what verdict the LLM call itself returned.
    verdict = "FAIL" if (blocking or result.get("verdict") == "FAIL") else "PASS"

    warnings = list(result.get("warnings", []))
    if verdict == "PASS" and issues and not warnings:
        warnings = [f"{i.issue_id} ({i.issue_type}): {i.explanation}" for i in issues]

    return CriticOutput(
        verdict=verdict,
        checks=_normalize_checks(result.get("checks", []), issues),
        issues=issues,
        revision_instructions=[
            RevisionInstruction(**r) for r in result.get("revision_instructions", [])
        ],
        warnings=warnings,
    )
