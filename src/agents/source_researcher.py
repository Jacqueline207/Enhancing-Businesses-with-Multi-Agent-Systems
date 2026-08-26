"""Source Researcher agent.

collects factual evidence from approved retrieved source material.

The Source Researcher:
- uses the shared AI gateway
- returns a SourceResearch dataclass
- validates claim types and confidence values
- normalizes claim IDs to R-###
- never invents source evidence
"""

from __future__ import annotations

from typing import Any

from src.integrations.ai_gateway import call_agent_json
from src.integrations.research_tools import search_sources
from src.prompts.researcher_prompt import (
    SOURCE_RESEARCHER_SYSTEM_PROMPT,
)
from src.state import (
    ClientBrief,
    SourceClaim,
    SourceResearch,
)


ALLOWED_CLAIM_TYPES = {
    "fact",
    "statistic",
    "quote",
    "date",
    "study_finding",
    "event",
    "causal_claim",
    "attributed_opinion",
}

ALLOWED_CONFIDENCE = {
    "high",
    "medium",
    "low",
}


def run_source_research(
    client_brief: ClientBrief,
    source_research_request: list[str] | None = None,
) -> SourceResearch:
    """
    Run the Source Researcher.

    The external research tool supplies source material.
    The LLM organizes that material into structured claims.

    The function then validates the claims before
    returning SourceResearch.
    """

    source_research_request = (
        source_research_request or []
    )

    missing_information: list[str] = []

    # retreive approved source material

    try:
        retrieved = search_sources(
            client_brief,
            source_research_request,
        )

    except NotImplementedError:
        retrieved = []

        missing_information.append(
            "No external research provider is currently "
            "connected."
        )

    except Exception as exc:
        retrieved = []

        missing_information.append(
            f"Research tool failed: {exc}"
        )

    # ask source researcher agent to organize evidence

    result = call_agent_json(
        system_prompt=SOURCE_RESEARCHER_SYSTEM_PROMPT,
        input_payload={
            "client_brief": client_brief,
            "source_research_request": (
                source_research_request
            ),
            "retrieved_source_material": retrieved,
        },
    )

    research = (
        result.get("source_research")
        or {}
    )

    raw_claims = research.get(
        "claims",
        [],
    )

    claims: list[SourceClaim] = []

    # Map original model IDs to validated R-### IDs.
    id_map: dict[str, str] = {}

    #validating claims

    for index, raw_claim in enumerate(
        raw_claims,
        start=1,
    ):

        if not isinstance(
            raw_claim,
            dict,
        ):
            missing_information.append(
                f"Research item {index} was invalid."
            )
            continue

        claim_type = raw_claim.get(
            "claim_type"
        )

        confidence = raw_claim.get(
            "confidence"
        )

        claim_text = raw_claim.get(
            "claim"
        )

        evidence = raw_claim.get(
            "evidence"
        )

        source_reference = raw_claim.get(
            "source_url_or_reference"
        )

        # claim type validation

        if (
            claim_type
            not in ALLOWED_CLAIM_TYPES
        ):
            missing_information.append(
                f"Research item {index} has an "
                "invalid claim_type."
            )
            continue

        # confidence validation

        if (
            confidence
            not in ALLOWED_CONFIDENCE
        ):
            missing_information.append(
                f"Research item {index} has an "
                "invalid confidence value."
            )
            continue

        # required evidence validation

        if (
            not claim_text
            or not evidence
            or not source_reference
        ):
            missing_information.append(
                f"Research item {index} is missing "
                "claim, evidence, or source reference."
            )
            continue

        uncertainty_note = raw_claim.get(
            "uncertainty_note",
            "",
        )

        # medium/low confidence must explain why.
        if (
            confidence in {
                "medium",
                "low",
            }
            and not uncertainty_note
        ):
            missing_information.append(
                f"Research item {index} requires "
                "an uncertainty_note."
            )
            continue

        # normalize the claim id
        claim_id = (
            f"R-{len(claims) + 1:03d}"
        )

        original_id = str(
            raw_claim.get(
                "claim_id",
                index,
            )
        )

        id_map[original_id] = claim_id

        claims.append(
            SourceClaim(
                claim_id=claim_id,
                claim_type=claim_type,
                claim=claim_text,
                evidence=evidence,
                source_title=raw_claim.get(
                    "source_title",
                    "",
                ),
                source_publisher=raw_claim.get(
                    "source_publisher",
                    "",
                ),
                source_url_or_reference=(
                    source_reference
                ),
                source_date=raw_claim.get(
                    "source_date",
                    "",
                ),
                confidence=confidence,
                uncertainty_note=(
                    uncertainty_note
                ),
                conflicts_with=[],
            )
        )

    # reconnect conflice id's after normalization
    claim_lookup = {
        claim.claim_id: claim
        for claim in claims
    }

    for index, raw_claim in enumerate(
        raw_claims,
        start=1,
    ):

        if not isinstance(
            raw_claim,
            dict,
        ):
            continue

        original_id = str(
            raw_claim.get(
                "claim_id",
                index,
            )
        )

        new_id = id_map.get(
            original_id
        )

        if not new_id:
            continue

        conflicts = raw_claim.get(
            "conflicts_with",
            [],
        )

        mapped_conflicts = []

        if isinstance(
            conflicts,
            list,
        ):
            for conflict_id in conflicts:

                mapped = id_map.get(
                    str(conflict_id)
                )

                if (
                    mapped
                    and mapped != new_id
                    and mapped in claim_lookup
                ):
                    mapped_conflicts.append(
                        mapped
                    )

        claim_lookup[
            new_id
        ].conflicts_with = mapped_conflicts

    # handling missing evidence
    model_missing = research.get(
        "missing_information",
        [],
    )

    if isinstance(
        model_missing,
        list,
    ):
        missing_information.extend(
            str(item)
            for item in model_missing
            if item
        )

    if not claims:
        missing_information.append(
            "No verified source material was "
            "available for factual claims."
        )

    research_summary = research.get(
        "research_summary",
        "",
    )

    if not research_summary:

        research_summary = (
            f"{len(claims)} verified research "
            "claim(s) prepared."
            if claims
            else (
                "No verified research claims "
                "were prepared."
            )
        )

    return SourceResearch(
        research_summary=research_summary,
        claims=claims,
        conflicting_evidence=research.get(
            "conflicting_evidence",
            [],
        ),
        missing_information=(
            missing_information
        ),
    )