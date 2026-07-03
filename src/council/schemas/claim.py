"""Claim schemas (data-model.md §Claim)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, model_validator


class ClaimStatus(str, Enum):
    supported = "supported"
    unsupported = "unsupported"
    uncertain = "uncertain"


class Claim(BaseModel):
    """A factual assertion surfaced during debate and its check result.

    Rule (FR-004/FR-005): a Claim with status != supported MUST NOT appear as
    established fact in the Verdict Brief; claim_guard strips such claims.
    """

    text: str = Field(..., min_length=1)
    status: ClaimStatus
    source_title: str | None = None
    source_url: str | None = None
    evidence: str | None = None

    @model_validator(mode="after")
    def _source_required_when_not_uncertain(self) -> "Claim":
        if self.status != ClaimStatus.uncertain:
            if not self.source_title or not self.source_url:
                raise ValueError(
                    "source_title and source_url are required when status != uncertain"
                )
            # Wikipedia is the configured public source (research R3).
            if "wikipedia.org" not in self.source_url:
                raise ValueError("source_url must be a Wikipedia URL")
        return self
