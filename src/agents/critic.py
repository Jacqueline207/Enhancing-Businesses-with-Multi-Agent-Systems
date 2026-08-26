"""Critic / Editor agent.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Any

from src.integrations.ai_gateway import call_agent_json
from src.prompts.critic_prompt import CRITIC_SYSTEM_PROMPT
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


# required critic checks

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


ALLOWED_CHECK_STATUSES = {
    "PASS",
    "FAIL",
    "WARNING",
}

#critic input
@dataclass
class CriticInput:
    client_brief: ClientBrief

    source_research: Optional[
        SourceResearch
    ]

    context_research: Optional[
        ContextResearch
    ]

    writer_output: Optional[
        WriterOutput
    ]


# issue normalization
def _normalize_issue(
    raw: dict[str, Any],
    index: int,
) -> CriticIssue:
    """
    convert raw LLM issue output into a valid CriticIssue.
    """

    severity = raw.get(
        "severity"
    )

    if severity not in {
        "minor",
        "major",
        "critical",
    }:
        severity = "minor"

    issue_type = raw.get(
        "issue_type"
    )

    if issue_type not in ISSUE_TYPES:
        issue_type = "unsupported_claim"

    raw_check_ids = raw.get(
        "check_ids",
        [],
    )

    valid_check_ids = []

    if isinstance(
        raw_check_ids,
        list,
    ):
        for check_id in raw_check_ids:

            if (
                check_id in CHECK_NAMES
                and check_id
                not in valid_check_ids
            ):
                valid_check_ids.append(
                    check_id
                )

    evidence = raw.get(
        "evidence",
        [],
    )

    if not isinstance(
        evidence,
        list,
    ):
        evidence = []

    return CriticIssue(
        issue_id=(
            raw.get("issue_id")
            or f"I-{index + 1:03d}"
        ),

        check_ids=valid_check_ids,

        issue_type=issue_type,

        severity=severity,

        draft_excerpt=str(
            raw.get(
                "draft_excerpt",
                "",
            )
        ),

        evidence=[
            str(item)
            for item in evidence
        ],

        explanation=str(
            raw.get(
                "explanation",
                "",
            )
        ),
    )


#k validation
def _validate_supplied_checks(
    raw_checks: Any,
) -> dict[str, dict]:
    """
    Validate model-supplied K1-K8 records.

    Project A required:
    - valid check ID
    - correct check name
    - valid status
    - no duplicates

    Invalid entries are ignored and rebuilt safely later.
    """

    if not isinstance(
        raw_checks,
        list,
    ):
        return {}

    validated: dict[
        str,
        dict,
    ] = {}

    for raw in raw_checks:

        if not isinstance(
            raw,
            dict,
        ):
            continue

        check_id = raw.get(
            "check_id"
        )

        if check_id not in CHECK_NAMES:
            continue

        # Reject duplicate check IDs.
        if check_id in validated:
            continue

        expected_name = CHECK_NAMES[
            check_id
        ]

        supplied_name = raw.get(
            "check_name"
        )

        if supplied_name != expected_name:
            continue

        status = raw.get(
            "status"
        )

        if (
            status
            not in ALLOWED_CHECK_STATUSES
        ):
            continue

        validated[
            check_id
        ] = {
            "status": status,
            "notes": str(
                raw.get(
                    "notes",
                    "",
                )
            ),
        }

    return validated


def _normalize_checks(
    raw_checks: Any,
    issues: list[CriticIssue],
) -> list[CriticCheck]:
    """
    always return K1-K8 exactly once.

    python enforces the final status based on the
    normalized issues rather than blindly trusting
    the model.
    """

    supplied = (
        _validate_supplied_checks(
            raw_checks
        )
    )

    checks: list[
        CriticCheck
    ] = []

    for (
        check_id,
        check_name,
    ) in CHECK_NAMES.items():

        related_issues = [
            issue
            for issue in issues
            if check_id
            in issue.check_ids
        ]

        has_blocking_issue = any(
            issue.severity
            in {
                "major",
                "critical",
            }
            for issue
            in related_issues
        )

        if has_blocking_issue:
            status = "FAIL"

        elif related_issues:
            # Minor issues are warnings.
            status = "WARNING"

        else:
            supplied_check = supplied.get(
                check_id
            )

            if supplied_check:
                status = supplied_check[
                    "status"
                ]

            else:
                status = "PASS"

        notes = ""

        supplied_check = supplied.get(
            check_id
        )

        if supplied_check:
            notes = supplied_check[
                "notes"
            ]

        checks.append(
            CriticCheck(
                check_id=check_id,
                check_name=check_name,
                status=status,
                notes=notes,
            )
        )

    return checks

# revision instructions
def _normalize_revision_instructions(
    raw_instructions: Any,
    issues: list[CriticIssue],
) -> list[RevisionInstruction]:
    """
    keep only valid revision instructions.

    also guarantees that blocking issues receive
    an actionable instruction.
    """

    instructions: list[
        RevisionInstruction
    ] = []

    if isinstance(
        raw_instructions,
        list,
    ):
        for raw in raw_instructions:

            if not isinstance(
                raw,
                dict,
            ):
                continue

            issue_id = raw.get(
                "issue_id"
            )

            instruction = raw.get(
                "instruction"
            )

            if (
                not issue_id
                or not instruction
            ):
                continue

            instructions.append(
                RevisionInstruction(
                    issue_id=str(
                        issue_id
                    ),
                    instruction=str(
                        instruction
                    ),
                )
            )

    existing_issue_ids = {
        item.issue_id
        for item in instructions
    }

    #every major/critical issue should tell the
    # writer what needs to change.
    for issue in issues:

        if (
            issue.severity
            not in {
                "major",
                "critical",
            }
        ):
            continue

        if (
            issue.issue_id
            in existing_issue_ids
        ):
            continue

        instruction = (
            "Revise the draft to resolve "
            f"{issue.issue_type}: "
            f"{issue.explanation}"
        )

        instructions.append(
            RevisionInstruction(
                issue_id=issue.issue_id,
                instruction=instruction,
            )
        )

    return instructions


# critic execution

def run_critic(
    critic_input: CriticInput,
) -> CriticOutput:
    """
    Run the Critic agent and enforce the workflow's
    QA rules locally.

    The model performs the analysis.

    Python enforces:
    - valid issue types
    - valid severities
    - exactly K1-K8
    - no PASS with major/critical issues
    """

    result = call_agent_json(
        system_prompt=(
            CRITIC_SYSTEM_PROMPT
        ),
        input_payload=critic_input,
    )

    # normalize issues
    raw_issues = result.get(
        "issues",
        [],
    )

    if not isinstance(
        raw_issues,
        list,
    ):
        raw_issues = []

    issues = [
        _normalize_issue(
            raw,
            index,
        )
        for index, raw
        in enumerate(
            raw_issues
        )
        if isinstance(
            raw,
            dict,
        )
    ]

    #enforce pass/fail rules locally
    
    has_blocking_issue = any(
        issue.severity
        in {
            "major",
            "critical",
        }
        for issue in issues
    )

    model_verdict = result.get(
        "verdict"
    )

    if has_blocking_issue:
        verdict = "FAIL"

    elif model_verdict == "FAIL":
        verdict = "FAIL"

    else:
        verdict = "PASS"

    # checks

    checks = _normalize_checks(
        result.get(
            "checks",
            [],
        ),
        issues,
    )

    # revision instructions

    revision_instructions = (
        _normalize_revision_instructions(
            result.get(
                "revision_instructions",
                [],
            ),
            issues,
        )
    )

    # warnings
    warnings = result.get(
        "warnings",
        [],
    )

    if not isinstance(
        warnings,
        list,
    ):
        warnings = []

    warnings = [
        str(warning)
        for warning
        in warnings
    ]

    #minor issues are allowed on PASS,
    # but they must be visible as warnings.
    if (
        verdict == "PASS"
        and issues
    ):

        existing_warnings = set(
            warnings
        )

        for issue in issues:

            if (
                issue.severity
                != "minor"
            ):
                continue

            warning = (
                f"{issue.issue_id} "
                f"({issue.issue_type}): "
                f"{issue.explanation}"
            )

            if (
                warning
                not in existing_warnings
            ):
                warnings.append(
                    warning
                )

                existing_warnings.add(
                    warning
                )

    return CriticOutput(
        verdict=verdict,
        checks=checks,
        issues=issues,
        revision_instructions=(
            revision_instructions
        ),
        warnings=warnings,
    )