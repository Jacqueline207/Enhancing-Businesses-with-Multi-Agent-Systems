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

import asyncio
from src.state import SharedState
from src.logging.logger import log_event
from src.agents.source_researcher import run_source_research
from src.agents.context_researcher import run_context_research
from src.agents.writer import run_writer
from src.agents.critic import run_critic


class Orchestrator:
    def __init__(self, max_retries: int = 2):
        """
        how many automated writer retries allowed before human interference
        passed in at construction, configurable per run (not harcoded inside the retry loop)
        """
        self.max_retries = max_retries

    async def run(self, client_brief: dict) -> SharedState:
        """
        async def becuase research runs two agents concurrently using "asyncio.gather"
        entry point,  runs the full workflow once and returns the
        final SharedState (inspect state.final_status [either "COMPLETED" or "HUMAN_REVIEW"]/ state.final_output [result])
        so its run from start to finish (parallel research, then writer, then critic or retry loop,
        and lastly SharedState) 
        """
        #every run starts with a new SharedState, it generates the run_id/created_at and holds every field agents read and write for the rest of the run
        state = SharedState(client_brief=client_brief, max_retries=self.max_retries)
        log_event(state, agent="orchestrator", event="run_start")

        """
        the first step is to fire off research agents at the same time are merge their results onto state
        """
        await self._run_parallel_research(state)

        """
        the second step is to do the first writer draft, which is built from the merged research
        """
        self._run_writer_step(state)

        """
        the third and fourth step grades draft and if failed loops until passed
        or no more retries
        """
        self._run_critic_retry_loop(state)

        log_event(
            state, agent="orchestrator", event="run_end",
            extra={"final_status": state.final_status},
        )
        return state


    #Parallel research
    async def _run_parallel_research(self, state: SharedState) -> None:
        """
        runs source and context researchers (done at the same time) then merges
        both results onto shared state before writer runs

        """
        log_event(state, agent="orchestrator", event="research_start")

        #wrap each synchronous agent call so both can run at the same time  and in separte threads (no blocking)
        source_task = asyncio.to_thread(run_source_research, state.client_brief)
        context_task = asyncio.to_thread(run_context_research, state.client_brief)

        
        #waits for both agents to be done and if any raise and exception, asyncio.gather re-raises it
        source_result, context_result = await asyncio.gather(source_task, context_task)

        """
        merge parallel research results into shared state, its the shared state box
        both research streams land here before the writer reads anything
        """
        state.research_sources = source_result.get("sources", [])
        state.key_facts = source_result.get("key_facts", [])
        state.audience_context = context_result

        log_event(state, agent="orchestrator", event="research_complete")

    #writer
    def _run_writer_step(self, state: SharedState) -> None:

        """
        runs one Writer pass
        its called once for the first draft, and then again for every retry
        each call produces exactly one new draft and bumps the drafe_version by one (important for logging)
        *on a retry, state.revision_instructions should aready be populated from the previous _run_critic_step() call
        writer does no computation of revision instructions, it just forwards what is sitting on state to the writer
        """
        state.draft_version += 1
        log_event(
            state, agent="orchestrator", event="writer_start",
            extra={"draft_version": state.draft_version},
        )

        
        #this dictionary should be the exact contract run_writer() expects (in writer.py file)
        writer_input = {
            "client_brief": state.client_brief,
            "research_sources": state.research_sources,
            "key_facts": state.key_facts,
            "audience_context": state.audience_context,
            # None on first draft; populated with Critic feedback on retries
            "revision_instructions": state.revision_instructions,
        }
        state.writer_draft = run_writer(writer_input)

        log_event(
            state, agent="orchestrator", event="writer_complete",
            extra={"draft_version": state.draft_version},
        )

    #critic
    def _run_critic_step(self, state: SharedState) -> None:
        """
        run one critic pass against draft that currently sits in state.writer_draft
        copies the cridicts verdict onto shared state
        called once per draft (once after the first writer pass, and again after every retry)
        the Critic's OUTPUT CONTRACT becomes enforced here, run_critic() needs to return a dict
        with exactly (verdict, issues, evidence, revision_instructions, severity,
        retry) in critic.py file
        *if Kryste's real Critic returns different keys, CHANGE THEM HERE
        """
        log_event(state, agent="orchestrator", event="critic_start")

        #this dictionary is the exact input the critic receives, the exact data that Critic gets @Krystle
        critic_input = {
            "client_brief": state.client_brief,
            "research_sources": state.research_sources,
            "key_facts": state.key_facts,
            "writer_draft": state.writer_draft,
            "retry_count": state.retry_count,
        }
        critic_output = run_critic(critic_input)

        """
        copy every expected key off Critic's return dict to state .get()
        with ad default so missing key won't crash Orchestrator (field left as empty or none)
        """
        state.critic_verdict = critic_output.get("verdict")
        state.critic_issues = critic_output.get("issues", [])
        state.critic_evidence = critic_output.get("evidence", [])
        state.revision_instructions = critic_output.get("revision_instructions")
        state.severity = critic_output.get("severity")
        state.critic_retry_flag = critic_output.get("retry")

        log_event(
            state, agent="orchestrator", event="critic_complete",
            extra={"verdict": state.critic_verdict, "severity": state.severity},
        )

    #retry logic
    def _run_critic_retry_loop(self, state: SharedState) -> None:
        """
        how FAIL routes back to the Writer, how PASS moves forward, and when the loop
        gives up (escalates to human)
        flow:
            grade the current draft (already writen before loop even starts)
            while verdict is FAIL
                max_reties used up, stop, hand off to human
                otherwise, count it as one more retry and send draft back to Writer (include Critic's 
                revision_instructions which should already be attatched in state), and then grade new draft again
            loop exists with a PASS, mark run COMPLETED, copy passing draft to final_output
        """
        #grade first draft before loop starts
        self._run_critic_step(state)

        #keep looping if most recent verdict is FAIL
        while state.critic_verdict == "FAIL":
            if state.retry_count >= state.max_retries:
                # Repeated failure -> exception-only human review
                state.final_status = "HUMAN_REVIEW"
                log_event(
                    state, agent="orchestrator", event="max_retries_reached",
                    extra={"retry_count": state.retry_count},
                )
                self._send_to_human_review(state)
                return

            state.retry_count += 1
            log_event(
                state, agent="orchestrator", event="retry_triggered",
                extra={"retry_count": state.retry_count},
            )

            # FAIL routes back to Writer with revision_instructions already
            # sitting on `state` from the last critic step
            self._run_writer_step(state)
            self._run_critic_step(state)

        # PASS -> move forward to final output
        state.final_status = "COMPLETED"
        state.final_output = state.writer_draft
        log_event(state, agent="orchestrator", event="pass_final_output")

    def _send_to_human_review(self, state: SharedState) -> None:
        """
        placeholder escalation hook, called when max_retries is used up and 
        draft continues to fail 
        """
        log_event(state, agent="orchestrator", event="human_review_flagged")
        state.final_output = (
            f"[HUMAN REVIEW REQUIRED] Draft did not pass after "
            f"{state.retry_count} retries. See critic_issues for details."
        )
