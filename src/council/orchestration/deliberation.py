"""The bounded deliberation loop (T031, R1).

A deterministic Python app-shell loop drives the ADK agents and threads shared
session state. Order per run: guard → recruit (or fallback) → N rounds ×
panelists (sequential, shared transcript) → fact-check → claim_guard →
synthesize. It enforces ``MAX_ROUNDS``/``MAX_PANEL`` (FR-009) and is exposed as
an async generator of ``StreamEvent``s so the web layer can stream them over
SSE (contracts/web-ui.md maps StreamEvent kinds 1:1 to SSE events).

FR-018 retry-once-then-degrade is implemented in ``recruit_with_fallback``,
``structure_claims_with_retry``, and ``synthesize_with_retry``.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator

from council.agents.factchecker import build_claim_structurer, build_factchecker, build_factcheck_toolset
from council.agents.moderator import OUTPUT_KEY as MOD_KEY, build_moderator, make_guard_callback
from council.agents.panelist import build_panelist
from council.agents.synthesizer import build_synthesizer
from council.app import CouncilApp, run_agent_for_output
from council.config import MAX_PANEL, MAX_ROUNDS, MIN_PANEL, MODEL
from council.guardrails.claim_guard import strike_unsupported
from council.guardrails.input_guard import GuardOutcome, classify_refusal, validate_question
from council.orchestration.fallback import fallback_roster
from council.orchestration import session_state
from council.schemas.claim import Claim, ClaimStatus
from council.schemas.roster import PanelRoster, RosterSource
from council.schemas.trace import DebateTurn, DeliberationTrace, TraceEvent, TraceKind
from council.schemas.verdict import VerdictBrief


@dataclass
class StreamEvent:
    """One streamed event. ``kind`` maps 1:1 to an SSE event name."""
    kind: str
    data: dict[str, Any] = field(default_factory=dict)


# ---------- model/toolset resolution (injection seams for tests) ----------

def resolve_models(binding: Any | None = None) -> dict[str, Any]:
    """Per-role model dict resolved from the active provider (feature 002, FR-008).

    Every role (moderator, panelist, factchecker, structurer, synthesizer)
    receives the SAME resolved model for a run. A zero-arg call resolves the
    effective ``RunBinding`` itself (production path); the web layer passes the
    binding it snapshotted at stream start. When unconfigured, the legacy
    Gemini-string map is returned so offline callers keep working. Google
    resolves to the plain model string — byte-identical to before (FR-014).
    (``SYNTH_MODEL`` in config.py is unused dead code; no separate wiring needed.)
    """
    from council import providers

    if binding is None:
        binding = providers.bind_run()
    if binding is None:
        return {role: MODEL for role in providers.ROLES}
    model = providers.resolve_model(binding)  # one instance, shared across roles
    return {role: model for role in providers.ROLES}


def resolve_factcheck_toolset():
    """Production MCP toolset for the Fact-Checker (None in offline tests)."""
    return build_factcheck_toolset()


# ---------- small helpers ----------

def _now() -> float:
    return time.time()


def _transcript_text(transcript: list[DebateTurn], question: str, round_num: int | None = None) -> str:
    """Render the running transcript as a message for the next panelist/agent."""
    lines = [f"QUESTION: {question}"]
    turns = transcript if round_num is None else [t for t in transcript if t.round < round_num]
    for t in turns:
        rebut = " (rebuttal)" if t.references_prior else ""
        lines.append(f"[Round {t.round}] {t.panelist_name}{rebut}: {t.content}")
    return "\n".join(lines)


def _prior_context_block(session) -> str:
    """Build a prior-session-context block for follow-ups (US2, FR-011).

    Empty on a first run (no prior verdicts). Prepended to the Moderator recruit
    message and threaded into the Synthesizer payload so a follow-up builds on
    earlier deliberation rather than starting cold. Treated as advisory context.
    """
    prior_q = session_state.get_prior_questions(session)
    prior_v = session_state.get_prior_verdicts(session)
    if not prior_v:
        return ""
    lines = ["PRIOR SESSION CONTEXT (reference only if the follow-up relates):"]
    for i, v in enumerate(prior_v):
        q = prior_q[i] if i < len(prior_q) else ""
        lines.append(f"- Prior question: {q!r}")
        lines.append(f"- Prior recommendation: {v.recommendation!r} (confidence: {v.confidence})")
    lines.append("END PRIOR CONTEXT.")
    return "\n".join(lines) + "\n\n"


def _extract_claim_texts(evidence: str) -> list[str]:
    """Heuristic extraction of claim texts from free-form evidence notes."""
    out = []
    for line in evidence.replace("\r", "").split("\n"):
        line = line.strip()
        if not line:
            continue
        for chunk in line.split("Claim:"):
            chunk = chunk.strip()
            if chunk:
                # cut at the next 'Verdict:' marker if present
                idx = chunk.lower().find("verdict:")
                text = chunk[:idx].strip() if idx >= 0 else chunk
                text = text.strip().strip(".").strip("'\"")
                if text:
                    out.append(text[:300])
    return out or [evidence.strip()[:300] or "unverifiable claim"]


# ---------- FR-018 retry-once-then-degrade steps ----------

async def recruit_with_fallback(
    app: CouncilApp, session, model, question: str, panel_size: int, *, message: str | None = None,
) -> tuple[PanelRoster, RosterSource, DeliberationTrace]:
    """Recruit a roster; retry once on invalid output, then fall back (FR-016/FR-018).

    ``question`` drives the guard callback (validation on the raw question);
    ``message`` (default ``question``) is what the Moderator agent processes and
    may carry prior-session context for follow-ups (US2, FR-011).
    """
    trace = DeliberationTrace()
    moderator = build_moderator(model, guard_callback=make_guard_callback(question))
    msg = message if message is not None else question

    async def _attempt() -> PanelRoster | None:
        try:
            _text, structured = await run_agent_for_output(app, moderator, session, msg)
            if structured is None:
                return None
            return PanelRoster.model_validate(structured)
        except Exception:
            return None

    roster = await _attempt()
    if roster is None:
        roster = await _attempt()  # retry once (FR-018)
    if roster is None:
        roster = fallback_roster()
        trace.add(TraceEvent(ts=_now(), kind=TraceKind.fallback, actor="moderator",
                             detail="recruitment failed → deterministic fallback roster"))
        return roster, RosterSource.fallback, trace
    for p in roster.panelists:
        trace.add(TraceEvent(ts=_now(), kind=TraceKind.recruit, actor="moderator",
                             detail=f"recruited {p.name} ({p.expertise})"))
    return roster, RosterSource.recruited, trace


async def structure_claims_with_retry(
    app: CouncilApp, session, model, evidence: str
) -> list[Claim]:
    """Map free-form evidence into typed Claims; retry once, then degrade (FR-018)."""
    structurer = build_claim_structurer(model)

    async def _attempt() -> list[Claim] | None:
        try:
            _text, structured = await run_agent_for_output(app, structurer, session, evidence)
            if not isinstance(structured, list):
                return None
            return [Claim.model_validate(c) for c in structured]
        except Exception:
            return None

    claims = await _attempt()
    if claims is None:
        claims = await _attempt()  # retry once
    if claims is None:
        # degrade: every extracted claim becomes uncertain (FR-018)
        claims = [Claim(text=t, status=ClaimStatus.uncertain) for t in _extract_claim_texts(evidence)]
    return claims


async def synthesize_with_retry(
    app: CouncilApp, session, model, *, question: str, roster: PanelRoster,
    transcript: list[DebateTurn], claims: list[Claim], prior_context: str = "",
) -> VerdictBrief:
    """Synthesize a VerdictBrief; retry once, then degrade to a minimal brief (FR-018)."""
    safe_claims = strike_unsupported(claims)
    payload = json.dumps({
        "question": question,
        "roster": roster.model_dump(),
        "transcript": [t.model_dump() for t in transcript],
        "claims": [c.model_dump() for c in safe_claims],
        "prior_context": prior_context,
    })
    synthesizer = build_synthesizer(model)

    async def _attempt() -> VerdictBrief | None:
        try:
            _text, structured = await run_agent_for_output(app, synthesizer, session, payload)
            if structured is None:
                return None
            return VerdictBrief.model_validate(structured)
        except Exception:
            return None

    brief = await _attempt()
    if brief is None:
        brief = await _attempt()  # retry once
    if brief is None:
        # degrade: minimal well-formed brief flagging the degradation (FR-018)
        positions = [
            {"label": p.name, "strongest_argument": p.stance}
            for p in roster.panelists
        ][: max(2, len(roster.panelists))]
        brief = VerdictBrief(
            question=question,
            roster=roster,
            positions=positions if len(positions) >= 2 else [
                {"label": "for", "strongest_argument": "see transcript"},
                {"label": "against", "strongest_argument": "see transcript"},
            ],
            fact_checks=safe_claims,
            recommendation=(
                "Synthesis was degraded (the model produced an invalid Verdict Brief); "
                "the minimal brief above preserves the roster and fact-checks for review."
            ),
            confidence="low",
            dissents=[],
        )
    return brief


# ---------- the full bounded loop ----------

async def run_deliberation(
    app: CouncilApp,
    session,
    question: str,
    rounds: int,
    panel: int,
    *,
    models: dict[str, Any] | None = None,
    toolset=None,
) -> AsyncIterator[StreamEvent]:
    """Run a full deliberation, yielding StreamEvents (SSE-ready).

    Bounds are enforced: rounds clamped to [1, MAX_ROUNDS], panel to
    [MIN_PANEL, MAX_PANEL]. Terminal event is exactly one of verdict/refusal/clarify.
    """
    models = models if models is not None else resolve_models()
    toolset = toolset if toolset is not None else resolve_factcheck_toolset()
    rounds = max(1, min(MAX_ROUNDS, int(rounds)))
    panel = max(MIN_PANEL, min(MAX_PANEL, int(panel)))

    trace = DeliberationTrace()
    session_state.set_trace(session, trace)

    # --- guard gate (FR-006) ---
    guard = validate_question(question)
    if guard.outcome is GuardOutcome.NEEDS_CLARIFICATION:
        yield StreamEvent("clarify", {"question_back": guard.clarifying_question})
        return
    if guard.outcome is GuardOutcome.REFUSE:
        yield StreamEvent("refusal", {"reason": guard.reason})
        return
    reason = classify_refusal(guard.question)
    if reason:
        trace.add(TraceEvent(ts=_now(), kind=TraceKind.guardrail, actor="moderator", detail=reason))
        yield StreamEvent("guardrail", {"rule": "input_scope", "outcome": "refuse"})
        yield StreamEvent("refusal", {"reason": reason})
        return
    session_state.add_prior_question(session, guard.question)

    # --- recruit (FR-010/FR-016) ---
    # Thread prior-session context into the recruit message for follow-ups (US2).
    prior_block = _prior_context_block(session)
    recruit_msg = prior_block + guard.question if prior_block else guard.question
    roster, source, rtrace = await recruit_with_fallback(
        app, session, models["moderator"], guard.question, panel, message=recruit_msg,
    )
    for e in rtrace.events:
        trace.add(e)
    if source is RosterSource.fallback:
        yield StreamEvent("fallback", {"roster": roster.model_dump()})
    else:
        for p in roster.panelists:
            yield StreamEvent("recruit", {"panelist": p.model_dump()})
    session_state.set_roster(session, roster)

    # --- bounded debate (FR-002/FR-009) ---
    transcript: list[DebateTurn] = []
    for round_num in range(1, rounds + 1):
        for p in roster.panelists:
            agent = build_panelist(models["panelist"], persona=p)
            msg = _transcript_text(transcript, guard.question, round_num) + f"\n\nYOUR TURN (Round {round_num})."
            try:
                _text, structured = await run_agent_for_output(app, agent, session, msg)
                from council.schemas.trace import PanelistTurn
                turn = PanelistTurn.model_validate(structured)
            except Exception:
                # degrade gracefully: a minimal non-empty turn (FR-018 spirit)
                from council.schemas.trace import PanelistTurn
                turn = PanelistTurn(content="(this panelist offered no argument)", references_prior=False)
            dt = DebateTurn(round=round_num, panelist_name=p.name, content=turn.content,
                            references_prior=turn.references_prior)
            transcript.append(dt)
            session_state.append_turn(session, dt)
            trace.add(TraceEvent(ts=_now(), kind=TraceKind.turn, actor=p.name,
                                 detail=f"round {round_num}{' (rebuttal)' if turn.references_prior else ''}"))
            yield StreamEvent("turn", {
                "round": round_num, "panelist_name": p.name,
                "content": turn.content, "references_prior": turn.references_prior,
            })

    # --- fact-check (FR-004) ---
    fc = build_factchecker(models["factchecker"], toolset=toolset)
    try:
        evidence, _struct = await run_agent_for_output(app, fc, session, _transcript_text(transcript, guard.question))
    except Exception:
        evidence = ""
    trace.add(TraceEvent(ts=_now(), kind=TraceKind.tool_call, actor="factchecker",
                         detail="fact-check pass against Wikipedia"))
    yield StreamEvent("tool_call", {"tool": "factcheck_mcp", "query": "fact-check pass"})

    claims = await structure_claims_with_retry(app, session, models["structurer"], evidence)
    session_state.set_claims(session, claims)

    # --- claim guard (FR-005) ---
    before = len(claims)
    claims = strike_unsupported(claims)
    after = len(claims)
    trace.add(TraceEvent(ts=_now(), kind=TraceKind.guardrail, actor="claim_guard",
                         detail=f"strike_unsupported: {before}→{after}"))
    yield StreamEvent("guardrail", {"rule": "strike_unsupported", "outcome": f"{before}→{after}"})

    # --- synthesize (FR-007) ---
    trace.add(TraceEvent(ts=_now(), kind=TraceKind.synthesize, actor="synthesizer", detail="synthesis begins"))
    yield StreamEvent("synthesize", {})
    brief = await synthesize_with_retry(app, session, models["synthesizer"],
                                        question=guard.question, roster=roster,
                                        transcript=transcript, claims=claims,
                                        prior_context=prior_block)
    session_state.set_trace(session, trace)
    session_state.add_prior_verdict(session, brief)
    yield StreamEvent("verdict", brief.model_dump())
