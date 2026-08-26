"""Tests for retry and escalation behavior.

These tests verify:
- FAIL allows an automated retry
- PASS stops retry behavior
- retry_count respects max_retries
- critical issues escalate to human review
- max retries escalate to human review
- Critic feedback reaches the Writer
"""

from unittest.mock import patch
from src.agents.writer import CriticFeedback
from src.state import (
    ClientBrief,
    CriticIssue,
    CriticOutput,
    RevisionInstruction,
    WriterOutput,
    create_shared_state,
)
from src.workflow.orchestrator import Orchestrator
from src.workflow.retry import escalate_to_human, should_retry


# shared test data

BRIEF = ClientBrief(
    topic="Test topic",
    audience="General public",
    tone="Informative",
    length="500 words",
    required_sections=["Introduction", "Body", "Conclusion"],
)


def make_major_failure() -> CriticOutput:
    """Create a normal retryable Critic failure."""
    issue = CriticIssue(
        issue_id="I-001",
        check_ids=["K1", "K3"],
        issue_type="unsupported_claim",
        severity="major",
        draft_excerpt="Unsupported statement.",
        evidence=[],
        explanation="The statement does not have supporting research.",
    )
    instruction = RevisionInstruction(
        issue_id="I-001",
        instruction="Remove the unsupported claim or rewrite it using verified evidence.",
    )
    return CriticOutput(
        verdict="FAIL",
        issues=[issue],
        revision_instructions=[instruction],
        warnings=[],
    )


def make_critical_failure() -> CriticOutput:
    """Create a Critic failure requiring human review."""
    issue = CriticIssue(
        issue_id="I-001",
        check_ids=["K6"],
        issue_type="publication_risk",
        severity="critical",
        draft_excerpt="Risky statement.",
        evidence=[],
        explanation="The draft contains a critical publication risk.",
    )
    return CriticOutput(
        verdict="FAIL",
        issues=[issue],
        revision_instructions=[RevisionInstruction(issue_id="I-001", instruction="Escalate this publication risk for review.")],
        warnings=[],
    )


#retry policy tests

def test_fail_allows_retry():
    state = create_shared_state(BRIEF, max_retries=2)
    critic = make_major_failure()
    assert should_retry(state, critic) is True


def test_pass_stops_retry_behavior():
    state = create_shared_state(BRIEF, max_retries=2)
    critic = CriticOutput(verdict="PASS", issues=[], revision_instructions=[], warnings=[])
    assert should_retry(state, critic) is False


def test_maximum_retries_stop_automated_retry():
    state = create_shared_state(BRIEF, max_retries=2)
    state.retry_count = 2
    critic = make_major_failure()
    assert should_retry(state, critic) is False


# human escalation test

def test_critical_issue_escalates_immediately():
    state = create_shared_state(BRIEF, max_retries=2)
    critic = make_critical_failure()
    assert escalate_to_human(state, critic) is True


def test_max_retries_escalates_to_human():
    state = create_shared_state(BRIEF, max_retries=2)
    state.retry_count = 2
    critic = make_major_failure()
    assert escalate_to_human(state, critic) is True


def test_normal_failure_does_not_immediately_escalate():
    state = create_shared_state(BRIEF, max_retries=2)
    critic = make_major_failure()
    assert escalate_to_human(state, critic) is False


# writer revision handoff
def test_critic_feedback_and_retry_count_reach_writer():
    orchestrator = Orchestrator(max_retries=2)
    state = create_shared_state(BRIEF, max_retries=2)
    state.retry_count = 1
    critic = make_major_failure()

    feedback = CriticFeedback(
        issues=critic.issues,
        revision_instructions=critic.revision_instructions,
        warnings=critic.warnings,
    )

    captured = {}

    def fake_writer(writer_input):
        captured["retry_count"] = writer_input.retry_count
        captured["critic_feedback"] = writer_input.critic_feedback
        return WriterOutput(title="Revised Article", article="Revised article.")

    with patch("src.workflow.orchestrator.run_writer", side_effect=fake_writer):
        orchestrator._run_writer(state, critic_feedback=feedback)

    assert captured["retry_count"] == 1
    assert captured["critic_feedback"] is not None
    assert captured["critic_feedback"].revision_instructions[0].issue_id == "I-001"
    assert state.writer_output.article == "Revised article."
    assert state.writer_draft == "Revised article."
    assert state.draft_version == 1