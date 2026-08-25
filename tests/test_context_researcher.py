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


def test_ctx_ids_are_present_and_sequential():
    result = run_context_research({"topic": "standing desks"})
    ids = [t["id"] for t in result["themes"]]
    assert ids == ["CTX-001", "CTX-002", "CTX-003"]


def test_flags_assumed_defaults_when_data_missing():
    """Should never silently invent values -- must flag what it guessed."""
    result = run_context_research({})
    assert "assumed_defaults" in result
    assert "audience" in result["assumed_defaults"]
    assert "tone" in result["assumed_defaults"]
    assert "topic" in result["assumed_defaults"]


def test_no_defaults_flagged_when_all_data_provided():
    result = run_context_research({
        "topic": "standing desks",
        "audience": "HR managers",
        "tone": "professional",
    })
    assert result["assumed_defaults"] == []


def test_handles_invalid_client_brief_type():
    """Should not crash if client_brief is None or wrong type entirely."""
    result = run_context_research(None)
    assert "audience_summary" in result
    result2 = run_context_research("not a dict")
    assert "audience_summary" in result2