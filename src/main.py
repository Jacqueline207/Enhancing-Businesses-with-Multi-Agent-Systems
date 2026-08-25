"""Application entry point.

to run from the python root:
    python -m src.main
"""

import asyncio
import json

from src.workflow.orchestrator import Orchestrator

"""
here is a sample client brief with fields [topic, audience, tone, length, required_sections]
fields can be modifed
*it is harcoded for testing purposes
"""

SAMPLE_CLIENT_BRIEF = {
    "topic": "Why people are upset with Flock cameras", 
    "audience": "General public",
    "tone": "Informative, concerned",
    "length": "500 words",
    "requried_sections": ["into", "body", "conclusion"],
}

async def main():
    """Start the Fieldstone agent workflow."""

    """
    runs exactly one client brief through the entire pipeline and prints
    the result 
    async def is required becausd Orchestrator.run() is also an aysnc function
    it awaits the parallel research step internally (main awaits it)
    """
    #max retries is changed here
    orchestrator = Orchestrator(max_retries=2)

    """
    single call runs the entire workflow
    state is the final SharedState with everything that happened recorded on it
    """
    state = await orchestrator.run(SAMPLE_CLIENT_BRIEF)

    print("\n*FINAL STATUS*")
    print(state.final_status)

    print("\n*FINAL OUTPUT*")
    print(state.final_output)
        
    print("\n*FULL SHARED STATE (for logging/debug)*")
    print(json.dumps(state.to_dict(), indent=2, default=str))
    

if __name__ == "__main__":

    #what actually starts the event loop
    asyncio.run(main())
