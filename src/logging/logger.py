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

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

#directory where workflow logs are stored
LOG_DIR = Path("logs")
LOG_DIR.mkdir(parents=True, exist_ok=True)

def _timestamp() -> str:
    #Return the current UTC timestamp
    return datetime.now(timezone.utc).isoformat()

def _serialize(value: Any) -> Any:
    """
    convert objects into JSON-safe values.

    this keeps logging from crashing the workflow if an object is not
    directly JSON serializable
    """
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {
            str(key): _serialize(item)
            for key, item in value.items()
        }

    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]

    # Handle dataclasses such as SharedState.
    if hasattr(value, "to_dict"):
        return _serialize(value.to_dict())

    # Final fallback so logging never crashes the workflow.
    return str(value)


def _get_log_path(run_id: str) -> Path:
    #return the JSONL log path for a workflow run
    return LOG_DIR / f"run_{run_id}.jsonl"


def log_event(
    state,
    agent: str,
    event: str,
    extra: dict | None = None,
) -> None:
    
    """
    write one structured event to the current run's JSONL log.

    parameters
    ----------
    state:
        Current SharedState object.

    agent:
        Name of the agent or workflow component generating the event.

    event:
        Name describing what happened.

    extra:
        Optional additional information specific to the event.
    """

    record = {
        "timestamp": _timestamp(),
        "run_id": state.run_id,
        "agent": agent,
        "event": event,
        "retry_count": state.retry_count,
        "draft_version": state.draft_version,
        "data": _serialize(extra or {}),
    }

    log_path = _get_log_path(state.run_id)

    try:
        with log_path.open("a", encoding="utf-8") as file:
            file.write(json.dumps(record, ensure_ascii=False) + "\n")
    except OSError as exc:
        #logging should not be allowed to crash the entire workflow.
        print(f"[WARNING] Unable to write log event: {exc}")