"""Tests for the Source Researcher agent."""

from src.agents.source_researcher import run_source_research


def test_returns_expected_keys():
    result = run_source_research({"topic": "standing desks"})
    assert "sources" in result
    assert "key_facts" in result


def test_sources_have_required_fields():
    result = run_source_research({"topic": "standing desks"})
    for source in result["sources"]:
        assert "title" in source
        assert "url" in source
        assert "text" in source


def test_key_facts_have_ids_and_source_urls():
    result = run_source_research({"topic": "standing desks"})
    for i, fact in enumerate(result["key_facts"], start=1):
        assert fact["id"] == f"R-{i:03d}"
        assert "fact" in fact
        assert "source_url" in fact


def test_handles_empty_client_brief():
    """Should not crash if topic is missing."""
    result = run_source_research({})
    assert "sources" in result
    assert "key_facts" in result


def test_result_is_deterministic():
    """Same topic should give same results every run."""
    result_1 = run_source_research({"topic": "standing desks"})
    result_2 = run_source_research({"topic": "standing desks"})
    assert result_1 == result_2