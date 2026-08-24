"""Writer agent."""
"""
for James, supplying real prompt and model call

the contract with the Orchestrator:
INPUT (dict):
        client_brief           - dict
        research_sources       - list[dict]
        key_facts               - list[dict]
        audience_context        - dict
        revision_instructions   - str or None (None on first draft,
                                  populated with Critic feedback on retries)
    OUTPUT: str  (the draft article text)

the body should have the reall LLM call using Jame's Writer system prompt
"""

def run_writer(writer_input: dict) -> str:
    revision_note = ""
    if writer_input.get("revision_instructions"):
        revision_note = f"\n\n[Revised per Critic feedback: {writer_input['revision_instructions']}]"
    
    return (
        "Placeholder draft article. Replace run_writer() with the real "
        "call to the Writer LLM using James's system prompt, the client "
        "brief, and the merged research."
        + revision_note
    )
