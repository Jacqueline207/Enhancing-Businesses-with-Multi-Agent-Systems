"""Context / Angle Researcher agent."""


def run_context_research(client_brief: dict) -> dict:
    """
    Determines audience, themes, and a suggested angle for the piece.
    Runs in parallel with Source Researcher. Produces framing/direction
    only — no factual claims, so the Critic never fact-checks this output.


  INPUT:
        client_brief: dict, expects {"topic": str, "audience": str (optional), "tone": str (optional)}

    OUTPUT:
        {
            "audience_summary": str,
            "themes": [str, ...],
            "suggested_angle": str
        }
    """
    topic = client_brief.get("topic", "")
    audience = client_brief.get("audience", "general readers")
    tone = client_brief.get("tone", "informative")

    audience_summary = (
        f"This piece is intended for {audience}. They are most likely "
        f"looking for practical, {tone} content about \"{topic}\" rather "
        f"than deep academic detail."
    )

    themes = [
        f"Why \"{topic}\" matters right now",
        "Practical takeaways the reader can act on",
        "Common misconceptions worth addressing",
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
    }


if __name__ == "__main__":
    import json
    result = run_context_research({"topic": "benefits of standing desks", "audience": "remote workers"})
    print(json.dumps(result, indent=2))