"""Retry and human-escalation logic.

the retry policy lives here and is used exclusively b the Orchestrator;
the critic does not decide whether a retry happens
"""

from src.state import CriticOutput, SharedState, highest_severity

def should_retry(state: SharedState, critic: CriticOutput) -> bool:
    """true when another automated Writer retry is allowed."""
    if critic.verdict != "FAIL":
        return False
    return state.retry_count < state.max_retries

def escalate_to_human(state: SharedState, critic: CriticOutput) -> bool:
    """
    true when the run must leave automation and go to a human.

    Exception-Only Approval: an unresolved CRITICAL issue escalates
    immediately, regardless of how many retries remain, so a critical
    issue is not something an automated retry should be trusted to fix
    silently. Otherwise, escalate once retries are exhausted.
    """
    if critic.verdict != "FAIL":
        return False
    if highest_severity(critic.issues) == "critical":
        return True
    return state.retry_count >= state.max_retries
