"""External research and data-source integrations.

search_sources() is where retreived outside material enters the workflow
no external search provider is connected, so an empty list is returned
the source researcer must work only from client brief and record what it can't
support in missing_information, to not invent evidence
"""

from __future__ import annotations

from typing import Any

def search_sources(client_brief: Any, requests: list[str] | None = None) -> list[dict]:
    """
    Returns retrieved source material for the given client brief and
    research requests. No approved search provider is connected yet,
    returning an empty list keeps the "never invent a source" contract
    intact while leaving one place to plug a real provider in later
    (e.g. a web search API or an internal document store).

    the expected entry shape once a provider is connected:
        {"query": str, "title": str, "publisher": str,
         "url_or_reference": str, "date": str, "excerpt": str}
    """
    return []
