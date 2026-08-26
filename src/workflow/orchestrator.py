"""Main multi-agent workflow orchestrator.

Workflow:
Client Brief → Parallel Research (Source + Context) → Writer → Critic → PASS → Final Output
FAIL → Critical? → Human Review
    ↓ No
Retry available? → Writer Revision → Critic (repeat)
Max retries reached → Human Review / Failed Max Retries

The Orchestrator owns:
- workflow routing, retry_count, draft_version, final_status, human escalation, workflow logging
"""

from __future__ import annotations
import asyncio

from src.agents.context_researcher import run_context_research
from src.agents.critic import CriticInput, run_critic
from src.agents.source_researcher import run_source_research
from src.agents.writer import CriticFeedback, WriterInput, run_writer
from src.integrations.ai_gateway import GatewayError
from src.logging.logger import log_event
from src.state import ClientBrief, SharedState, create_shared_state, highest_severity
from src.workflow.retry import escalate_to_human, should_retry


class Orchestrator:
    """controls the complete multi-agent workflow."""

    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries

    # the main entry point
    async def run(self, client_brief: ClientBrief) -> SharedState:
        state = create_shared_state(client_brief=client_brief, max_retries=self.max_retries)
        self._log(state, agent="orchestrator", event="run_start", data={"topic": client_brief.topic, "max_retries": state.max_retries})

        try:
            # 1 Parallel research
            await self._run_research(state)

            # 2 Initial Writer draft
            self._run_writer(state, critic_feedback=None)

            # 3 + Critic / retry loop
            while True:
                self._run_critic(state)
                critic = state.critic_output
                if critic is None:
                    raise RuntimeError("Critic did not produce an output.")

                # PASS
                if critic.verdict == "PASS":
                    state.final_status = "COMPLETED"
                    state.final_output = state.writer_output.article if state.writer_output else state.writer_draft
                    self._log(state, agent="orchestrator", event="pass_final_output",
                              data={"final_status": state.final_status, "retry_count": state.retry_count, "draft_version": state.draft_version})
                    break

                # CRITICAL → HUMAN REVIEW
                if escalate_to_human(state, critic):
                    state.final_status = "HUMAN_REVIEW"
                    state.final_output = state.writer_output.article if state.writer_output else state.writer_draft
                    self._log(state, agent="orchestrator", event="human_review_flagged",
                              data={"reason": "critical_issue" if highest_severity(critic.issues) == "critical" else "max_retries_reached",
                                    "retry_count": state.retry_count, "critic_verdict": critic.verdict})
                    break

                # retry
                if should_retry(state, critic):
                    state.retry_count += 1
                    self._log(state, agent="orchestrator", event="retry_triggered",
                              data={"retry_count": state.retry_count, "max_retries": state.max_retries,
                                    "critic_verdict": critic.verdict, "critic_issues": critic.issues,
                                    "revision_instructions": critic.revision_instructions})
                    feedback = CriticFeedback(issues=critic.issues, revision_instructions=critic.revision_instructions, warnings=critic.warnings)
                    self._run_writer(state, critic_feedback=feedback)
                    continue

                # defensive fallback
                state.final_status = "FAILED_MAX_RETRIES"
                state.final_output = state.writer_output.article if state.writer_output else state.writer_draft
                self._log(state, agent="orchestrator", event="max_retries_reached",
                          data={"retry_count": state.retry_count, "max_retries": state.max_retries})
                break

        except GatewayError as exc:
            state.final_status = "HUMAN_REVIEW"
            self._log(state, agent="orchestrator", event="gateway_error",
                      data={"status": exc.status, "message": str(exc), "retryable": exc.retryable})

        except Exception as exc:
            state.final_status = "HUMAN_REVIEW"
            self._log(state, agent="orchestrator", event="workflow_error",
                      data={"error_type": type(exc).__name__, "message": str(exc)})

        finally:
            self._log(state, agent="orchestrator", event="run_end",
                      data={"final_status": state.final_status, "retry_count": state.retry_count, "draft_version": state.draft_version})

        return state

    # parallel research

    async def _run_research(self, state: SharedState) -> None:
        self._log(state, agent="orchestrator", event="research_start")
        source_task = asyncio.to_thread(run_source_research, state.client_brief)
        context_task = asyncio.to_thread(run_context_research, state.client_brief)
        source_result, context_result = await asyncio.gather(source_task, context_task)
        state.source_research = source_result
        state.context_research = context_result

        self._log(state, agent="source_researcher", event="source_research_complete",
                  data={"claim_count": len(source_result.claims), "missing_information": source_result.missing_information})
        self._log(state, agent="context_researcher", event="context_research_complete",
                  data={"context_note_count": len(context_result.context_notes), "source_research_requests": context_result.source_research_requests})
        self._log(state, agent="orchestrator", event="research_complete")

    # Writer

    def _run_writer(self, state: SharedState, critic_feedback: CriticFeedback | None) -> None:
        self._log(state, agent="writer", event="writer_revision_start" if critic_feedback else "writer_start",
                  data={"retry_count": state.retry_count, "next_draft_version": state.draft_version + 1})
        writer_input = WriterInput(client_brief=state.client_brief, source_research=state.source_research,
                                   context_research=state.context_research, critic_feedback=critic_feedback,
                                   retry_count=state.retry_count)
        output = run_writer(writer_input)
        state.writer_output = output
        state.writer_draft = output.article
        state.draft_version += 1
        self._log(state, agent="writer", event="writer_revision_complete" if critic_feedback else "writer_complete",
                  data={"draft_version": state.draft_version, "retry_count": state.retry_count,
                        "title": output.title, "source_claim_ids_used": output.source_claim_ids_used})

    # critic

    def _run_critic(self, state: SharedState) -> None:
        self._log(state, agent="critic", event="critic_start",
                  data={"draft_version": state.draft_version, "retry_count": state.retry_count})
        critic_input = CriticInput(client_brief=state.client_brief, source_research=state.source_research,
                                   context_research=state.context_research, writer_output=state.writer_output)
        output = run_critic(critic_input)
        state.critic_output = output
        state.critic_verdict = output.verdict
        state.critic_issues = output.issues
        state.revision_instructions = output.revision_instructions
        state.severity = highest_severity(output.issues)
        self._log(state, agent="critic", event="critic_complete",
                  data={"verdict": output.verdict, "issues": output.issues, "revision_instructions": output.revision_instructions,
                        "warnings": output.warnings, "severity": state.severity,
                        "retry_count": state.retry_count, "draft_version": state.draft_version})

    #the logging adapter

    def _log(self, state: SharedState, agent: str, event: str, data: dict | None = None) -> None:
        log_event(
        state=state,
        agent=agent,
        event=event,
        extra=data or {},)