"""Application entry point for the Fieldstone workflow
creates a sample client brief, runs the multi-agent workflow, and 
prints a concise workflow summary
"""

from __future__ import annotations
import asyncio
from src.logging.logger import get_log_path
from src.state import ClientBrief
from src.workflow.orchestrator import Orchestrator


SAMPLE_CLIENT_BRIEF = ClientBrief(
    topic="Why people are upset with Flock cameras",
    audience="General public",
    tone="Informative, balanced, and concerned",
    length="500 words",
    required_sections=["Introduction", "Main concerns", "Potential benefits", "Conclusion"],
    objective="Explain why some communities are concerned about Flock Safety cameras while presenting the topic clearly and fairly.",
    format="Article",
    special_instructions="Do not invent facts, statistics, quotes, sources, or events. Clearly represent research uncertainty.",
)

#main workflow

async def main() -> None:
    print("\n\n *MULTI-AGENT CONTENT WORKFLOW*\n\n")
    print(f"Topic: {SAMPLE_CLIENT_BRIEF.topic}")
    print("Starting workflow...\n")

    orchestrator = Orchestrator(max_retries=2)
    state = await orchestrator.run(SAMPLE_CLIENT_BRIEF)

    # workflow summary
    print("\n\n WORKFLOW RESULT:\n")
    print(f"Run ID: {state.run_id}")
    print(f"Final Status: {state.final_status}")
    print(f"Retry Count: {state.retry_count}/{state.max_retries}")
    print(f"Draft Version: {state.draft_version}")

    # critic summary
    if state.critic_output:
        print("\n\n CRITIC RESULT:\n")
        print(f"Verdict: {state.critic_output.verdict}")
        print(f"Severity: {state.severity or 'none'}")

        if state.critic_output.issues:
            print("\nIssues:")
            for issue in state.critic_output.issues:
                print(f"- {issue.issue_id}: {issue.issue_type} [{issue.severity}]")
                if issue.explanation:
                    print(f"  Why: {issue.explanation}")
        else:
            print("\nIssues: None")

        if state.critic_output.revision_instructions:
            print("\nRevision Instructions:")
            for instruction in state.critic_output.revision_instructions:
                print(f"- {instruction.issue_id}: {instruction.instruction}")

    # final output
    print("\n--------------\n FINAL OUTPUT\n--------------")
    if state.final_output:
        print(state.final_output)
    else:
        print("No final article was produced.")

    # logging information
    print("\n\n OBSERVABILITY:\n")
    print(f"Workflow Events: {len(state.events)}")
    print(f"Log File: {get_log_path(state)}")
    print("\n\n WORKFLOW COMPLETE\n\n")


# python module entry point
if __name__ == "__main__":
    asyncio.run(main())