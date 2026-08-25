"""Critic / Editor agent."""
"""
@Krystle, contract with orchestrator
this is basically the proposed critic output section 12 of your master plan

the input is a dictionary:
    INPUT (dict):
            client_brief      - dict
            research_sources  - list[dict]
            key_facts         - list[dict]
            writer_draft      - str
            retry_count       - int

the body needs the real Critic logic [section 11 of the master plan] (the llm grading against 
factual grounding, the source fidelity, unsupported claims, client requriements, etc)
the output should be another dictionary with the fields listed in the return part of run_critic
these return keys should be kept exactly as they are because the Orchestrator reads them directly
"""

def run_critic(critic_input: dict) -> dict:
    """
    placeholder always passes on the first attempt to the full pipeline is runnable before the real 
    Critic exists
    """
    return {
        "verdict": "PASS",
        "issues": [],
        "evidence": [],
        "revision_instructions": None,
        "severity": None,
        "retry": False,
    }