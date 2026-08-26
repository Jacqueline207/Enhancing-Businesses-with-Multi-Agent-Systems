"""Tests for Critic behavior and K1-K8 QA contract."""

from copy import deepcopy

from src.agents.critic import run_critic


VALID_CRITIC_INPUT = {
    "client_brief": {"topic": "Test topic"},
    "source_research": {"claims": []},
    "context_research": {"context_notes": []},
    "writer_output": {"article": "Test article"},
}


VALID_CHECKS = [
    {
        "check_id": "K1",
        "check_name": "factual_grounding",
        "status": "PASS",
        "notes": "Factual claims are grounded.",
    },
    {
        "check_id": "K2",
        "check_name": "source_fidelity",
        "status": "PASS",
        "notes": "Sources are represented faithfully.",
    },
    {
        "check_id": "K3",
        "check_name": "unsupported_claims",
        "status": "PASS",
        "notes": "No unsupported claims found.",
    },
    {
        "check_id": "K4",
        "check_name": "client_requirements",
        "status": "PASS",
        "notes": "Client requirements are satisfied.",
    },
    {
        "check_id": "K5",
        "check_name": "internal_consistency",
        "status": "PASS",
        "notes": "The article is internally consistent.",
    },
    {
        "check_id": "K6",
        "check_name": "publication_risk",
        "status": "PASS",
        "notes": "No blocking publication risk found.",
    },
    {
        "check_id": "K7",
        "check_name": "research_uncertainty",
        "status": "PASS",
        "notes": "Research uncertainty is preserved.",
    },
    {
        "check_id": "K8",
        "check_name": "conflicting_evidence",
        "status": "PASS",
        "notes": "No unresolved conflicting evidence found.",
    },
]


def valid_model_output():
    return {
        "verdict": "PASS",
        "checks": deepcopy(VALID_CHECKS),
        "issues": [],
        "evidence": [],
        "revision_instructions": [],
        "severity": None,
        "warnings": [],
    }


def test_critic_pass_returns_all_k1_k8_checks_once():
    result = run_critic(
        VALID_CRITIC_INPUT,
        valid_model_output(),
    )

    assert result["verdict"] == "PASS"
    assert result["retry"] is False
    assert len(result["checks"]) == 8

    assert [check["check_id"] for check in result["checks"]] == [
        "K1",
        "K2",
        "K3",
        "K4",
        "K5",
        "K6",
        "K7",
        "K8",
    ]

    assert [check["check_name"] for check in result["checks"]] == [
        "factual_grounding",
        "source_fidelity",
        "unsupported_claims",
        "client_requirements",
        "internal_consistency",
        "publication_risk",
        "research_uncertainty",
        "conflicting_evidence",
    ]


def test_critic_fail_requests_retry():
    output = valid_model_output()

    output["verdict"] = "FAIL"
    output["checks"][2]["status"] = "FAIL"
    output["issues"] = [
        {
            "issue_id": "I-001",
            "message": "Unsupported claim.",
            "severity": "major",
            "evidence": ["R-001"],
        }
    ]
    output["revision_instructions"] = [
        {
            "issue_id": "I-001",
            "instruction": "Remove or support the claim.",
        }
    ]

    result = run_critic(
        VALID_CRITIC_INPUT,
        output,
    )

    assert result["verdict"] == "FAIL"
    assert result["retry"] is True
    assert result["severity"] == "major"
    assert result["evidence"] == ["R-001"]
    assert len(result["revision_instructions"]) == 1


def test_critic_invalid_verdict_becomes_fail():
    output = valid_model_output()
    output["verdict"] = "MAYBE"

    result = run_critic(
        VALID_CRITIC_INPUT,
        output,
    )

    assert result["verdict"] == "FAIL"
    assert result["retry"] is True


def test_critic_missing_required_input_fails_safely():
    result = run_critic(
        {
            "client_brief": {},
            "source_research": {},
            "context_research": {},
        },
        valid_model_output(),
    )

    assert result["verdict"] == "FAIL"
    assert result["retry"] is False
    assert "writer_output" in result["issues"][0]


def test_critic_invalid_model_output_fails_safely():
    result = run_critic(
        VALID_CRITIC_INPUT,
        "not-a-dictionary",
    )

    assert result["verdict"] == "FAIL"
    assert result["retry"] is False
    assert "expected a dictionary" in result["issues"][0]


def test_critic_rejects_missing_k_check():
    output = valid_model_output()
    output["checks"] = output["checks"][:-1]

    result = run_critic(
        VALID_CRITIC_INPUT,
        output,
    )

    assert result["verdict"] == "FAIL"
    assert result["retry"] is False
    assert result["checks"] == []
    assert "expected K1 through K8 exactly once" in result["issues"][0]


def test_critic_rejects_duplicate_k_check():
    output = valid_model_output()
    output["checks"][7] = deepcopy(output["checks"][0])

    result = run_critic(
        VALID_CRITIC_INPUT,
        output,
    )

    assert result["verdict"] == "FAIL"
    assert result["retry"] is False
    assert result["checks"] == []
    assert "expected K1 through K8 exactly once" in result["issues"][0]


def test_critic_rejects_wrong_check_name():
    output = valid_model_output()
    output["checks"][3]["check_name"] = "wrong_name"

    result = run_critic(
        VALID_CRITIC_INPUT,
        output,
    )

    assert result["verdict"] == "FAIL"
    assert result["retry"] is False
    assert result["checks"] == []
    assert "expected K1 through K8 exactly once" in result["issues"][0]


def test_critic_rejects_invalid_check_status():
    output = valid_model_output()
    output["checks"][5]["status"] = "MAYBE"

    result = run_critic(
        VALID_CRITIC_INPUT,
        output,
    )

    assert result["verdict"] == "FAIL"
    assert result["retry"] is False
    assert result["checks"] == []
    assert "expected K1 through K8 exactly once" in result["issues"][0]


def test_critic_sorts_k_checks_into_k1_k8_order():
    output = valid_model_output()
    output["checks"].reverse()

    result = run_critic(
        VALID_CRITIC_INPUT,
        output,
    )

    assert result["verdict"] == "PASS"

    assert [check["check_id"] for check in result["checks"]] == [
        "K1",
        "K2",
        "K3",
        "K4",
        "K5",
        "K6",
        "K7",
        "K8",
    ]