"""Application entry point (Fieldstone Media agentic content pipeline).

to run from the python root:
    python -m src.main

requires the llm api key to be set (look at .env.example) since the agents 
now call a reall LLM through src/integrations/ai_gateway.py (no more placeholder)
"""

import os
import asyncio
import json
from dataclasses import asdict
from dotenv import load_dotenv

from src.state import ClientBrief
from src.workflow.orchestrator import Orchestrator

load_dotenv()

SAMPLE_CLIENT_BRIEF = ClientBrief(
    topic="Benefits of community solar programs",
    audience="Local homeowners",
    tone="Informative, friendly",
    length="500 words",
    required_sections=["intro", "body", "conclusion"],
)


async def main() -> None:
    orchestrator = Orchestrator(max_retries=2)
    state = await orchestrator.run(SAMPLE_CLIENT_BRIEF)

    print("\n=== FINAL STATUS ===")
    print(state.final_status)

    print("\n=== FINAL OUTPUT ===")
    print(state.final_output)

    print("\n=== FULL SHARED STATE (for logging/debug) ===")
    print(json.dumps(asdict(state), indent=2, default=str))


if __name__ == "__main__":
    asyncio.run(main())
