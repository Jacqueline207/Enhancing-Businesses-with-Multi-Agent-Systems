"""Tests for the Context / Angle Researcher agent."""

from src.agents.context_researcher import run_context_research


def test_returns_expected_keys():
    result = run_context_research({"topic": "standing desks"})
    assert "audience_summary" in result
    assert "themes" in result
    assert "suggested_angle" in result


def test_no_factual_claim_fields_present():
    """Context output must never contain a 'key_facts' field --
    the Critic should never mistake framing for checkable evidence."""
    result = run_context_research({"topic": "standing desks"})
    assert "key_facts" not in result
    assert "sources" not in result


def test_themes_is_a_list():
    result = run_context_research({"topic": "standing desks"})
    assert isinstance(result["themes"], list)
    assert len(result["themes"]) > 0


def test_handles_empty_client_brief():
    """Should not crash if topic/audience/tone are missing."""
    result = run_context_research({})
    assert "audience_summary" in result
    assert "suggested_angle" in result


def test_uses_custom_audience_when_provided():
    result = run_context_research({"topic": "standing desks", "audience": "HR managers"})
    assert "HR managers" in result["audience_summary"]