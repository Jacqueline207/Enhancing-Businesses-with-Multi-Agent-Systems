"""Workflow orchestrator."""

import asyncio

from src.agents.context_researcher import run_context_research
from src.agents.critic import run_critic
from src.agents.source_researcher import run_source_research
from src.agents.writer import run_writer
from src.logging.logger import log_event
from src.state import SharedState


class Orchestrator:
    def __init__(self, max_retries: int = 2):
        self.max_retries = max_retries

    async def run(self, client_brief: dict) -> SharedState:
        state = SharedState(
            client_brief=client_brief,
            max_retries=self.max_retries,
        )

        log_event(
            state,
            agent="orchestrator",
            event="run_start",
        )

        await self._run_parallel_research(state)

        self._run_writer_step(state)

        self._run_critic_retry_loop(state)

        log_event(
            state,
            agent="orchestrator",
            event="run_end",
            extra={
                "final_status": state.final_status,
                "retry_count": state.retry_count,
            },
        )

        return state

    @staticmethod
    def _unwrap_contract(result: dict, key: str) -> dict:
        if not isinstance(result, dict):
            return {}

        nested_result = result.get(key)

        if isinstance(nested_result, dict):
            return nested_result

        return result

    async def _run_parallel_research(
        self,
        state: SharedState,
    ) -> None:
        log_event(
            state,
            agent="orchestrator",
            event="research_start",
        )

        source_task = asyncio.to_thread(
            run_source_research,
            state.client_brief,
        )

        context_task = asyncio.to_thread(
            run_context_research,
            state.client_brief,
        )

        source_result, context_result = await asyncio.gather(
            source_task,
            context_task,
        )

        state.source_research = self._unwrap_contract(
            source_result,
            "source_research",
        )

        state.context_research = self._unwrap_contract(
            context_result,
            "context_research",
        )

        log_event(
            state,
            agent="orchestrator",
            event="research_complete",
        )

    def _run_writer_step(
        self,
        state: SharedState,
    ) -> None:
        state.draft_version += 1

        writer_input = {
            "client_brief": state.client_brief,
            "source_research": state.source_research,
            "context_research": state.context_research,
            "revision_instructions": state.revision_instructions,
            "draft_version": state.draft_version,
        }

        log_event(
            state,
            agent="orchestrator",
            event="writer_start",
            extra={
                "draft_version": state.draft_version,
            },
        )

        state.writer_output = run_writer(writer_input)

        log_event(
            state,
            agent="orchestrator",
            event="writer_complete",
            extra={
                "draft_version": state.draft_version,
            },
        )

    def _run_critic_step(
        self,
        state: SharedState,
    ) -> None:
        critic_input = {
            "client_brief": state.client_brief,
            "source_research": state.source_research,
            "context_research": state.context_research,
            "writer_output": state.writer_output,
            "retry_count": state.retry_count,
        }

        log_event(
            state,
            agent="orchestrator",
            event="critic_start",
        )

        state.critic_output = run_critic(critic_input)

        state.critic_verdict = state.critic_output.get(
            "verdict",
            "FAIL",
        )

        state.revision_instructions = state.critic_output.get(
            "revision_instructions",
            [],
        )

        log_event(
            state,
            agent="orchestrator",
            event="critic_complete",
            extra={
                "verdict": state.critic_verdict,
                "retry_count": state.retry_count,
            },
        )

    def _retry_available(
        self,
        state: SharedState,
    ) -> bool:
        critic_requests_retry = bool(
            state.critic_output.get("retry", False)
        )

        retries_remaining = (
            state.retry_count < state.max_retries
        )

        return (
            state.critic_verdict == "FAIL"
            and critic_requests_retry
            and retries_remaining
        )

    def _run_critic_retry_loop(
        self,
        state: SharedState,
    ) -> None:
        self._run_critic_step(state)

        while state.critic_verdict == "FAIL":
            if not self._retry_available(state):
                self._send_to_human_review(state)
                return

            state.retry_count += 1

            log_event(
                state,
                agent="orchestrator",
                event="retry_triggered",
                extra={
                    "retry_count": state.retry_count,
                },
            )

            self._run_writer_step(state)

            self._run_critic_step(state)

        state.final_status = "COMPLETED"
        state.final_output = state.writer_output

        log_event(
            state,
            agent="orchestrator",
            event="pass_final_output",
        )

    def _send_to_human_review(
        self,
        state: SharedState,
    ) -> None:
        state.final_status = "HUMAN_REVIEW"

        state.final_output = {
            "status": "HUMAN_REVIEW",
            "writer_output": state.writer_output,
            "critic_output": state.critic_output,
            "retry_count": state.retry_count,
        }

        log_event(
            state,
            agent="orchestrator",
            event="human_review_flagged",
            extra={
                "retry_count": state.retry_count,
            },
        )