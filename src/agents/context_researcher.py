"""Context / Angle Researcher agent."""


def run_context_research(client_brief) -> dict:
    """
    Determines audience, themes, and a suggested angle for the piece.
    Runs in parallel with Source Researcher. Produces framing/direction
    only -- no factual claims, so the Critic never fact-checks this output.

    INPUT:
        client_brief: dict, expects {"topic": str, "audience": str (optional), "tone": str (optional)}
        If client_brief is missing or not a dict, treated as empty.

    OUTPUT:
        {
            "audience_summary": str,
            "themes": [{"id": "CTX-001", "theme": str}, ...],
            "suggested_angle": str,
            "assumed_defaults": [str, ...]   # flags any field we had to guess
        }
    """
    # Guard against invalid input types instead of crashing
    if not isinstance(client_brief, dict):
        client_brief = {}

    assumed_defaults = []

    topic = client_brief.get("topic")
    if not topic or not isinstance(topic, str):
        topic = "this topic"
        assumed_defaults.append("topic")

    audience = client_brief.get("audience")
    if not audience or not isinstance(audience, str):
        audience = "general readers"
        assumed_defaults.append("audience")

    tone = client_brief.get("tone")
    if not tone or not isinstance(tone, str):
        tone = "informative"
        assumed_defaults.append("tone")

    audience_summary = (
        f"This piece is intended for {audience}. They are most likely "
        f"looking for practical, {tone} content about \"{topic}\" rather "
        f"than deep academic detail."
    )

    raw_themes = [
        f"Why \"{topic}\" matters right now",
        "Practical takeaways the reader can act on",
        "Common misconceptions worth addressing",
    ]
    themes = [
        {"id": f"CTX-{i+1:03d}", "theme": t}
        for i, t in enumerate(raw_themes)
    ]

    suggested_angle = (
        f"Frame the piece around the real-world impact of \"{topic}\" for "
        f"{audience}, leading with a concrete benefit rather than a broad "
        f"definition."
    )

    return {
        "audience_summary": audience_summary,
        "themes": themes,
        "suggested_angle": suggested_angle,
        "assumed_defaults": assumed_defaults,
    }


if __name__ == "__main__":
    import json
    result = run_context_research({"topic": "benefits of standing desks", "audience": "remote workers"})
    print(json.dumps(result, indent=2))