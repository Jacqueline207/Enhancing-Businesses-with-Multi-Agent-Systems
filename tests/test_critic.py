"""Tests for Critic behavior.
mocks call_agent_json to these tests check the Critic's own normalization/
enforcement logic
"""

from unittest.mock import patch

from src.agents.critic import CriticInput, run_critic
from src.state import ClientBrief

BRIEF = ClientBrief(topic="t", audience="a", tone="informative", length="500 words",
                     required_sections=["intro"])

CRITIC_INPUT = CriticInput(
    client_brief=BRIEF, source_research=None, context_research=None, writer_output=None,
)


def test_pass_with_all_eight_checks_when_no_issues():
    with patch("src.agents.critic.call_agent_json") as mock_call:
        mock_call.return_value = {"verdict": "PASS", "checks": [], "issues": []}
        out = run_critic(CRITIC_INPUT)

    assert out.verdict == "PASS"
    assert [c.check_id for c in out.checks] == ["K1", "K2", "K3", "K4", "K5", "K6", "K7", "K8"]
    assert out.warnings == []


def test_never_returns_pass_while_listing_a_major_issue():
    with patch("src.agents.critic.call_agent_json") as mock_call:
        mock_call.return_value = {
            "verdict": "PASS",
            "checks": [],
            "issues": [{
                "issue_id": "I-001", "check_ids": ["K1"], "issue_type": "unsupported_claim",
                "severity": "major", "draft_excerpt": "", "evidence": [], "explanation": "no marker",
            }],
        }
        out = run_critic(CRITIC_INPUT)

    assert out.verdict == "FAIL"
    assert next(c for c in out.checks if c.check_id == "K1").status == "FAIL"


def test_keeps_minor_only_issues_as_pass_with_warnings():
    with patch("src.agents.critic.call_agent_json") as mock_call:
        mock_call.return_value = {
            "verdict": "PASS",
            "checks": [],
            "issues": [{
                "issue_id": "I-001", "check_ids": ["K4"], "issue_type": "length_violation",
                "severity": "minor", "draft_excerpt": "", "evidence": [], "explanation": "slightly short",
            }],
        }
        out = run_critic(CRITIC_INPUT)

    assert out.verdict == "PASS"
    assert len(out.warnings) == 1
    assert next(c for c in out.checks if c.check_id == "K4").status == "WARNING"


def test_coerces_an_unknown_issue_type_to_a_permitted_value():
    with patch("src.agents.critic.call_agent_json") as mock_call:
        mock_call.return_value = {
            "verdict": "FAIL",
            "checks": [],
            "issues": [{
                "issue_id": "", "check_ids": ["K3"], "issue_type": "made_up_type",
                "severity": "major", "draft_excerpt": "", "evidence": [], "explanation": "",
            }],
        }
        out = run_critic(CRITIC_INPUT)

    assert out.issues[0].issue_type == "unsupported_claim"
    assert out.issues[0].issue_id == "I-001"
