"""Context / Angle Researcher agent

produces editorial guidance as context records, does not return research records
and never makes any outside facts
"""

from __future__ import annotations

from src.prompts.context_researcher_prompt import CONTEXT_ANGLE_RESEARCHER_SYSTEM_PROMPT
from src.integrations.ai_gateway import call_agent_json
from src.state import ClientBrief, ContextNote, ContextResearch


def run_context_research(
    client_brief: ClientBrief,
    context_research_request: list[str] | None = None,
) -> ContextResearch:
    context_research_request = context_research_request or []

    result = call_agent_json(
        system_prompt=CONTEXT_ANGLE_RESEARCHER_SYSTEM_PROMPT,
        input_payload={
            "client_brief": client_brief,
            "context_research_request": context_research_request,
        },
    )

    research = result.get("context_research") or {}
    return ContextResearch(
        context_summary=research.get("context_summary", ""),
        context_notes=[ContextNote(**n) for n in research.get("context_notes", [])],
        recommended_outline=research.get("recommended_outline", []),
        source_research_requests=research.get("source_research_requests", []),
    )
