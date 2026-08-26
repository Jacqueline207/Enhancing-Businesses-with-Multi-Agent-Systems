"""Tests for retry behavior."""


from src.state import ClientBrief, CriticIssue, CriticOutput, Severity, create_shared_state
from src.workflow.retry import escalate_to_human, should_retry

BRIEF = ClientBrief(topic="t", audience="a", tone="informative", length="500 words",
                     required_sections=["intro"])


def make_issue(severity: Severity) -> CriticIssue:
    return CriticIssue(
        issue_id="I-001", check_ids=["K1"], issue_type="unsupported_claim",
        severity=severity, draft_excerpt="", evidence=[], explanation="",
    )


def make_critic(verdict: str, issues: list[CriticIssue] | None = None) -> CriticOutput:
    return CriticOutput(verdict=verdict, checks=[], issues=issues or [],
                         revision_instructions=[], warnings=[])


def test_never_retries_a_pass():
    state = create_shared_state(BRIEF, 2)
    assert should_retry(state, make_critic("PASS")) is False
    assert escalate_to_human(state, make_critic("PASS")) is False


def test_retries_a_fail_while_retries_remain():
    state = create_shared_state(BRIEF, 2)
    assert should_retry(state, make_critic("FAIL", [make_issue("major")])) is True
    state.retry_count = 2
    assert should_retry(state, make_critic("FAIL", [make_issue("major")])) is False


def test_escalates_when_retries_are_exhausted():
    state = create_shared_state(BRIEF, 2)
    state.retry_count = 2
    assert escalate_to_human(state, make_critic("FAIL", [make_issue("major")])) is True


def test_escalates_immediately_on_a_critical_issue():
    state = create_shared_state(BRIEF, 2)
    assert escalate_to_human(state, make_critic("FAIL", [make_issue("critical")])) is True
