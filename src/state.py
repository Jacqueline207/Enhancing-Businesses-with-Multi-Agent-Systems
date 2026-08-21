"""Shared workflow state.

This module will define the information shared between agents.

A single object that flows through the whole workflow

    Starting at Client Briefing. 1. Parallel research 2. Shared state 3. Writer 4. Critic
    A pass leads to the final output and a fail leads to a retry writer and critic (loop)
    A repeated fail should lead to human review and then a final output

Every agent reads what it needs from this object. It writes its result back to it. 
The orchestrator is the only to assemble inputs and apply outuputs

"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import List, Optional, Literal
import uuid


@dataclass
class SharedState:
    #identification, runs metadata

    """
    create a unique id, generated automatically after a created shared state
    not passed in, usefull for logging
    """
    run_id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    #automated timestamp
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    #input
    """
    clients request is topic, audience, tone, length, required, sections, etc
    Orchestrator.run(client_brief) is read by both research agents, the writer and the critic
    """
    client_brief: dict = field(default_factory=dict)

    #research (filled in parallel before writer is run)
    """
    raw factual sources found by the Source Researcher
    """
    research_sources: List[dict] = field(default_factory=list)

    """
    verified facts pulled from research_sources. The Critic checks Writer's claims against
    and the expected shape should be: [{"fact": str, "source": str}, ...]
    """
    key_facts: List[dict] = field(default_factory=list)

    """
    Audience, tone/angle information from the Context Researcher and the expected shape is:
    {"audience_summary": str, "themes": [...], "suggested_angle": str}
    """
    audience_context: dict = field(default_factory=dict)

    #writer
    """
    The article text produced by the Writer agent (the prompt). Is overwritten on every retry
    with revised draft
    """
    writer_draft: Optional[str] = None

    """
    Which attempt it is. Incremented by the Orchestrator every time the Writer runs
    """
    draft_version: int = 0

    #critic

    """
    pass/fail. Orchestrators retry loop branches on this field
    """
    critic_verdict: Optional[Literal["PASS", "FAIL"]] = None

    """
    plain language list of what is wrong with the draft. Used to show humans during
    escalation and also useful for QA test records
    """
    critic_issues: List[str] = field(default_factory=list)

    """
    what source or client requirements poves each issue real. Used to verify Critic's 
    judgement
    """
    critic_evidence: List[str] = field(default_factory=list)

    """
    the specific instructions for what the Writer should change. Is only set when 
    verdict is FAIL. Orchestrator hands this to run_writer() on next retry in order 
    to target retry
    """
    revision_instructions: Optional[str] = None

    """
    how bad failure is. Can be used for the type of handling action
    """
    severity: Optional[Literal["Mino", "Major", "Critical"]] = None

    """
    Critic's own opinion (if retry is worthwhile). informational only
    """
    critic_retry_flag: Optional[bool] = None

    #retry
    retry_count: int = 0

    """
    once retry_cout reaches 2 (for now) the Orchestrator stops automated retries
    """
    max_retries: int = 2

    #final
    final_status: Optional[Literal[
        "COMPLETED", "HUMAN_REVIEW", "FAILED_MAX_RETRIES"
    ]] = None

    """
    actual deliverable (passing draft or human-review placeholder message if never passed)
    """
    final_output: Optional[str] = None

    def to_dict(self) -> dict:
        """
        A full snapshot of state. logging should be able to dump at any point in the run
        """
        return asdict(self)