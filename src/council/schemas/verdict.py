"""Verdict Brief schemas (data-model.md §VerdictBrief / §Position / §Dissent)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator

from council.schemas.claim import Claim, ClaimStatus
from council.schemas.roster import PanelRoster


class Confidence(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class Position(BaseModel):
    """One distinct side's strongest argument."""

    label: str = Field(..., min_length=1)
    strongest_argument: str = Field(..., min_length=1)


class Dissent(BaseModel):
    """A minority view retained in the brief."""

    panelist_name: str = Field(..., min_length=1)
    objection: str = Field(..., min_length=1)


class VerdictBrief(BaseModel):
    """The final deliverable (FR-007).

    Structured output of the Synthesizer (output_schema=VerdictBrief).
    fact_checks MUST contain only supported/uncertain claims — an unsupported
    claim presented as established fact is a validation error (FR-005).
    """

    question: str = Field(..., min_length=1)
    roster: PanelRoster
    positions: list[Position] = Field(..., min_length=1)
    fact_checks: list[Claim] = Field(default_factory=list)
    recommendation: str = Field(..., min_length=1)
    confidence: Confidence
    dissents: list[Dissent] = Field(default_factory=list)

    @model_validator(mode="after")
    def _no_unsupported_as_fact(self) -> "VerdictBrief":
        for c in self.fact_checks:
            if c.status == ClaimStatus.unsupported:
                raise ValueError(
                    "an unsupported claim cannot appear as established fact (FR-005)"
                )
        return self
