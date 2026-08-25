"""Source Researcher agent."""

"""
for Dejameir (integration)

the input is the client brief and the output consist of sources and key facts

the body should contain real search and API integration
the return signature and return shape should be the same as here so orchestrator.py likely 
wont change
"""

"""Source Researcher agent."""

from src.integrations.reasearch_tools import search_web


def run_source_research(client_brief: dict) -> dict:
    """
    Gathers factual, source-backed evidence for the Writer and Critic.

    INPUT:
        client_brief: dict, expects at least {"topic": str}

    OUTPUT:
        {
            "sources": [{"title": str, "url": str, "text": str}, ...],
            "key_facts": [{"id": "R-001", "fact": str, "source_url": str}, ...]
        }
    """
    topic = client_brief.get("topic", "")

    raw_results = search_web(topic, max_results=5)

    sources = [
        {"title": r["title"], "url": r["url"], "text": r["snippet"]}
        for r in raw_results
    ]

    key_facts = []
    for i, r in enumerate(raw_results, start=1):
        fact_text = r["snippet"].split(".")[0].strip() + "."
        key_facts.append({
            "id": f"R-{i:03d}",
            "fact": fact_text,
            "source_url": r["url"],
        })

    return {
        "sources": sources,
        "key_facts": key_facts,
    }


if __name__ == "__main__":
    import json
    result = run_source_research({"topic": "benefits of standing desks"})
    print(json.dumps(result, indent=2))