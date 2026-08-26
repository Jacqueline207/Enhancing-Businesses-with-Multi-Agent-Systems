"""
retry and human-escalation logic.

the retry policy belongs to the workflow layer.

the Critic evaluates the draft.
the Orchestrator decides what happens next.
"""

from src.state import (
    CriticOutput,
    SharedState,
    highest_severity,
)


def should_retry(
    state: SharedState,
    critic: CriticOutput,
) -> bool:
    """
    return true when another automated Writer
    revision is allowed.
    """

    if critic.verdict != "FAIL":
        return False

    return state.retry_count < state.max_retries


def escalate_to_human(
    state: SharedState,
    critic: CriticOutput,
) -> bool:
    """
    determine whether automated processing should
    stop and require human review.

    critical issues escalate immediately.

    major/minor failures receive automated retries
    until the retry limit is reached.
    """

    if critic.verdict != "FAIL":
        return False

    severity = highest_severity(
        critic.issues
    )

    if severity == "critical":
        return True

    return (
        state.retry_count
        >= state.max_retries
    )