"""
logger should record the workflow, SharedState.to_dict() for state capatured 

structured logging for the multi-agent workflow

each workflow run get its own JSONL log file.

one line = one event

ex:
-run_start
-research_start
-research_complete
-writer_start
-writer_complete
-critic_start
-critic_complete
-retry_triggered
-max_retries_reached
-human_review_flagged
-pass_final_output
-run_end
"""


from __future__ import annotations
import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from src.state import SharedState, WorkflowEvent


# log directory

LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)


# helpers

def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize(value: Any) -> Any:
    """
    convert nested workflow objects into JSON-safe values.
    logging must never fail simply because a dataclass or other custom Python object was supplied.
    """
    if value is None:
        return None
    if isinstance(value, (str, int, float, bool)):
        return value
    if is_dataclass(value):
        return _serialize(asdict(value))
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_serialize(item) for item in value]
    if hasattr(value, "to_dict"):
        try:
            return _serialize(value.to_dict())
        except Exception:
            pass
    # Final defensive fallback.
    return str(value)


def _get_log_path(run_id: str) -> Path:
    """Return the JSONL path for a workflow run."""
    return LOG_DIR / f"run_{run_id}.jsonl"


# main logging function 

def log_event(state: SharedState, agent: str, event: str, extra: dict[str, Any] | None = None) -> WorkflowEvent:
    """
    record one workflow event.

    The event is:
    1. appended to state.events
    2. written to logs/run_<run_id>.jsonl

    Logging failures are handled gracefully and must never crash the workflow.
    """
    safe_extra = _serialize(extra or {})
    workflow_event = WorkflowEvent(run_id=state.run_id, timestamp=_timestamp(), agent=agent, event=event, extra=safe_extra)

    # In-memory logging
    try:
        state.events.append(workflow_event)
    except Exception as exc:
        print(f"[WARNING] Unable to append in-memory log event: {exc}")

    # persistent JSONL logging
    record = {
        "timestamp": workflow_event.timestamp,
        "run_id": workflow_event.run_id,
        "agent": workflow_event.agent,
        "event": workflow_event.event,
        "retry_count": state.retry_count,
        "draft_version": state.draft_version,
        "data": safe_extra,
    }

    log_path = _get_log_path(state.run_id)
    try:
        with log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        # Logging must never crash the workflow.
        print(f"[WARNING] Unable to write log event: {exc}")

    return workflow_event


#optional helper

def get_log_path(state: SharedState) -> Path:
    """Public helper for finding the log file associated with a workflow state."""
    return _get_log_path(state.run_id)