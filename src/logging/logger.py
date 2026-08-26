"""
structured logging for the multi-agent workflow

one event is one record and events are appended to state.events which
is the run's full log

the events names in use across the workflow:

run_start, research_start, research_complete, writer_start, writer_complete,
critic_start, critic_complete, retry_triggered, max_retries_reached, human_review_flagged
pass_final_output, run_end, agent_error
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from src.state import SharedState, WorkflowEvent

EventEmitter = Callable[[WorkflowEvent], None]

_emitters: dict[str, EventEmitter] = {}


def register_emitter(run_id: str, emitter: EventEmitter) -> None:
    _emitters[run_id] = emitter


def unregister_emitter(run_id: str) -> None:
    _emitters.pop(run_id, None)


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def log_event(
    state: SharedState,
    agent: str,
    event: str,
    extra: dict[str, Any] | None = None,
) -> WorkflowEvent:
    record = WorkflowEvent(
        run_id=state.run_id,
        timestamp=_timestamp(),
        agent=agent,
        event=event,
        extra=extra,
    )

    state.events.append(record)

    emit = _emitters.get(state.run_id)
    if emit is not None:
        try:
            emit(record)
        except Exception:
            # Logging must never break the workflow.
            pass

    return record
