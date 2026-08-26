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

        # research (filled in parallel before writer is run)
    source_research: dict = field(default_factory=dict)
    context_research: dict = field(default_factory=dict)

        # writer
    writer_output: dict = field(default_factory=dict)
    draft_version: int = 0
       # critic
    critic_output: dict = field(default_factory=dict)
    critic_verdict: Optional[Literal["PASS", "FAIL"]] = None
    revision_instructions: Optional[str] = None

    # retry
    retry_count: int = 0
    max_retries: int = 2

    # final
    final_status: Optional[
        Literal["COMPLETED", "HUMAN_REVIEW", "FAILED_MAX_RETRIES"]
    ] = None
    final_output: Optional[object] = None

    def to_dict(self) -> dict:
        return asdict(self)