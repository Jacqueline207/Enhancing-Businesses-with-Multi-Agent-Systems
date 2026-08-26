"""Writer agent.

the writer creates initial article and handles revisions requested 
by the Critic. Factual claims must come from source research
and context research is editorial guidance only. The writers only
job is to recieve structured inputs and give them to the model and then
convert the respose into a WriterOutput

also, standardizing the whole project on LLM_API_KEY, LLM_MODEL, and LLM_API_BASE_URL
since we are pointing at DeepSeek

"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from src.integrations.ai_gateway import call_agent_json
from src.prompts.writer_prompt import WRITER_SYSTEM_PROMPT
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
    """feedback passed from the Critic back to the Writer."""

    issues: list[Any]

    revision_instructions: list[
        RevisionInstruction
    ]

    warnings: list[str]


@dataclass
class WriterInput:
    """complete input contract for the Writer."""

    client_brief: ClientBrief

    source_research: Optional[
        SourceResearch
    ]

    context_research: Optional[
        ContextResearch
    ]

    critic_feedback: Optional[
        CriticFeedback
    ]

    retry_count: int


def run_writer(
    writer_input: WriterInput,
) -> WriterOutput:
    """
    run the Writer agent.

    on the first attempt:
        critic_feedback = None
        retry_count = 0

    on a revision:
        critic_feedback contains the Critic's issues
        retry_count > 0
    """

    result = call_agent_json(
        system_prompt=WRITER_SYSTEM_PROMPT,
        input_payload=writer_input,
    )

    return WriterOutput(
        title=result.get(
            "title",
            "",
        ),

        article=result.get(
            "article",
            "",
        ),

        source_claim_ids_used=result.get(
            "source_claim_ids_used",
            [],
        ),

        claim_trace=[
            ClaimTraceEntry(**entry)
            for entry
            in result.get(
                "claim_trace",
                [],
            )
        ],

        requirements_self_check=[
            RequirementSelfCheck(**item)
            for item
            in result.get(
                "requirements_self_check",
                [],
            )
        ],

        unsupported_or_missing_information=(
            result.get(
                "unsupported_or_missing_information",
                [],
            )
        ),

        revision_summary=[
            RevisionSummaryEntry(**item)
            for item
            in result.get(
                "revision_summary",
                [],
            )
        ],
    )