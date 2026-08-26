"""End-to-end workflow and handoff tests."""

import asyncio

import src.workflow.orchestrator as orchestrator_module
from src.workflow.orchestrator import Orchestrator


def valid_checks():
    return [
        {"check_id": f"K{number}"}
        for number in range(1, 9)
    ]


def test_successful_workflow_handoffs_are_correct(
    monkeypatch,
):
    client_brief = {
        "topic": "Test topic",
    }

    source_research = {
        "claims": [
            {
                "claim_id": "R-001",
                "claim": "Verified source fact.",
            }
        ],
    }

    context_research = {
        "context_notes": [
            {
                "context_id": "CTX-001",
                "note": "Use a clear public-facing angle.",
            }
        ],
    }

    captured_writer_input = {}
    captured_critic_input = {}

    def fake_source_research(current_brief):
        assert current_brief == client_brief

        return {
            "source_research": source_research,
        }

    def fake_context_research(current_brief):
        assert current_brief == client_brief

        return {
            "context_research": context_research,
        }

    def fake_writer(writer_input):
        captured_writer_input.update(writer_input)

        return {
            "article": "Completed draft.",
        }

    def fake_critic(critic_input):
        captured_critic_input.update(critic_input)

        return {
            "verdict": "PASS",
            "checks": valid_checks(),
            "issues": [],
            "revision_instructions": [],
            "warnings": [],
        }

    monkeypatch.setattr(
        orchestrator_module,
        "run_source_research",
        fake_source_research,
    )

    monkeypatch.setattr(
        orchestrator_module,
        "run_context_research",
        fake_context_research,
    )

    monkeypatch.setattr(
        orchestrator_module,
        "run_writer",
        fake_writer,
    )

    monkeypatch.setattr(
        orchestrator_module,
        "run_critic",
        fake_critic,
    )

    state = asyncio.run(
        Orchestrator(max_retries=2).run(client_brief)
    )

    assert state.final_status == "COMPLETED"
    assert state.retry_count == 0

    assert state.source_research == source_research
    assert state.context_research == context_research

    assert captured_writer_input["client_brief"] == client_brief
    assert captured_writer_input["source_research"] == source_research
    assert captured_writer_input["context_research"] == context_research
    assert captured_writer_input["critic_feedback"] is None
    assert captured_writer_input["retry_count"] == 0

    assert captured_critic_input["client_brief"] == client_brief
    assert captured_critic_input["source_research"] == source_research
    assert captured_critic_input["context_research"] == context_research
    assert captured_critic_input["writer_output"] == {
        "article": "Completed draft.",
    }

    assert "retry_count" not in captured_critic_input


def test_fail_retry_pass_workflow(
    monkeypatch,
):
    client_brief = {
        "topic": "Retry test",
    }

    writer_inputs = []
    critic_inputs = []

    def fake_source_research(current_brief):
        return {
            "source_research": {
                "claims": [],
            }
        }

    def fake_context_research(current_brief):
        return {
            "context_research": {
                "context_notes": [],
            }
        }

    def fake_writer(writer_input):
        writer_inputs.append(dict(writer_input))

        if len(writer_inputs) == 1:
            return {
                "article": "First draft.",
            }

        return {
            "article": "Revised draft.",
        }

    def fake_critic(critic_input):
        critic_inputs.append(dict(critic_input))

        if len(critic_inputs) == 1:
            return {
                "verdict": "FAIL",
                "checks": valid_checks(),
                "issues": [
                    {
                        "issue_id": "I-001",
                        "message": "Draft needs revision.",
                    }
                ],
                "revision_instructions": [
                    {
                        "issue_id": "I-001",
                        "instruction": "Revise the draft.",
                    }
                ],
                "warnings": [],
            }

        return {
            "verdict": "PASS",
            "checks": valid_checks(),
            "issues": [],
            "revision_instructions": [],
            "warnings": [],
        }

    monkeypatch.setattr(
        orchestrator_module,
        "run_source_research",
        fake_source_research,
    )

    monkeypatch.setattr(
        orchestrator_module,
        "run_context_research",
        fake_context_research,
    )

    monkeypatch.setattr(
        orchestrator_module,
        "run_writer",
        fake_writer,
    )

    monkeypatch.setattr(
        orchestrator_module,
        "run_critic",
        fake_critic,
    )

    state = asyncio.run(
        Orchestrator(max_retries=2).run(client_brief)
    )

    assert state.final_status == "COMPLETED"
    assert state.retry_count == 1

    assert len(writer_inputs) == 2
    assert len(critic_inputs) == 2

    assert writer_inputs[0]["critic_feedback"] is None
    assert writer_inputs[0]["retry_count"] == 0

    assert writer_inputs[1]["critic_feedback"]["verdict"] == "FAIL"
    assert writer_inputs[1]["retry_count"] == 1

    assert critic_inputs[0]["writer_output"]["article"] == "First draft."
    assert critic_inputs[1]["writer_output"]["article"] == "Revised draft."


def test_infrastructure_failure_routes_to_human_review(
    monkeypatch,
):
    client_brief = {
        "topic": "Failure test",
    }

    writer_calls = []

    def fake_source_research(current_brief):
        return {
            "source_research": {
                "claims": [],
            }
        }

    def fake_context_research(current_brief):
        return {
            "context_research": {
                "context_notes": [],
            }
        }

    def fake_writer(writer_input):
        writer_calls.append(dict(writer_input))

        return {
            "article": "",
        }

    def fake_critic(critic_input):
        return {
            "verdict": "FAIL",
            "checks": [],
            "issues": [
                "Critic model unavailable.",
            ],
            "revision_instructions": [],
            "warnings": [
                "Critic model unavailable.",
            ],
        }

    monkeypatch.setattr(
        orchestrator_module,
        "run_source_research",
        fake_source_research,
    )

    monkeypatch.setattr(
        orchestrator_module,
        "run_context_research",
        fake_context_research,
    )

    monkeypatch.setattr(
        orchestrator_module,
        "run_writer",
        fake_writer,
    )

    monkeypatch.setattr(
        orchestrator_module,
        "run_critic",
        fake_critic,
    )

    state = asyncio.run(
        Orchestrator(max_retries=2).run(client_brief)
    )

    assert state.final_status == "HUMAN_REVIEW"
    assert state.retry_count == 0
    assert len(writer_calls) == 1


def test_workflow_logging_events_are_present(
    monkeypatch,
):
    events = []

    def fake_log_event(
        state,
        agent,
        event,
        extra=None,
    ):
        events.append(event)

    def fake_source_research(current_brief):
        return {
            "source_research": {
                "claims": [],
            }
        }

    def fake_context_research(current_brief):
        return {
            "context_research": {
                "context_notes": [],
            }
        }

    def fake_writer(writer_input):
        return {
            "article": "Draft.",
        }

    def fake_critic(critic_input):
        return {
            "verdict": "PASS",
            "checks": valid_checks(),
            "issues": [],
            "revision_instructions": [],
            "warnings": [],
        }

    monkeypatch.setattr(
        orchestrator_module,
        "log_event",
        fake_log_event,
    )

    monkeypatch.setattr(
        orchestrator_module,
        "run_source_research",
        fake_source_research,
    )

    monkeypatch.setattr(
        orchestrator_module,
        "run_context_research",
        fake_context_research,
    )

    monkeypatch.setattr(
        orchestrator_module,
        "run_writer",
        fake_writer,
    )

    monkeypatch.setattr(
        orchestrator_module,
        "run_critic",
        fake_critic,
    )

    asyncio.run(
        Orchestrator(max_retries=2).run(
            {
                "topic": "Logging test",
            }
        )
    )

    assert "run_start" in events
    assert "research_start" in events
    assert "research_complete" in events
    assert "writer_start" in events
    assert "writer_complete" in events
    assert "critic_start" in events
    assert "critic_complete" in events
    assert "pass_final_output" in events
    assert "run_end" in events