"""Source Researcher agent
collects factual evedince in proper records and never returns context research records
"""

from __future__ import annotations

from src.prompts.researcher_prompt import SOURCE_RESEARCHER_SYSTEM_PROMPT
from src.integrations.ai_gateway import call_agent_json
from src.integrations.research_tools import search_sources
from src.state import ClientBrief, SourceClaim, SourceResearch


def run_source_research(
    client_brief: ClientBrief,
    source_research_request: list[str] | None = None,
) -> SourceResearch:
    source_research_request = source_research_request or []
    retrieved = search_sources(client_brief, source_research_request)

    result = call_agent_json(
        system_prompt=SOURCE_RESEARCHER_SYSTEM_PROMPT,
        input_payload={
            "client_brief": client_brief,
            "source_research_request": source_research_request,
            "retrieved_source_material": retrieved,
        },
    )

    research = result.get("source_research") or {}
    return SourceResearch(
        research_summary=research.get("research_summary", ""),
        claims=[SourceClaim(**c) for c in research.get("claims", [])],
        conflicting_evidence=research.get("conflicting_evidence", []),
        missing_information=research.get("missing_information", []),
    )