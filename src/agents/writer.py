"""Writer agent

produces or revises the article draft, uses research records for factual support and 
client brief facts, context researcher notes are editorial guidance only
writer only reads orchestrator retry count
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from src.prompts.writer_prompt import WRITER_SYSTEM_PROMPT
from src.integrations.ai_gateway import call_agent_json
from src.state import (
    ClaimTraceEntry,
    ClientBrief,
    ContextResearch,
    RequirementSelfCheck,
    RevisionInstruction,
    RevisionSummaryEntry,
    SourceResearch,
    WriterOutput,
)


@dataclass
class CriticFeedback:
    issues: list[Any]
    revision_instructions: list[RevisionInstruction]
    warnings: list[str]


@dataclass
class WriterInput:
    client_brief: ClientBrief
    source_research: Optional[SourceResearch]
    context_research: Optional[ContextResearch]
    critic_feedback: Optional[CriticFeedback]
    retry_count: int


def run_writer(writer_input: WriterInput) -> WriterOutput:
    result = call_agent_json(
        system_prompt=WRITER_SYSTEM_PROMPT,
        input_payload=writer_input,
    )

    return WriterOutput(
        title=result.get("title", ""),
        article=result.get("article", ""),
        source_claim_ids_used=result.get("source_claim_ids_used", []),
        claim_trace=[ClaimTraceEntry(**e) for e in result.get("claim_trace", [])],
        requirements_self_check=[
            RequirementSelfCheck(**r) for r in result.get("requirements_self_check", [])
        ],
        unsupported_or_missing_information=result.get(
            "unsupported_or_missing_information", []
        ),
        revision_summary=[
            RevisionSummaryEntry(**r) for r in result.get("revision_summary", [])
        ],
    )
