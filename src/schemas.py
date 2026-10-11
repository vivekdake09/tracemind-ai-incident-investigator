"""Data contracts and validation schemas for TraceMind.

All LLM outputs, diagnostic tool arguments, and investigation reports are
strictly validated against these Pydantic models.
"""

from typing import List, Optional, Literal, Dict, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict


class DiagnosticCheck(BaseModel):
    """A recommended check to test or falsify a root-cause hypothesis."""
    model_config = ConfigDict(extra="ignore")
    
    check_name: str = Field(
        ...,
        description="Concise name of the diagnostic check or command to verify this hypothesis."
    )
    description: str = Field(
        ...,
        description="Clear rationale and instructions on what this check verifies and how to interpret results."
    )


class Hypothesis(BaseModel):
    """A single root-cause hypothesis grounded in retrieved evidence."""
    model_config = ConfigDict(extra="ignore")

    rank: int = Field(
        default=1,
        ge=1,
        le=3,
        description="Rank of plausible cause, where 1 is the most probable hypothesis."
    )
    title: str = Field(
        ...,
        description="Concise descriptive title of the plausible root cause."
    )
    confidence: Literal["High", "Medium", "Low"] = Field(
        ...,
        description="Qualitative confidence label justified by evidence (High, Medium, or Low)."
    )
    explanation: str = Field(
        ...,
        description="Detailed reasoning explaining why this hypothesis fits the incident symptoms and evidence."
    )
    cited_evidence_ids: List[str] = Field(
        default_factory=list,
        description="List of exact document IDs from retrieved evidence supporting this hypothesis."
    )
    diagnostic_checks: List[DiagnosticCheck] = Field(
        default_factory=list,
        description="Recommended non-destructive diagnostic checks to test this hypothesis."
    )
    remediation: str = Field(
        ...,
        description="Proposed remediation action for human engineers to review and approve."
    )
    verification_steps: str = Field(
        ...,
        description="Steps to verify the incident is resolved after remediation is applied."
    )


class InvestigationReport(BaseModel):
    """Structured report returned by the TraceMind investigator."""
    model_config = ConfigDict(extra="ignore")

    incident_summary: str = Field(
        ...,
        description="Executive summary of the incident symptoms, blast radius, and initial findings."
    )
    hypotheses: List[Hypothesis] = Field(
        default_factory=list,
        max_length=3,
        description="Up to three ranked root-cause hypotheses grounded in retrieved records."
    )
    missing_information: Optional[str] = Field(
        default=None,
        description="Missing data, unobserved variables, or contradictory signals needed to confirm diagnosis."
    )
    insufficient_evidence: bool = Field(
        default=False,
        description="True if retrieved knowledge contains no relevant match, mandating safe abstention."
    )
    unmatched_evidence_flags: List[str] = Field(
        default_factory=list,
        description="Validation warnings for cited IDs that failed code-level grounding verification."
    )

    @field_validator("hypotheses")
    @classmethod
    def validate_hypotheses_length(cls, v: List[Hypothesis]) -> List[Hypothesis]:
        if len(v) > 3:
            raise ValueError("A maximum of 3 hypotheses is permitted.")
        return v


# -------------------------------------------------------------------------
# Diagnostic Tool Argument Schemas (whitelisted validation)
# -------------------------------------------------------------------------

class ErrorSignatureArgs(BaseModel):
    logs: str = Field(..., max_length=50000, description="Raw application logs to parse.")


class CheckConfigKeysArgs(BaseModel):
    logs: str = Field(..., max_length=50000, description="Raw logs to inspect for keys.")
    keys: List[str] = Field(..., min_length=1, max_length=20, description="List of config keys to check.")


class SearchIncidentsArgs(BaseModel):
    keyword: str = Field(..., min_length=2, max_length=100, description="Keyword to search in incident history.")
    top_k: int = Field(default=3, ge=1, le=10, description="Number of historical incidents to return.")


class CheckLogPatternArgs(BaseModel):
    logs: str = Field(..., max_length=50000, description="Raw application logs.")
    pattern: str = Field(..., min_length=2, max_length=200, description="Regex or text pattern to locate.")
