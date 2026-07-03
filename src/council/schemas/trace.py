"""Deliberation trace schemas (data-model.md §TraceEvent / §DeliberationTrace).

The ordered observability artifact (FR-008) — streamed live to the web UI via
SSE. TraceEvent kinds map 1:1 to the SSE stream kinds (contracts/web-ui.md).
"""
from __future__ import annotations

import logging
from enum import Enum

from pydantic import BaseModel, Field, field_validator

_log = logging.getLogger("council.trace")


class TraceKind(str, Enum):
    recruit = "recruit"
    turn = "turn"
    tool_call = "tool_call"
    guardrail = "guardrail"
    synthesize = "synthesize"
    fallback = "fallback"
    error = "error"


class PanelistTurn(BaseModel):
    """Structured output of one Panelist agent turn (no tools → schema allowed).

    The deliberation loop converts this into a ``DebateTurn`` by attaching the
    round index and panelist name. ``references_prior`` is the A2A signal that
    the turn explicitly rebuts a named prior contribution.
    """

    content: str = Field(..., min_length=1)
    references_prior: bool = False


class DebateTurn(BaseModel):
    """One panelist's contribution in one round (internal transcript unit)."""

    round: int = Field(..., ge=1)
    panelist_name: str = Field(..., min_length=1)
    content: str = Field(..., min_length=1)
    references_prior: bool = False


class TraceEvent(BaseModel):
    ts: float
    kind: TraceKind
    actor: str = Field(..., min_length=1)
    detail: str = Field(..., min_length=1)

    @field_validator("kind", mode="before")
    @classmethod
    def _coerce_kind(cls, v):
        if isinstance(v, TraceKind):
            return v
        if isinstance(v, str) and v in TraceKind._value2member_map_:
            return TraceKind(v)
        raise ValueError(f"unknown trace kind: {v!r}")


class DeliberationTrace(BaseModel):
    events: list[TraceEvent] = Field(default_factory=list)

    def add(self, event: TraceEvent) -> TraceEvent:
        """Append an event, preserving insertion order (ts is informational).

        Also emits a structured log line so every TraceEvent reaches BOTH the
        UI trace drawer (via the SSE stream) and the log (FR-008/T043).
        """
        self.events.append(event)
        _log.info("trace %s actor=%s detail=%s", event.kind.value, event.actor, event.detail)
        return event
