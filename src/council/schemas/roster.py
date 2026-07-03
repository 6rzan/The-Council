"""Panel roster schemas (data-model.md §Panelist / §PanelRoster)."""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field, field_validator, model_validator

from council.config import MAX_PANEL, MIN_PANEL


class RosterSource(str, Enum):
    """How a roster was produced (FR-016)."""

    recruited = "recruited"
    fallback = "fallback"


class Panelist(BaseModel):
    """One recruited expert persona."""

    name: str = Field(..., min_length=1, max_length=60)
    expertise: str = Field(..., min_length=1)
    stance: str = Field(...)
    recruitment_reason: str = Field(..., min_length=1)
    is_challenger: bool = False

    @field_validator("name", "expertise", "stance", "recruitment_reason")
    @classmethod
    def _no_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("must be non-empty")
        return v.strip()


class PanelRoster(BaseModel):
    """The assembled panel for one deliberation."""

    panelists: list[Panelist] = Field(...)
    source: RosterSource = RosterSource.recruited

    @field_validator("panelists")
    @classmethod
    def _bounds(cls, v: list[Panelist]) -> list[Panelist]:
        if not (MIN_PANEL <= len(v) <= MAX_PANEL):
            raise ValueError(f"panel size must be within [{MIN_PANEL},{MAX_PANEL}]")
        return v

    @model_validator(mode="after")
    def _check_challenger_and_uniques(self) -> "PanelRoster":
        if not any(p.is_challenger for p in self.panelists):
            raise ValueError("roster must include at least one challenger (FR-010)")
        names = [p.name for p in self.panelists]
        if len(names) != len(set(names)):
            raise ValueError("panelist names must be unique")
        return self
