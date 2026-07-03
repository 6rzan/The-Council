"""Unit tests for the Pydantic schemas (data-model.md rules).

Covers: challenger-required, panel bounds, unique names, claim
source-required-when-supported. (T014)
"""
import pytest
from pydantic import ValidationError

from council.config import MIN_PANEL, MAX_PANEL
from council.schemas.roster import PanelRoster, Panelist, RosterSource
from council.schemas.claim import Claim, ClaimStatus
from council.schemas.verdict import VerdictBrief, Position, Dissent, Confidence
from council.schemas.trace import TraceEvent, DeliberationTrace


def _panelist(name="A", challenger=False):
    return Panelist(
        name=name,
        expertise="e",
        stance="s",
        recruitment_reason="r",
        is_challenger=challenger,
    )


# ---------- Panelist ----------

def test_panelist_rejects_empty_name():
    with pytest.raises(ValidationError):
        Panelist(name=" ", expertise="e", stance="s", recruitment_reason="r", is_challenger=False)


def test_panelist_name_cap_60():
    Panelist(name="x" * 60, expertise="e", stance="s", recruitment_reason="r", is_challenger=False)
    with pytest.raises(ValidationError):
        Panelist(name="x" * 61, expertise="e", stance="s", recruitment_reason="r", is_challenger=False)


# ---------- PanelRoster ----------

def test_roster_requires_at_least_one_challenger():
    with pytest.raises(ValidationError):
        PanelRoster(panelists=[_panelist("A"), _panelist("B")], source=RosterSource.recruited)


def test_roster_accepts_with_challenger():
    r = PanelRoster(panelists=[_panelist("A"), _panelist("B", challenger=True)], source=RosterSource.recruited)
    assert any(p.is_challenger for p in r.panelists)


def test_roster_rejects_too_few_panelists():
    with pytest.raises(ValidationError):
        PanelRoster(panelists=[_panelist("A", challenger=True)], source=RosterSource.recruited)


def test_roster_rejects_too_many_panelists():
    panelists = [_panelist(chr(65 + i), challenger=(i == 0)) for i in range(MAX_PANEL + 1)]
    with pytest.raises(ValidationError):
        PanelRoster(panelists=panelists, source=RosterSource.recruited)


def test_roster_bounds_match_config():
    assert (MIN_PANEL, MAX_PANEL) == (2, 4)


def test_roster_rejects_duplicate_names():
    panelists = [_panelist("Same", challenger=True), _panelist("Same")]
    with pytest.raises(ValidationError):
        PanelRoster(panelists=panelists, source=RosterSource.recruited)


def test_roster_source_fallback_allowed():
    r = PanelRoster(panelists=[_panelist("A", challenger=True), _panelist("B")], source=RosterSource.fallback)
    assert r.source == RosterSource.fallback


# ---------- Claim ----------

def test_claim_uncertain_needs_no_source():
    c = Claim(text="x", status=ClaimStatus.uncertain)
    assert c.source_title is None and c.source_url is None


def test_claim_supported_requires_source():
    with pytest.raises(ValidationError):
        Claim(text="x", status=ClaimStatus.supported)
    c = Claim(text="x", status=ClaimStatus.supported, source_title="T", source_url="https://en.wikipedia.org/x")
    assert c.source_url.startswith("https://")


def test_claim_unsupported_requires_source():
    with pytest.raises(ValidationError):
        Claim(text="x", status=ClaimStatus.unsupported)
    Claim(text="x", status=ClaimStatus.unsupported, source_title="T", source_url="https://en.wikipedia.org/y")


def test_claim_supported_rejects_non_wikipedia_url():
    with pytest.raises(ValidationError):
        Claim(text="x", status=ClaimStatus.supported, source_title="T", source_url="https://example.org/y")


# ---------- VerdictBrief ----------

def test_verdict_brief_minimal_valid():
    roster = PanelRoster(panelists=[_panelist("A", challenger=True), _panelist("B")], source=RosterSource.recruited)
    v = VerdictBrief(
        question="q",
        roster=roster,
        positions=[Position(label="for", strongest_argument="a"), Position(label="against", strongest_argument="b")],
        fact_checks=[],
        recommendation="rec",
        confidence=Confidence.medium,
        dissents=[Dissent(panelist_name="B", objection="o")],
    )
    assert v.confidence == Confidence.medium


def test_verdict_brief_rejects_unsupported_as_fact():
    roster = PanelRoster(panelists=[_panelist("A", challenger=True), _panelist("B")], source=RosterSource.recruited)
    bad = Claim(text="x", status=ClaimStatus.unsupported, source_title="T", source_url="https://en.wikipedia.org/z")
    with pytest.raises(ValidationError):
        VerdictBrief(
            question="q", roster=roster,
            positions=[Position(label="a", strongest_argument="a"), Position(label="b", strongest_argument="b")],
            fact_checks=[bad], recommendation="r", confidence=Confidence.low, dissents=[],
        )


# ---------- Trace ----------

def test_trace_event_kinds():
    for k in ["recruit", "turn", "tool_call", "guardrail", "synthesize", "fallback", "error"]:
        TraceEvent(ts=0.0, kind=k, actor="mod", detail="d")
    with pytest.raises(ValidationError):
        TraceEvent(ts=0.0, kind="bogus", actor="x", detail="d")


def test_deliberation_trace_preserves_insertion_order():
    t = DeliberationTrace()
    t.add(TraceEvent(ts=1.0, kind="recruit", actor="M", detail="d1"))
    t.add(TraceEvent(ts=2.0, kind="turn", actor="A", detail="d2"))
    assert [e.kind.value for e in t.events] == ["recruit", "turn"]
