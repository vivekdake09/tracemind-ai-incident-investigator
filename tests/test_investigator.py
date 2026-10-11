"""Unit tests for src/investigator.py grounding validation and demo mode."""

import pytest
from src.investigator import Investigator


@pytest.fixture(scope="module")
def investigator():
    # Initialize without API key for offline/demo tests
    return Investigator(api_key=None)


def test_model_status_offline_without_key(investigator):
    status = investigator.check_model_status()
    assert status["online"] is False
    assert "not configured" in status["message"]


def test_grounding_validation_strips_hallucinated_ids(investigator):
    retrieved_ids = ["incident_INC-001", "runbook_db_timeouts.md"]
    mock_report = {
        "incident_summary": "DB issue",
        "hypotheses": [
            {
                "rank": 1,
                "title": "Network Route Drop",
                "confidence": "High",
                "explanation": "Matches symptoms.",
                "cited_evidence_ids": [
                    "incident_INC-001",
                    "incident_INC-999_HALLUCINATED",  # Fabricated ID
                    "runbook_fake.md",               # Fabricated ID
                ],
                "diagnostic_checks": [],
                "remediation": "Rollback",
                "verification_steps": "Verify"
            }
        ],
        "missing_information": None,
        "insufficient_evidence": False,
    }

    filtered_report, warnings = investigator._validate_and_filter_grounding(mock_report, retrieved_ids)
    
    # Check that hallucinated IDs were stripped
    remaining_ids = filtered_report["hypotheses"][0]["cited_evidence_ids"]
    assert remaining_ids == ["incident_INC-001"]
    assert len(warnings) == 2
    assert any("INC-999" in w for w in warnings)
    assert any("runbook_fake.md" in w for w in warnings)


def test_demo_mode_db_timeout(investigator):
    result = investigator.analyze(
        title="Database Connection Timeout on Checkout",
        logs="FATAL: connection to database 'payments' failed\ntimeout expired while waiting",
        demo_mode=True,
    )
    assert result["status"] == "success"
    assert result["mode"] == "demo"
    assert "report" in result
    report = result["report"]
    assert len(report["hypotheses"]) >= 1
    assert report["hypotheses"][0]["confidence"] in ["High", "Medium"]
    assert len(result["evidence"]) > 0


def test_demo_mode_abstention_on_unknown_incident(investigator):
    result = investigator.analyze(
        title="Completely Unrelated Quantum Kernel Error 9988",
        logs="Quantum entanglement coherence lost at node 42 in sector 7",
        demo_mode=True,
    )
    assert result["status"] == "success"
    assert result["mode"] == "demo"
    report = result["report"]
    assert report["insufficient_evidence"] is True
    assert len(report["hypotheses"]) == 0
    assert "No historical postmortems" in report["missing_information"]


def test_demo_mode_masks_sensitive_data(investigator):
    logs = "Connecting with secret postgres://admin:superSecret123@db.prod:5432/main and Bearer abcdef1234567890abcdef12345"
    result = investigator.analyze(
        title="DB auth failure",
        logs=logs,
        demo_mode=True,
    )
    assert result["redactions_count"] >= 2
