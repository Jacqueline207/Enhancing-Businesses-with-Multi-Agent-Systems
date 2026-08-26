"""Workflow orchestrator

Client Brief
    1. Parallel research (Source and context researchers)
    2. Shared state
    3. Writer
    4. Critic
    5. Pass -final output or Fail (retry, up to max retries) -writer -critic 
    6. If repeated fail after max retries -human review and then final output

The orchestrator calls each agent's public function and knows what shape of input 
to send and what shape of output to expect
"""

from __future__ import annotations

import asyncio

from src.agents.context_researcher import run_context_research
from src.agents.critic import CriticInput, run_critic
from src.agents.source_researcher import run_source_research
from src.agents.writer import CriticFeedback, WriterInput, run_writer
from src.logging.logger import log_event
from src.state import ClientBrief, SharedState, create_shared_state
from src.workflow.retry import escalate_to_human, should_retry


class Orchestrator:
    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries

    async def run(self, client_brief: ClientBrief, state: SharedState | None = None) -> SharedState:
        """Runs the full workflow once and returns the final SharedState."""
        working_state = state or create_shared_state(client_brief, self.max_retries)
        log_event(
            working_state, "orchestrator", "run_start",
            {"topic": client_brief.topic, "max_retries": working_state.max_retries},
        )

        try:
            await self._run_parallel_research(working_state)
            await self._run_writer_step(working_state)
            await self._run_critic_retry_loop(working_state)
        except Exception as error:
            # Unexpected input/agent failures must not crash the whole
            # system - land on a terminal status instead, per the
            # checklist's "handled without crashing the entire system".
            working_state.final_status = "FAILED_MAX_RETRIES"
            working_state.final_output = None
            log_event(working_state, "orchestrator", "agent_error", {"message": str(error)})
            log_event(working_state, "orchestrator", "run_end", {"final_status": working_state.final_status})
            raise

        log_event(working_state, "orchestrator", "run_end", {"final_status": working_state.final_status})
        return working_state

    # ------------------------------------------------------------------
    # Step 1: Parallel research
    # ------------------------------------------------------------------
    async def _run_parallel_research(self, state: SharedState) -> None:
        """Both researchers run at the same time, then results merge into
        shared state as two SEPARATE fields (never combined into one list)."""
        log_event(state, "orchestrator", "research_start")

        source_task = asyncio.to_thread(run_source_research, state.client_brief)
        context_task = asyncio.to_thread(run_context_research, state.client_brief)
        source_result, context_result = await asyncio.gather(source_task, context_task)

        state.source_research = source_result
        state.context_research = context_result

        log_event(
            state, "orchestrator", "research_complete",
            {
                "source_claims": len(source_result.claims),
                "context_notes": len(context_result.context_notes),
            },
        )

    # ------------------------------------------------------------------
    # Step 3: Writer
    # ------------------------------------------------------------------
    async def _run_writer_step(self, state: SharedState) -> None:
        """One Writer pass. Called for the first draft and for every retry."""
        state.draft_version += 1
        log_event(
            state, "orchestrator", "writer_start",
            {"draft_version": state.draft_version, "retry_count": state.retry_count},
        )

        critic_feedback = None
        if state.critic_output is not None and state.critic_output.verdict == "FAIL":
            critic_feedback = CriticFeedback(
                issues=state.critic_output.issues,
                revision_instructions=state.critic_output.revision_instructions,
                warnings=state.critic_output.warnings,
            )

        writer_input = WriterInput(
            client_brief=state.client_brief,
            source_research=state.source_research,
            context_research=state.context_research,
            critic_feedback=critic_feedback,
            retry_count=state.retry_count,
        )
        output = await asyncio.to_thread(run_writer, writer_input)

        state.writer_output = output
        state.writer_draft = output.article

        log_event(
            state, "writer", "writer_complete",
            {
                "draft_version": state.draft_version,
                "title": output.title,
                "claims_used": len(output.source_claim_ids_used),
            },
        )

    # ------------------------------------------------------------------
    # Step 4: Critic
    # ------------------------------------------------------------------
    async def _run_critic_step(self, state: SharedState) -> None:
        """One Critic pass against the draft currently in state."""
        log_event(state, "orchestrator", "critic_start", {"draft_version": state.draft_version})

        critic_input = CriticInput(
            client_brief=state.client_brief,
            source_research=state.source_research,
            context_research=state.context_research,
            writer_output=state.writer_output,
        )
        output = await asyncio.to_thread(run_critic, critic_input)

        state.critic_output = output
        state.critic_verdict = output.verdict
        state.critic_issues = output.issues
        state.critic_evidence = [e for i in output.issues for e in i.evidence]
        state.revision_instructions = output.revision_instructions
        from src.state import highest_severity
        state.severity = highest_severity(output.issues)

        log_event(
            state, "critic", "critic_complete",
            {
                "verdict": output.verdict,
                "severity": state.severity,
                "issues": len(output.issues),
                "warnings": len(output.warnings),
            },
        )

    # ------------------------------------------------------------------
    # Steps 4-6: grade, route PASS/FAIL, retry, and escalate
    # ------------------------------------------------------------------
    async def _run_critic_retry_loop(self, state: SharedState) -> None:
        await self._run_critic_step(state)

        while True:
            critic = state.critic_output
            assert critic is not None

            if critic.verdict == "PASS":
                state.final_status = "COMPLETED"
                state.final_output = state.writer_draft
                log_event(
                    state, "orchestrator", "pass_final_output",
                    {"draft_version": state.draft_version, "retry_count": state.retry_count},
                )
                return

            if escalate_to_human(state, critic) or not should_retry(state, critic):
                if state.retry_count >= state.max_retries:
                    log_event(state, "orchestrator", "max_retries_reached", {"retry_count": state.retry_count})
                self._send_to_human_review(state)
                return

            state.retry_count += 1
            log_event(
                state, "orchestrator", "retry_triggered",
                {"retry_count": state.retry_count, "severity": state.severity},
            )

            await self._run_writer_step(state)
            await self._run_critic_step(state)

    def _send_to_human_review(self, state: SharedState) -> None:
        """Exception-Only Approval escalation hook."""
        state.final_status = "HUMAN_REVIEW"
        log_event(
            state, "orchestrator", "human_review_flagged",
            {
                "retry_count": state.retry_count,
                "severity": state.severity,
                "issues": len(state.critic_issues),
            },
        )
        retries_word = "retry" if state.retry_count == 1 else "retries"
        state.final_output = (
            f"[HUMAN REVIEW REQUIRED] Draft did not pass after {state.retry_count} "
            f"automated {retries_word}. Highest severity: {state.severity or 'unknown'}. "
            f"See critic issues for details."
        )
