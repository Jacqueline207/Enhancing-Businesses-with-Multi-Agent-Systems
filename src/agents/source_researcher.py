"""Source Researcher agent."""

from typing import Any, Optional

from src.integrations.research_tools import search_sources


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

ALLOWED_CONFIDENCE = {"high", "medium", "low"}


def run_source_research(
    client_brief: dict,
    research_request: Optional[dict] = None,
    retrieved_source_material: Optional[Any] = None,
) -> dict:
    missing_information = []

    if not isinstance(client_brief, dict):
        return {
            "source_research": {
                "research_summary": "",
                "claims": [],
                "conflicting_evidence": [],
                "missing_information": ["Invalid client_brief: expected a dictionary."],
            }
        }

    material = retrieved_source_material

    if material is None:
        query_parts = []

        if isinstance(research_request, dict):
            request_text = research_request.get("query") or research_request.get("request")
            if request_text:
                query_parts.append(str(request_text))

        for key in ("topic", "objective"):
            value = client_brief.get(key)
            if value:
                query_parts.append(str(value))

        query = " ".join(query_parts).strip()

        if query:
            try:
                material = search_sources(query)
            except (NotImplementedError, Exception):
                material = None

    if isinstance(material, dict):
        raw_claims = material.get("claims", [])
        raw_conflicts = material.get("conflicting_evidence", [])
    elif isinstance(material, list):
        raw_claims = material
        raw_conflicts = []
    else:
        raw_claims = []
        raw_conflicts = []

    claims = []
    id_map = {}

    for index, raw_claim in enumerate(raw_claims, start=1):
        if not isinstance(raw_claim, dict):
            missing_information.append(
                f"Research item {index} was invalid and was not converted into a claim."
            )
            continue

        claim_type = raw_claim.get("claim_type")
        confidence = raw_claim.get("confidence")
        claim_text = raw_claim.get("claim")
        evidence = raw_claim.get("evidence")
        source_reference = raw_claim.get("source_url_or_reference")

        if claim_type not in ALLOWED_CLAIM_TYPES:
            missing_information.append(
                f"Research item {index} has a missing or invalid claim_type."
            )
            continue

        if confidence not in ALLOWED_CONFIDENCE:
            missing_information.append(
                f"Research item {index} has a missing or invalid confidence value."
            )
            continue

        if not claim_text or not evidence or not source_reference:
            missing_information.append(
                f"Research item {index} is missing claim, evidence, or source reference."
            )
            continue

        uncertainty_note = raw_claim.get("uncertainty_note", "")

        if confidence in {"medium", "low"} and not uncertainty_note:
            missing_information.append(
                f"Research item {index} requires an uncertainty_note."
            )
            continue

        claim_id = f"R-{len(claims) + 1:03d}"
        original_id = str(raw_claim.get("claim_id", index))
        id_map[original_id] = claim_id

        claims.append(
            {
                "claim_id": claim_id,
                "claim_type": claim_type,
                "claim": claim_text,
                "evidence": evidence,
                "source_title": raw_claim.get("source_title", ""),
                "source_publisher": raw_claim.get("source_publisher", ""),
                "source_url_or_reference": source_reference,
                "source_date": raw_claim.get("source_date", ""),
                "confidence": confidence,
                "uncertainty_note": uncertainty_note,
                "conflicts_with": [],
            }
        )

    valid_claim_ids = {claim["claim_id"] for claim in claims}

    for index, raw_claim in enumerate(raw_claims, start=1):
        original_id = str(raw_claim.get("claim_id", index)) if isinstance(raw_claim, dict) else ""
        new_id = id_map.get(original_id)

        if not new_id:
            continue

        conflicts = raw_claim.get("conflicts_with", [])
        mapped_conflicts = []

        if isinstance(conflicts, list):
            for conflict_id in conflicts:
                mapped = id_map.get(str(conflict_id))
                if mapped and mapped in valid_claim_ids and mapped != new_id:
                    mapped_conflicts.append(mapped)

        for claim in claims:
            if claim["claim_id"] == new_id:
                claim["conflicts_with"] = mapped_conflicts
                break

    conflicting_evidence = []

    if isinstance(raw_conflicts, list):
        for item in raw_conflicts:
            if not isinstance(item, dict):
                continue

            mapped_ids = [
                id_map[str(claim_id)]
                for claim_id in item.get("claim_ids", [])
                if str(claim_id) in id_map
            ]

            if mapped_ids:
                conflicting_evidence.append(
                    {
                        "topic": item.get("topic", ""),
                        "claim_ids": mapped_ids,
                        "explanation": item.get("explanation", ""),
                    }
                )

    if not claims:
        missing_information.append(
            "No verified source material was available for factual claims."
        )

    research_summary = (
        f"{len(claims)} verified research claim(s) prepared."
        if claims
        else "No verified research claims were prepared."
    )

    return {
        "source_research": {
            "research_summary": research_summary,
            "claims": claims,
            "conflicting_evidence": conflicting_evidence,
            "missing_information": missing_information,
        }
    }