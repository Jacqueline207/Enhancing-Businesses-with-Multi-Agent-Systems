"""End-to-end workflow tests.

these tests mock the individual agents so that we can verify orchestration behavior without making real API calls.

Covered behavior:
- research handoffs, writer handoff, critic handoff
- successful PASS workflow
- FAIL -> retry -> PASS workflow
- GatewayError -> HUMAN_REVIEW
- workflow logging events
"""

from __future__ import annotations
import asyncio
from unittest.mock import patch
from src.integrations.ai_gateway import GatewayError
from src.state import (
    ClientBrief,
    ContextNote,
    ContextResearch,
    CriticCheck,
    CriticIssue,
    CriticOutput,
    RevisionInstruction,
    SourceClaim,
    SourceResearch,
    WriterOutput,
)
from src.workflow.orchestrator import Orchestrator


#shared test data

BRIEF = ClientBrief(
    topic="Test topic",
    audience="General public",
    tone="Informative",
    length="500 words",
    required_sections=["Introduction", "Body", "Conclusion"],
)


def valid_checks() -> list[CriticCheck]:
    """Return a valid K1-K8 PASS check set."""
    names = {
        "K1": "factual_grounding",
        "K2": "source_fidelity",
        "K3": "unsupported_claims",
        "K4": "client_requirements",
        "K5": "internal_consistency",
        "K6": "publication_risk",
        "K7": "research_uncertainty",
        "K8": "conflicting_evidence",
    }
    return [CriticCheck(check_id=check_id, check_name=check_name, status="PASS", notes="") for check_id, check_name in names.items()]


def make_source_research() -> SourceResearch:
    """Create deterministic source research."""
    return SourceResearch(
        research_summary="One verified source claim.",
        claims=[
            SourceClaim(
                claim_id="R-001",
                claim_type="fact",
                claim="Verified source fact.",
                evidence="Verified evidence supporting the factual claim.",
                source_title="Test Source",
                source_publisher="Test Publisher",
                source_url_or_reference="https://example.com/source",
                source_date="2026-01-01",
                confidence="high",
            )
        ],
        conflicting_evidence=[],
        missing_information=[],
    )


def make_context_research() -> ContextResearch:
    """Create deterministic editorial context."""
    return ContextResearch(
        context_summary="Use a clear public-facing angle.",
        context_notes=[
            ContextNote(
                context_id="CTX-001",
                category="article_angle",
                recommendation="Use a clear public-facing angle.",
                rationale="The audience is the general public.",
                client_brief_reference="audience",
            )
        ],
        recommended_outline=["Introduction", "Body", "Conclusion"],
        source_research_requests=[],
    )


def make_pass() -> CriticOutput:
    """Create a passing critic result."""
    return CriticOutput(verdict="PASS", checks=valid_checks(), issues=[], revision_instructions=[], warnings=[])


def make_fail() -> CriticOutput:
    """Create a retryable major Critic failure."""
    return CriticOutput(
        verdict="FAIL",
        checks=valid_checks(),
        issues=[
            CriticIssue(
                issue_id="I-001",
                check_ids=["K1", "K3"],
                issue_type="unsupported_claim",
                severity="major",
                draft_excerpt="Unsupported statement.",
                evidence=[],
                explanation="The statement does not have supporting research.",
            )
        ],
        revision_instructions=[
            RevisionInstruction(
                issue_id="I-001",
                instruction="Remove the unsupported claim or support it with verified research.",
            )
        ],
        warnings=[],
    )


# successfull workflow

def test_successful_workflow_handoffs_are_correct():
    captured = {}
    source_research = make_source_research()
    context_research = make_context_research()

    def fake_source_research(current_brief):
        assert current_brief == BRIEF
        return source_research

    def fake_context_research(current_brief):
        assert current_brief == BRIEF
        return context_research

    def fake_writer(writer_input):
        captured["writer_input"] = writer_input
        return WriterOutput(title="Completed Article", article="Completed draft.", source_claim_ids_used=["R-001"])

    def fake_critic(critic_input):
        captured["critic_input"] = critic_input
        return make_pass()

    with patch("src.workflow.orchestrator.run_source_research", side_effect=fake_source_research), \
         patch("src.workflow.orchestrator.run_context_research", side_effect=fake_context_research), \
         patch("src.workflow.orchestrator.run_writer", side_effect=fake_writer), \
         patch("src.workflow.orchestrator.run_critic", side_effect=fake_critic):
        state = asyncio.run(Orchestrator(max_retries=2).run(BRIEF))

    # Research outputs made it into the Writer.
    writer_input = captured["writer_input"]
    assert writer_input.client_brief == BRIEF
    assert writer_input.source_research == source_research
    assert writer_input.context_research == context_research
    assert writer_input.critic_feedback is None
    assert writer_input.retry_count == 0

    # Writer output made it into the Critic.
    critic_input = captured["critic_input"]
    assert critic_input.client_brief == BRIEF
    assert critic_input.source_research == source_research
    assert critic_input.context_research == context_research
    assert critic_input.writer_output.article == "Completed draft."

    # Final workflow state.
    assert state.final_status == "COMPLETED"
    assert state.final_output == "Completed draft."
    assert state.retry_count == 0
    assert state.draft_version == 1


# fail to retry to pass
def test_fail_retry_pass_workflow():
    writer_inputs = []
    critic_inputs = []

    def fake_source_research(current_brief):
        return make_source_research()

    def fake_context_research(current_brief):
        return make_context_research()

    def fake_writer(writer_input):
        writer_inputs.append(writer_input)
        if len(writer_inputs) == 1:
            return WriterOutput(title="First Draft", article="First draft.")
        return WriterOutput(title="Revised Draft", article="Revised draft.")

    def fake_critic(critic_input):
        critic_inputs.append(critic_input)
        if len(critic_inputs) == 1:
            return make_fail()
        return make_pass()

    with patch("src.workflow.orchestrator.run_source_research", side_effect=fake_source_research), \
         patch("src.workflow.orchestrator.run_context_research", side_effect=fake_context_research), \
         patch("src.workflow.orchestrator.run_writer", side_effect=fake_writer), \
         patch("src.workflow.orchestrator.run_critic", side_effect=fake_critic):
        state = asyncio.run(Orchestrator(max_retries=2).run(BRIEF))

    # Writer ran twice: initial draft and one revision
    assert len(writer_inputs) == 2
    assert writer_inputs[0].retry_count == 0
    assert writer_inputs[0].critic_feedback is None

    # retry Writer gets critic feedback.
    assert writer_inputs[1].retry_count == 1
    assert writer_inputs[1].critic_feedback is not None
    assert writer_inputs[1].critic_feedback.revision_instructions[0].issue_id == "I-001"

    # Critic ran once for each draft.
    assert len(critic_inputs) == 2
    assert critic_inputs[0].writer_output.article == "First draft."
    assert critic_inputs[1].writer_output.article == "Revised draft."

    # final workflow result.
    assert state.final_status == "COMPLETED"
    assert state.retry_count == 1
    assert state.draft_version == 2
    assert state.final_output == "Revised draft."
    assert state.critic_verdict == "PASS"


# Infrastructure failure

def test_infrastructure_failure_routes_to_human_review():
    writer_calls = []

    def fake_source_research(current_brief):
        return make_source_research()

    def fake_context_research(current_brief):
        return make_context_research()

    def fake_writer(writer_input):
        writer_calls.append(writer_input)
        return WriterOutput(title="Draft", article="Draft.")

    def fake_critic(critic_input):
        raise GatewayError(503, "Critic model unavailable.")

    with patch("src.workflow.orchestrator.run_source_research", side_effect=fake_source_research), \
         patch("src.workflow.orchestrator.run_context_research", side_effect=fake_context_research), \
         patch("src.workflow.orchestrator.run_writer", side_effect=fake_writer), \
         patch("src.workflow.orchestrator.run_critic", side_effect=fake_critic):
        state = asyncio.run(Orchestrator(max_retries=2).run(BRIEF))

    assert state.final_status == "HUMAN_REVIEW"
    # Infrastructure failure must NOT consume a content-revision retry.
    assert state.retry_count == 0
    assert len(writer_calls) == 1


# logging

def test_workflow_logging_events_are_present():
    events = []

    def fake_log_event(state, agent, event, extra=None):
        events.append(event)

    def fake_source_research(current_brief):
        return make_source_research()

    def fake_context_research(current_brief):
        return make_context_research()

    def fake_writer(writer_input):
        return WriterOutput(title="Draft", article="Draft.")

    def fake_critic(critic_input):
        return make_pass()

    with patch("src.workflow.orchestrator.log_event", side_effect=fake_log_event), \
         patch("src.workflow.orchestrator.run_source_research", side_effect=fake_source_research), \
         patch("src.workflow.orchestrator.run_context_research", side_effect=fake_context_research), \
         patch("src.workflow.orchestrator.run_writer", side_effect=fake_writer), \
         patch("src.workflow.orchestrator.run_critic", side_effect=fake_critic):
        asyncio.run(Orchestrator(max_retries=2).run(BRIEF))

    expected_events = {
        "run_start",
        "research_start",
        "source_research_complete",
        "context_research_complete",
        "research_complete",
        "writer_start",
        "writer_complete",
        "critic_start",
        "critic_complete",
        "pass_final_output",
        "run_end",
    }
    assert expected_events <= set(events)