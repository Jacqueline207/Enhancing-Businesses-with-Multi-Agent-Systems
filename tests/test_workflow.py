"""End-to-end workflow tests.
mocks all four agents. tests check the Orchestrator's own
routing logic (not llm calls)
"""

import asyncio
from unittest.mock import patch

from src.state import (
    ClientBrief, ContextResearch, CriticIssue, CriticOutput, SourceResearch, WriterOutput,
)
from src.workflow.orchestrator import Orchestrator

BRIEF = ClientBrief(topic="t", audience="a", tone="informative", length="500 words",
                     required_sections=["intro"])

DRAFT = WriterOutput(
    title="T", article="Body [R-001].", source_claim_ids_used=["R-001"],
    claim_trace=[], requirements_self_check=[],
    unsupported_or_missing_information=[], revision_summary=[],
)

EMPTY_SOURCE = SourceResearch(research_summary="", claims=[], conflicting_evidence=[], missing_information=[])
EMPTY_CONTEXT = ContextResearch(context_summary="", context_notes=[], recommended_outline=[], source_research_requests=[])


def make_critic(verdict: str, severity: str = "major") -> CriticOutput:
    issues = []
    if verdict == "FAIL":
        issues = [CriticIssue(
            issue_id="I-001", check_ids=["K1"], issue_type="unsupported_claim",
            severity=severity, draft_excerpt="", evidence=[], explanation="",
        )]
    return CriticOutput(verdict=verdict, checks=[], issues=issues, revision_instructions=[], warnings=[])


def run(coro):
    return asyncio.run(coro)


@patch("src.workflow.orchestrator.run_critic")
@patch("src.workflow.orchestrator.run_writer")
@patch("src.workflow.orchestrator.run_context_research")
@patch("src.workflow.orchestrator.run_source_research")
def test_completes_on_first_pass_without_retrying(mock_source, mock_context, mock_writer, mock_critic):
    mock_source.return_value = EMPTY_SOURCE
    mock_context.return_value = EMPTY_CONTEXT
    mock_writer.return_value = DRAFT
    mock_critic.return_value = make_critic("PASS")

    state = run(Orchestrator(2).run(BRIEF))

    assert state.final_status == "COMPLETED"
    assert state.retry_count == 0
    assert mock_writer.call_count == 1
    assert state.final_output == DRAFT.article


@patch("src.workflow.orchestrator.run_critic")
@patch("src.workflow.orchestrator.run_writer")
@patch("src.workflow.orchestrator.run_context_research")
@patch("src.workflow.orchestrator.run_source_research")
def test_retries_once_and_completes_when_revised_draft_passes(mock_source, mock_context, mock_writer, mock_critic):
    mock_source.return_value = EMPTY_SOURCE
    mock_context.return_value = EMPTY_CONTEXT
    mock_writer.return_value = DRAFT
    mock_critic.side_effect = [make_critic("FAIL"), make_critic("PASS")]

    state = run(Orchestrator(2).run(BRIEF))

    assert state.retry_count == 1
    assert state.draft_version == 2
    assert state.final_status == "COMPLETED"


@patch("src.workflow.orchestrator.run_critic")
@patch("src.workflow.orchestrator.run_writer")
@patch("src.workflow.orchestrator.run_context_research")
@patch("src.workflow.orchestrator.run_source_research")
def test_stops_at_max_retries_and_escalates(mock_source, mock_context, mock_writer, mock_critic):
    mock_source.return_value = EMPTY_SOURCE
    mock_context.return_value = EMPTY_CONTEXT
    mock_writer.return_value = DRAFT
    mock_critic.return_value = make_critic("FAIL")

    state = run(Orchestrator(2).run(BRIEF))

    assert state.retry_count == 2
    assert mock_writer.call_count == 3
    assert state.final_status == "HUMAN_REVIEW"
    assert any(e.event == "max_retries_reached" for e in state.events)


@patch("src.workflow.orchestrator.run_critic")
@patch("src.workflow.orchestrator.run_writer")
@patch("src.workflow.orchestrator.run_context_research")
@patch("src.workflow.orchestrator.run_source_research")
def test_escalates_immediately_on_a_critical_issue(mock_source, mock_context, mock_writer, mock_critic):
    mock_source.return_value = EMPTY_SOURCE
    mock_context.return_value = EMPTY_CONTEXT
    mock_writer.return_value = DRAFT
    mock_critic.return_value = make_critic("FAIL", severity="critical")

    state = run(Orchestrator(2).run(BRIEF))

    assert state.retry_count == 0
    assert state.final_status == "HUMAN_REVIEW"


@patch("src.workflow.orchestrator.run_critic")
@patch("src.workflow.orchestrator.run_writer")
@patch("src.workflow.orchestrator.run_context_research")
@patch("src.workflow.orchestrator.run_source_research")
def test_runs_both_researchers_in_parallel_before_the_writer(mock_source, mock_context, mock_writer, mock_critic):
    mock_source.return_value = EMPTY_SOURCE
    mock_context.return_value = EMPTY_CONTEXT
    mock_writer.return_value = DRAFT
    mock_critic.return_value = make_critic("PASS")

    state = run(Orchestrator(2).run(BRIEF))

    order = [e.event for e in state.events]
    assert order.index("research_complete") < order.index("writer_start")
    assert mock_source.call_count == 1
    assert mock_context.call_count == 1
