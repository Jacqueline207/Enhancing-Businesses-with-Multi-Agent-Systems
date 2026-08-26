"""External research and data-source integrations.

this module is the single entry point through which
outside factual source material enters the workflow, no 
external search provider is currently connected.

Returning an empty list is intentional: it prevents
the Source Researcher from inventing evidence when
no approved source material exists.
"""

from __future__ import annotations

from typing import Any


def search_sources(
    client_brief: Any,
    requests: list[str] | None = None,
) -> list[dict]:
    """
    Retrieve approved factual source material.

    A real research provider can later be connected
    here without changing the Source Researcher.

    Expected future result format:

    [
        {
            "query": "...",
            "title": "...",
            "publisher": "...",
            "url_or_reference": "...",
            "date": "...",
            "excerpt": "..."
        }
    ]
    """

    requests = requests or []

    #no external research provider is connected yet.
    #it is safer than raise NotImplementedError
    #the workflow can continue instead of crashing
    return []