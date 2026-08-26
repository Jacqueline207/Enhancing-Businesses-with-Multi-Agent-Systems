"""Tests for retry and routing behavior."""

import src.workflow.orchestrator as orchestrator_module
from src.state import SharedState
from src.workflow.orchestrator import Orchestrator


def valid_checks():
    return [
        {"check_id": f"K{number}"}
        for number in range(1, 9)
    ]


def test_critic_fail_triggers_writer_retry_and_increments_count(
    monkeypatch,
):
    orchestrator = Orchestrator(max_retries=2)

    state = SharedState(
        client_brief={"topic": "Test topic"},
        max_retries=2,
    )

    critic_calls = []
    writer_calls = []

    def fake_critic_step(current_state):
        critic_calls.append(1)

        if len(critic_calls) == 1:
            current_state.critic_verdict = "FAIL"
            current_state.critic_output = {
                "verdict": "FAIL",
                "checks": valid_checks(),
                "revision_instructions": [
                    {
                        "instruction": "Revise the unsupported claim.",
                    }
                ],
            }
        else:
            current_state.critic_verdict = "PASS"
            current_state.critic_output = {
                "verdict": "PASS",
                "checks": valid_checks(),
                "revision_instructions": [],
            }

    def fake_writer_step(current_state):
        writer_calls.append(current_state.retry_count)

    monkeypatch.setattr(
        orchestrator,
        "_run_critic_step",
        fake_critic_step,
    )

    monkeypatch.setattr(
        orchestrator,
        "_run_writer_step",
        fake_writer_step,
    )

    orchestrator._run_critic_retry_loop(state)

    assert state.retry_count == 1
    assert writer_calls == [1]
    assert len(critic_calls) == 2
    assert state.final_status == "COMPLETED"


def test_critic_feedback_and_retry_count_reach_writer(
    monkeypatch,
):
    orchestrator = Orchestrator(max_retries=2)

    state = SharedState(
        client_brief={"topic": "Test topic"},
        max_retries=2,
    )

    state.source_research = {
        "claims": [],
    }

    state.context_research = {
        "context_notes": [],
    }

    state.critic_output = {
        "verdict": "FAIL",
        "checks": valid_checks(),
        "revision_instructions": [
            {
                "instruction": "Revise the draft.",
            }
        ],
    }

    state.retry_count = 1

    captured_input = {}

    def fake_run_writer(writer_input):
        captured_input.update(writer_input)

        return {
            "article": "Revised article.",
        }

    monkeypatch.setattr(
        orchestrator_module,
        "run_writer",
        fake_run_writer,
    )

    orchestrator._run_writer_step(state)

    assert captured_input["client_brief"] == state.client_brief
    assert captured_input["source_research"] == state.source_research
    assert captured_input["context_research"] == state.context_research
    assert captured_input["critic_feedback"] == state.critic_output
    assert captured_input["retry_count"] == 1
    assert state.writer_output["article"] == "Revised article."


def test_pass_stops_retry_behavior(
    monkeypatch,
):
    orchestrator = Orchestrator(max_retries=2)

    state = SharedState(
        client_brief={"topic": "Test topic"},
        max_retries=2,
    )

    writer_calls = []

    def fake_critic_step(current_state):
        current_state.critic_verdict = "PASS"
        current_state.critic_output = {
            "verdict": "PASS",
            "checks": valid_checks(),
            "revision_instructions": [],
        }

    def fake_writer_step(current_state):
        writer_calls.append(1)

    monkeypatch.setattr(
        orchestrator,
        "_run_critic_step",
        fake_critic_step,
    )

    monkeypatch.setattr(
        orchestrator,
        "_run_writer_step",
        fake_writer_step,
    )

    orchestrator._run_critic_retry_loop(state)

    assert state.retry_count == 0
    assert writer_calls == []
    assert state.final_status == "COMPLETED"


def test_maximum_retries_stop_automated_retry(
    monkeypatch,
):
    orchestrator = Orchestrator(max_retries=2)

    state = SharedState(
        client_brief={"topic": "Test topic"},
        max_retries=2,
    )

    state.retry_count = 2

    writer_calls = []

    def fake_critic_step(current_state):
        current_state.critic_verdict = "FAIL"
        current_state.critic_output = {
            "verdict": "FAIL",
            "checks": valid_checks(),
            "revision_instructions": [
                {
                    "instruction": "Revise again.",
                }
            ],
        }

    def fake_writer_step(current_state):
        writer_calls.append(1)

    monkeypatch.setattr(
        orchestrator,
        "_run_critic_step",
        fake_critic_step,
    )

    monkeypatch.setattr(
        orchestrator,
        "_run_writer_step",
        fake_writer_step,
    )

    orchestrator._run_critic_retry_loop(state)

    assert state.retry_count == 2
    assert writer_calls == []
    assert state.final_status == "HUMAN_REVIEW"


def test_critic_infrastructure_failure_does_not_use_retry(
    monkeypatch,
):
    orchestrator = Orchestrator(max_retries=2)

    state = SharedState(
        client_brief={"topic": "Test topic"},
        max_retries=2,
    )

    writer_calls = []

    def fake_critic_step(current_state):
        current_state.critic_verdict = "FAIL"
        current_state.critic_output = {
            "verdict": "FAIL",
            "checks": [],
            "issues": [
                "Critic model unavailable.",
            ],
        }

    def fake_writer_step(current_state):
        writer_calls.append(1)

    monkeypatch.setattr(
        orchestrator,
        "_run_critic_step",
        fake_critic_step,
    )

    monkeypatch.setattr(
        orchestrator,
        "_run_writer_step",
        fake_writer_step,
    )

    orchestrator._run_critic_retry_loop(state)

    assert state.retry_count == 0
    assert writer_calls == []
    assert state.final_status == "HUMAN_REVIEW"