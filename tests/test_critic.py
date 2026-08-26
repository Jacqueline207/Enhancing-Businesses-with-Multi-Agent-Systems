"""Tests for Critic behavior and K1-K8 QA contract."""
from unittest.mock import patch

from src.agents.critic import (
    CriticInput,
    run_critic,
)
from src.state import (
    ClientBrief,
)


BRIEF = ClientBrief(
    topic="Test topic",
    audience="General audience",
    tone="Informative",
    length="500 words",
    required_sections=[
        "intro",
        "body",
        "conclusion",
    ],
)


CRITIC_INPUT = CriticInput(
    client_brief=BRIEF,
    source_research=None,
    context_research=None,
    writer_output=None,
)


def test_critic_pass_contains_k1_through_k8():

    with patch(
        "src.agents.critic.call_agent_json"
    ) as mock_call:

        mock_call.return_value = {
            "verdict": "PASS",
            "checks": [],
            "issues": [],
            "revision_instructions": [],
            "warnings": [],
        }

        result = run_critic(
            CRITIC_INPUT
        )

    assert (
        result.verdict
        == "PASS"
    )

    assert [
        check.check_id
        for check in result.checks
    ] == [
        "K1",
        "K2",
        "K3",
        "K4",
        "K5",
        "K6",
        "K7",
        "K8",
    ]


def test_major_issue_forces_fail():

    with patch(
        "src.agents.critic.call_agent_json"
    ) as mock_call:

        mock_call.return_value = {
            "verdict": "PASS",

            "issues": [
                {
                    "issue_id": "I-001",
                    "check_ids": [
                        "K1",
                        "K3",
                    ],
                    "issue_type": (
                        "unsupported_claim"
                    ),
                    "severity": "major",
                    "draft_excerpt": (
                        "Unsupported statement."
                    ),
                    "evidence": [],
                    "explanation": (
                        "No research evidence "
                        "supports this statement."
                    ),
                }
            ],
        }

        result = run_critic(
            CRITIC_INPUT
        )

    assert (
        result.verdict
        == "FAIL"
    )

    k1 = next(
        check
        for check
        in result.checks
        if check.check_id == "K1"
    )

    assert (
        k1.status
        == "FAIL"
    )


def test_minor_issue_remains_pass():

    with patch(
        "src.agents.critic.call_agent_json"
    ) as mock_call:

        mock_call.return_value = {
            "verdict": "PASS",

            "issues": [
                {
                    "issue_id": "I-001",
                    "check_ids": [
                        "K4",
                    ],
                    "issue_type": (
                        "length_violation"
                    ),
                    "severity": "minor",
                    "draft_excerpt": "",
                    "evidence": [],
                    "explanation": (
                        "Article is slightly "
                        "shorter than requested."
                    ),
                }
            ],
        }

        result = run_critic(
            CRITIC_INPUT
        )

    assert (
        result.verdict
        == "PASS"
    )

    assert (
        len(result.warnings)
        == 1
    )

    k4 = next(
        check
        for check
        in result.checks
        if check.check_id == "K4"
    )

    assert (
        k4.status
        == "WARNING"
    )


def test_unknown_issue_type_is_normalized():

    with patch(
        "src.agents.critic.call_agent_json"
    ) as mock_call:

        mock_call.return_value = {
            "verdict": "FAIL",

            "issues": [
                {
                    "issue_id": "",
                    "check_ids": [
                        "K3",
                    ],
                    "issue_type": (
                        "made_up_issue"
                    ),
                    "severity": "major",
                    "draft_excerpt": "",
                    "evidence": [],
                    "explanation": "",
                }
            ],
        }

        result = run_critic(
            CRITIC_INPUT
        )

    assert (
        result.issues[
            0
        ].issue_type
        == "unsupported_claim"
    )

    assert (
        result.issues[
            0
        ].issue_id
        == "I-001"
    )


def test_blocking_issue_gets_revision_instruction():

    with patch(
        "src.agents.critic.call_agent_json"
    ) as mock_call:

        mock_call.return_value = {
            "verdict": "FAIL",

            "issues": [
                {
                    "issue_id": "I-001",
                    "check_ids": [
                        "K3",
                    ],
                    "issue_type": (
                        "unsupported_claim"
                    ),
                    "severity": "major",
                    "draft_excerpt": "",
                    "evidence": [],
                    "explanation": (
                        "Claim lacks evidence."
                    ),
                }
            ],

            "revision_instructions": [],
        }

        result = run_critic(
            CRITIC_INPUT
        )

    assert (
        len(
            result.revision_instructions
        )
        == 1
    )

    assert (
        result.revision_instructions[
            0
        ].issue_id
        == "I-001"
    )