"""Session-state accessors over ADK ``InMemorySessionService`` (plan §Storage).

All deliberation state (transcript, roster, claims, trace, prior questions and
verdicts) lives in the in-memory ADK session's ``state`` dict — nothing is ever
written to disk (FR-012, Principle VII). These helpers keep the key scheme in
one place so the deliberation loop, the web layer, and US2 follow-ups agree.
"""
from __future__ import annotations

from typing import Any

from council.schemas.claim import Claim
from council.schemas.roster import PanelRoster
from council.schemas.trace import DebateTurn, DeliberationTrace
from council.schemas.verdict import VerdictBrief

# Namespaced state keys (single source of truth).
_K = {
    "transcript": "council:transcript",
    "roster": "council:roster",
    "claims": "council:claims",
    "trace": "council:trace",
    "prior_questions": "council:prior_questions",
    "prior_verdicts": "council:prior_verdicts",
}


def _state(session: Any) -> dict[str, Any]:
    """Return the live state dict of an ADK Session (or a plain dict for tests)."""
    state = getattr(session, "state", None)
    if state is None:
        state = session.setdefault("state", {}) if isinstance(session, dict) else {}
    return state


# ---------- transcript ----------

def get_transcript(session: Any) -> list[DebateTurn]:
    raw = _state(session).get(_K["transcript"], [])
    return [DebateTurn.model_validate(t) for t in raw]


def append_turn(session: Any, turn: DebateTurn) -> None:
    state = _state(session)
    raw = list(state.get(_K["transcript"], []))
    raw.append(turn.model_dump())
    state[_K["transcript"]] = raw


# ---------- roster ----------

def get_roster(session: Any) -> PanelRoster | None:
    raw = _state(session).get(_K["roster"])
    return PanelRoster.model_validate(raw) if raw else None


def set_roster(session: Any, roster: PanelRoster) -> None:
    _state(session)[_K["roster"]] = roster.model_dump()


# ---------- claims ----------

def get_claims(session: Any) -> list[Claim]:
    raw = _state(session).get(_K["claims"], [])
    return [Claim.model_validate(c) for c in raw]


def set_claims(session: Any, claims: list[Claim]) -> None:
    _state(session)[_K["claims"]] = [c.model_dump() for c in claims]


# ---------- trace ----------

def get_trace(session: Any) -> DeliberationTrace:
    raw = _state(session).get(_K["trace"])
    return DeliberationTrace.model_validate(raw) if raw else DeliberationTrace()


def set_trace(session: Any, trace: DeliberationTrace) -> None:
    _state(session)[_K["trace"]] = trace.model_dump()


# ---------- prior context (US2, FR-011) ----------

def get_prior_questions(session: Any) -> list[str]:
    return list(_state(session).get(_K["prior_questions"], []))


def add_prior_question(session: Any, question: str) -> None:
    state = _state(session)
    prior = list(state.get(_K["prior_questions"], []))
    prior.append(question)
    state[_K["prior_questions"]] = prior


def get_prior_verdicts(session: Any) -> list[VerdictBrief]:
    raw = _state(session).get(_K["prior_verdicts"], [])
    return [VerdictBrief.model_validate(v) for v in raw]


def add_prior_verdict(session: Any, verdict: VerdictBrief) -> None:
    state = _state(session)
    prior = list(state.get(_K["prior_verdicts"], []))
    prior.append(verdict.model_dump())
    state[_K["prior_verdicts"]] = prior


def reset(session: Any) -> None:
    """Clear all council keys from a session (used by tests)."""
    state = _state(session)
    for k in _K.values():
        state.pop(k, None)


# ---------- typed session context (US2, FR-011) ----------

def get_session_context(session: Any):
    """Return a typed ``SessionContext`` snapshot of the prior questions/verdicts."""
    from council.schemas.session import SessionContext
    return SessionContext(
        prior_questions=get_prior_questions(session),
        prior_verdicts=get_prior_verdicts(session),
    )
