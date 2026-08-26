"""Context / Angle Researcher agent."""

from typing import Optional


ALLOWED_CATEGORIES = {
    "audience",
    "tone",
    "framing",
    "theme",
    "article_angle",
    "general_context",
}


def run_context_research(
    client_brief: dict,
    context_research_request: Optional[dict] = None,
) -> dict:
    context_notes = []
    recommended_outline = []
    source_research_requests = []

    if not isinstance(client_brief, dict):
        return {
            "context_research": {
                "context_summary": "",
                "context_notes": [],
                "recommended_outline": [],
                "source_research_requests": [],
            }
        }

    def add_note(
        category: str,
        recommendation: str,
        rationale: str,
        client_brief_reference: str,
    ) -> None:
        if category not in ALLOWED_CATEGORIES or not recommendation:
            return

        context_notes.append(
            {
                "context_id": f"CTX-{len(context_notes) + 1:03d}",
                "category": category,
                "recommendation": recommendation,
                "rationale": rationale,
                "client_brief_reference": client_brief_reference,
            }
        )

    audience = client_brief.get("audience")
    if audience:
        add_note(
            "audience",
            f"Write for the audience described in the client brief: {audience}.",
            "Keeps the article aligned with the requested readership.",
            "audience",
        )

    tone = client_brief.get("tone")
    if tone:
        add_note(
            "tone",
            f"Use the tone requested in the client brief: {tone}.",
            "Keeps the writing style aligned with the client request.",
            "tone",
        )

    objective = client_brief.get("objective")
    if objective:
        add_note(
            "framing",
            f"Frame the article around the stated objective: {objective}.",
            "Keeps the article focused on the intended outcome.",
            "objective",
        )

    topic = client_brief.get("topic")
    if topic:
        add_note(
            "article_angle",
            f"Keep the article centered on the stated topic: {topic}.",
            "Prevents the draft from drifting away from the requested subject.",
            "topic",
        )

    required_sections = client_brief.get("required_sections", [])

    if isinstance(required_sections, str):
        required_sections = [required_sections]

    if isinstance(required_sections, list):
        for section in required_sections:
            if section:
                recommended_outline.append(
                    {
                        "section": str(section),
                        "purpose": "Cover the section required by the client brief.",
                        "context_ids": [],
                    }
                )

    if isinstance(context_research_request, dict):
        category = context_research_request.get("category")
        recommendation = context_research_request.get("recommendation")

        if category in ALLOWED_CATEGORIES and recommendation:
            add_note(
                category,
                str(recommendation),
                str(
                    context_research_request.get(
                        "rationale",
                        "Recommendation supplied in the context research request.",
                    )
                ),
                str(context_research_request.get("client_brief_reference", "")),
            )

        requested_facts = context_research_request.get(
            "source_research_requests",
            [],
        )

        if isinstance(requested_facts, list):
            for request in requested_facts:
                if isinstance(request, dict) and request.get("question"):
                    source_research_requests.append(
                        {
                            "question": str(request["question"]),
                            "reason": str(request.get("reason", "")),
                        }
                    )

    context_summary = (
        f"{len(context_notes)} editorial context note(s) prepared."
        if context_notes
        else "No editorial context notes were prepared."
    )

    return {
        "context_research": {
            "context_summary": context_summary,
            "context_notes": context_notes,
            "recommended_outline": recommended_outline,
            "source_research_requests": source_research_requests,
        }
    }