"""Application entry point for the Fieldstone workflow."""

import asyncio
import json

from src.workflow.orchestrator import Orchestrator


SAMPLE_CLIENT_BRIEF = {
    "topic": "Why people are upset with Flock cameras",
    "audience": "General public",
    "tone": "Informative, concerned",
    "objective": "Explain the main concerns clearly and accurately.",
    "length": "500 words",
    "required_sections": [
        "intro",
        "body",
        "conclusion",
    ],
}


async def main() -> None:
    orchestrator = Orchestrator(max_retries=2)

    state = await orchestrator.run(SAMPLE_CLIENT_BRIEF)

    print("\nFINAL STATUS")
    print(state.final_status)

    print("\nFINAL OUTPUT")
    print(
        json.dumps(
            state.final_output,
            indent=2,
            default=str,
        )
    )

    print("\nRUN ID")
    print(state.run_id)


if __name__ == "__main__":
    asyncio.run(main())