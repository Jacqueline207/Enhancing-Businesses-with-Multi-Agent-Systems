"""Shared workflow state.

This module will define the information shared between agents.

A single object that flows through the whole workflow

    Starting at Client Briefing. 1. Parallel research 2. Shared state 3. Writer 4. Critic
    A pass leads to the final output and a fail leads to a retry writer and critic (loop)
    A repeated fail should lead to human review and then a final output

Every agent reads what it needs from this object. It writes its result back to it. 
The orchestrator is the only to assemble inputs and apply outuputs

"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional, Literal
import uuid

#adding the shared type definitions, critic issue types, and client brief
Confidence = Literal["high", "medium", "low"]

ClaimType = Literal[
    "fact",
    "statistic",
    "quote",
    "date",
    "study_finding",
    "event",
    "causal_claim",
    "attributed_opinion",
]


ContextCategory = Literal[
    "audience",
    "tone",
    "framing",
    "theme",
    "article_angle",
    "general_context",
]

Severity = Literal[
    "minor",
    "major",
    "critical",
]

CheckStatus = Literal[
    "PASS",
    "FAIL",
    "WARNING",
]


Verdict = Literal[
    "PASS",
    "FAIL",
]

FinalStatus = Literal[
    "COMPLETED",
    "HUMAN_REVIEW",
    "FAILED_MAX_RETRIES",
]

CheckId = Literal[
    "K1",
    "K2",
    "K3",
    "K4",
    "K5",
    "K6",
    "K7",
    "K8",
]


# Critic issue types allowed by the workflow.
ISSUE_TYPES = (
    "unsupported_claim",
    "source_misrepresentation",
    "invented_statistic",
    "invented_quote",
    "invented_source",
    "invented_entity",
    "context_note_used_as_fact",
    "missing_citation_marker",
    "missing_requirement",
    "tone_violation",
    "length_violation",
    "internal_contradiction",
    "uncertainty_misrepresented",
    "conflicting_evidence_mishandled",
    "publication_risk",
)


@dataclass
class ClientBrief:
    topic: str
    audience: str
    tone: str
    length: str

    required_sections: list[str] = field(default_factory=list)

    objective: Optional[str] = None
    format: Optional[str] = None
    special_instructions: Optional[str] = None

# now the source researcher output

@dataclass
class SourceClaim:
    claim_id: str
    claim_type: ClaimType
    claim: str
    evidence: str

    source_title: str = ""
    source_publisher: str = ""
    source_url_or_reference: str = ""
    source_date: str = ""

    confidence: Confidence = "high"
    uncertainty_note: str = ""

    conflicts_with: list[str] = field(default_factory=list)


@dataclass
class SourceResearch:
    research_summary: str = ""

    claims: list[SourceClaim] = field(
        default_factory=list
    )

    conflicting_evidence: list[Any] = field(
        default_factory=list
    )

    missing_information: list[str] = field(
        default_factory=list
    )
#the context researcher output

@dataclass
class ContextNote:
    context_id: str
    category: ContextCategory
    recommendation: str

    rationale: str = ""
    client_brief_reference: str = ""

@dataclass
class ContextResearch:
    context_summary: str = ""

    context_notes: list[ContextNote] = field(
        default_factory=list
    )

    recommended_outline: list[Any] = field(
        default_factory=list
    )

    source_research_requests: list[Any] = field(
        default_factory=list
    )

#writer output

@dataclass
class ClaimTraceEntry:
    draft_excerpt: str
    claim_ids: list[str] = field(default_factory=list)


@dataclass
class RequirementSelfCheck:
    requirement: str
    met: bool
    notes: str = ""


@dataclass
class RevisionSummaryEntry:
    status: Literal[
        "resolved",
        "not_resolved",
        "not_applicable",
    ]

    issue_id: Optional[str] = None
    action: Optional[str] = None
    notes: Optional[str] = None

@dataclass
class WriterOutput:
    title: str = ""
    article: str = ""

    source_claim_ids_used: list[str] = field(
        default_factory=list
    )

    claim_trace: list[ClaimTraceEntry] = field(
        default_factory=list
    )

    requirements_self_check: list[
        RequirementSelfCheck
    ] = field(default_factory=list)

    unsupported_or_missing_information: list[str] = field(
        default_factory=list
    )

    revision_summary: list[
        RevisionSummaryEntry
    ] = field(default_factory=list)

#critic output
@dataclass
class CriticCheck:
    check_id: CheckId
    check_name: str
    status: CheckStatus

    notes: str = ""
@dataclass
class CriticIssue:
    issue_id: str
    check_ids: list[str]
    issue_type: str
    severity: Severity

    draft_excerpt: str = ""
    evidence: list[str] = field(default_factory=list)
    explanation: str = ""


@dataclass
class RevisionInstruction:
    issue_id: str
    instruction: str

@dataclass
class CriticOutput:
    """
    The critic determines whether the draft passes or fails.

    The Critic DOES NOT control:
    - retry_count
    - whether a retry happens
    - human review
    - final status

    Those decisions belong to the orchestrator.
    """

    verdict: Verdict

    checks: list[CriticCheck] = field(
        default_factory=list
    )

    issues: list[CriticIssue] = field(
        default_factory=list
    )

    revision_instructions: list[
        RevisionInstruction
    ] = field(default_factory=list)

    warnings: list[str] = field(
        default_factory=list
    )

#logging

@dataclass
class WorkflowEvent:
    run_id: str
    timestamp: str
    agent: str
    event: str

    extra: Optional[dict[str, Any]] = None


# ***main shared workflow***
@dataclass
class SharedState:

    #run id
    run_id: str = field(
        default_factory=lambda: uuid.uuid4().hex[:8]
    )

    created_at: str = field(
        default_factory=lambda:
        datetime.now(timezone.utc).isoformat()
    )

    # client input
    client_brief: ClientBrief = field(
        default_factory=lambda: ClientBrief(
            topic="",
            audience="",
            tone="",
            length="",
        )
    )

    # parallel research results
    source_research: Optional[
        SourceResearch
    ] = None

    context_research: Optional[
        ContextResearch
    ] = None

    # Writer
    writer_output: Optional[
        WriterOutput
    ] = None

    writer_draft: Optional[str] = None

    draft_version: int = 0

    # Critic
    critic_output: Optional[
        CriticOutput
    ] = None


    critic_verdict: Optional[
        Verdict
    ] = None

    critic_issues: list[
        CriticIssue
    ] = field(default_factory=list)

    critic_evidence: list[str] = field(
        default_factory=list
    )

    revision_instructions: list[
        RevisionInstruction
    ] = field(default_factory=list)

    severity: Optional[
        Severity
    ] = None

    #retry logic
    retry_count: int = 0

    max_retries: int = 2

    #final workflow result
    final_status: Optional[
        FinalStatus
    ] = None

    final_output: Optional[str] = None

    # in-memory workflow log
    events: list[
        WorkflowEvent
    ] = field(default_factory=list)

    def to_dict(self) -> dict:
        """
        Convert the entire workflow state into
        a JSON-serializable dictionary.

        This also allows Project A's existing JSONL
        logger to serialize SharedState.
        """
        return asdict(self)


# Helper functions

def create_shared_state(
    client_brief: ClientBrief,
    max_retries: int = 2,
) -> SharedState:

    return SharedState(
        client_brief=client_brief,
        max_retries=max_retries,
    )


def highest_severity(
    issues: list[CriticIssue],
) -> Optional[Severity]:

    if any(
        issue.severity == "critical"
        for issue in issues
    ):
        return "critical"

    if any(
        issue.severity == "major"
        for issue in issues
    ):
        return "major"

    if any(
        issue.severity == "minor"
        for issue in issues
    ):
        return "minor"

    return None
