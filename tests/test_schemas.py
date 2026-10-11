"""Unit tests for Pydantic data schemas in src/schemas.py."""

import pytest
from pydantic import ValidationError
from src.schemas import InvestigationReport, Hypothesis, DiagnosticCheck


def test_valid_investigation_report():
    report = InvestigationReport(
        incident_summary="Database connection pool exhausted.",
        hypotheses=[
            Hypothesis(
                rank=1,
                title="VPC Route Table Change",
                confidence="High",
                explanation="Matches INC-001 where route table alteration severed connectivity.",
                cited_evidence_ids=["incident_INC-001", "runbook_db_timeouts.md"],
                diagnostic_checks=[
                    DiagnosticCheck(
                        check_name="Check CloudTrail",
                        description="Inspect recent VPC RouteTable updates."
                    )
                ],
                remediation="Revert route table modifications in AWS console.",
                verification_steps="Check DB connection metric in Grafana returns to 0 errors."
            )
        ],
        missing_information="Need VPC network flow logs.",
        insufficient_evidence=False,
    )
    assert report.incident_summary == "Database connection pool exhausted."
    assert len(report.hypotheses) == 1
    assert report.hypotheses[0].confidence == "High"
    assert len(report.hypotheses[0].cited_evidence_ids) == 2


def test_invalid_confidence_level():
    with pytest.raises(ValidationError):
        Hypothesis(
            rank=1,
            title="Test",
            confidence="Certain",  # Invalid: must be High, Medium, or Low
            explanation="Test explanation",
            cited_evidence_ids=[],
            diagnostic_checks=[],
            remediation="Test remediation",
            verification_steps="Test steps"
        )


def test_invalid_hypothesis_rank_out_of_bounds():
    with pytest.raises(ValidationError):
        Hypothesis(
            rank=5,  # Invalid: ge=1, le=3
            title="Test",
            confidence="Low",
            explanation="Test explanation",
            cited_evidence_ids=[],
            diagnostic_checks=[],
            remediation="Test",
            verification_steps="Test"
        )


def test_max_hypotheses_limit_enforced():
    with pytest.raises(ValidationError):
        InvestigationReport(
            incident_summary="Test Summary",
            hypotheses=[
                Hypothesis(
                    rank=1,
                    title=f"Hypothesis {i}",
                    confidence="Low",
                    explanation="Reason",
                    remediation="Fix",
                    verification_steps="Verify"
                )
                for i in range(4)  # 4 hypotheses exceeds max_length=3
            ]
        )
