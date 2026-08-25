"""Mock research tool — simulates a web search without needing any API key."""

import hashlib


def _fake_snippet(query: str, angle: str) -> str:
    return (
        f"Research on \"{query}\" suggests that {angle}. "
        f"Multiple sources point to consistent findings on this topic."
    )


def search_web(query: str, max_results: int = 5) -> list[dict]:
    """Returns a deterministic, offline list of mock sources.

    Returns:
        list of dicts: [{"title": str, "url": str, "snippet": str}, ...]
    """
    angles = [
        "there are measurable short-term benefits",
        "experts generally recommend a gradual, tested approach",
        "outcomes improve significantly with proper implementation",
        "common mistakes come from skipping early planning steps",
        "the long-term impact depends heavily on consistency",
    ]

    results = []
    for i in range(min(max_results, len(angles))):
        slug = hashlib.md5(f"{query}-{i}".encode()).hexdigest()[:8]
        results.append({
            "title": f"Source {i + 1}: Findings on \"{query}\"",
            "url": f"https://example-research.com/articles/{slug}",
            "snippet": _fake_snippet(query, angles[i]),
        })

    return results