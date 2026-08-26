"""Context / Angle Researcher agent.

it produces editorial guidance for the Writer.

Context Research:
- guides audience, tone, framing, and organization
- does NOT provide factual evidence
- never creates R-### research records
"""

from __future__ import annotations

from src.integrations.ai_gateway import (
    call_agent_json,
)
from src.prompts.context_researcher_prompt import (
    CONTEXT_ANGLE_RESEARCHER_SYSTEM_PROMPT,
)
from src.state import (
    ClientBrief,
    ContextNote,
    ContextResearch,
)


ALLOWED_CATEGORIES = {
    "audience",
    "tone",
    "framing",
    "theme",
    "article_angle",
    "general_context",
}


def run_context_research(
    client_brief: ClientBrief,
    context_research_request: list[str] | None = None,
) -> ContextResearch:
    """
    run the Context / Angle Researcher.

    this agent provides editorial guidance only.
    it must never create factual source evidence.
    """

    context_research_request = (
        context_research_request or []
    )

    result = call_agent_json(
        system_prompt=(
            CONTEXT_ANGLE_RESEARCHER_SYSTEM_PROMPT
        ),
        input_payload={
            "client_brief": client_brief,
            "context_research_request": (
                context_research_request
            ),
        },
    )

    research = (
        result.get("context_research")
        or {}
    )

    raw_notes = research.get(
        "context_notes",
        [],
    )

    context_notes: list[
        ContextNote
    ] = []

    # validating context notes

    for index, note in enumerate(
        raw_notes,
        start=1,
    ):

        if not isinstance(
            note,
            dict,
        ):
            continue

        category = note.get(
            "category"
        )

        recommendation = note.get(
            "recommendation"
        )

        if (
            category
            not in ALLOWED_CATEGORIES
        ):
            continue

        if not recommendation:
            continue

        # normalize CTX identifier instead of
        # blindly trusting the model's ID.
        context_id = (
            f"CTX-{len(context_notes) + 1:03d}"
        )

        context_notes.append(
            ContextNote(
                context_id=context_id,
                category=category,
                recommendation=str(
                    recommendation
                ),
                rationale=str(
                    note.get(
                        "rationale",
                        "",
                    )
                ),
                client_brief_reference=str(
                    note.get(
                        "client_brief_reference",
                        "",
                    )
                ),
            )
        )

    context_summary = research.get(
        "context_summary",
        "",
    )

    if not context_summary:

        context_summary = (
            f"{len(context_notes)} editorial "
            "context note(s) prepared."
            if context_notes
            else (
                "No editorial context notes "
                "were prepared."
            )
        )

    return ContextResearch(
        context_summary=context_summary,

        context_notes=context_notes,

        recommended_outline=research.get(
            "recommended_outline",
            [],
        ),

        source_research_requests=research.get(
            "source_research_requests",
            [],
        ),
    )