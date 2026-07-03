"""Input guardrail — trust-boundary validation of the user's question (FR-006).

T011 implements the *boundary* layer only: trim/non-empty, length cap, and a
NEEDS_CLARIFICATION outcome for empty / too-short / undecipherable input that
carries ONE focused clarifying question (spec Edge Cases → web UI `clarify`).

The refusal-category logic (regulated advice / unsafe / injection) is added
later in T040 (US3). Injection content is treated as untrusted *content* here
already — it is never executed, only length-checked and passed along; full
injection neutralization/classification lands in T040.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from council.config import MAX_PANEL, MIN_PANEL  # noqa: F401  (re-exported for clamping)

# Boundary limits for the raw question text.
QUESTION_MIN_CHARS = 3
QUESTION_MAX_CHARS = 2000


class GuardOutcome(str, Enum):
    ALLOW = "allow"
    NEEDS_CLARIFICATION = "needs_clarification"
    REFUSE = "refuse"  # populated by T040; kept here so the contract is stable.


@dataclass
class GuardResult:
    outcome: GuardOutcome
    question: str  # normalized text actually carried forward (never raw untrusted cmds)
    reason: str | None = None
    clarifying_question: str | None = None

    @property
    def allowed(self) -> bool:
        return self.outcome is GuardOutcome.ALLOW


def _is_undecipherable(text: str) -> bool:
    """Heuristic: only punctuation/whitespace or no letters at all."""
    return not any(ch.isalpha() for ch in text)


def validate_question(raw: str | None) -> GuardResult:
    """Validate untrusted user input at the trust boundary (FR-006).

    Returns a GuardResult. Empty/too-short/undecipherable → NEEDS_CLARIFICATION
    with one focused clarifying question. Refusal categories are classified by
    `classify_refusal` (T040); this function only does boundary validation.
    """
    if raw is None:
        raw = ""
    # Treat as untrusted content: strip, length-cap, never execute.
    text = raw.strip()[:QUESTION_MAX_CHARS]
    if not text or len(text) < QUESTION_MIN_CHARS:
        return GuardResult(
            outcome=GuardOutcome.NEEDS_CLARIFICATION,
            question=text,
            clarifying_question="Could you share the full question you'd like the council to debate?",
        )
    if _is_undecipherable(text):
        return GuardResult(
            outcome=GuardOutcome.NEEDS_CLARIFICATION,
            question=text,
            clarifying_question="I couldn't find an actual question in that — what dilemma would you like explored?",
        )
    return GuardResult(outcome=GuardOutcome.ALLOW, question=text)


def clamp(value: int, lo: int, hi: int) -> int:
    """Clamp an integer query param to [lo, hi] (FR-009 bounds, server-side)."""
    try:
        v = int(value)
    except (TypeError, ValueError):
        return lo if lo != hi else hi
    return max(lo, min(hi, v))


# ---------------------------------------------------------------------------
# Refusal classification (US3 / FR-005 / FR-006, research R7).
# Deterministic keyword/phrase guardrail — no LLM call (quota-free, offline-
# testable, and a guardrail must be reliable, not probabilistic). Injection
# content is treated as untrusted CONTENT here: it is matched, never executed.
# Per R7 a refusal short-circuits with a visible refusal and NO panel run.
# ---------------------------------------------------------------------------

import re

# Order matters: unsafe first (safety), then injection (clearest override
# signal), then regulated-advice domains. Each pattern is a phrase/keyword that
# is specific enough not to over-fire on legitimate policy questions.
_UNSAFE_PATTERNS = [
    r"\bexplosive\b", r"\bmake a bomb\b", r"\bpipe bomb\b", r"\b(iode|make) .* bomb\b",
    r"\bsynthesi[sz]e .* (weapon|nerve agent|chemical weapon)\b",
    r"\bchemical weapon\b", r"\bnerve agent\b", r"\bmethamphetamine\b",
    r"\bhow (to|do i) .* (firearm|gun|poison)\b",
    r"\bstep[- ]by[- ]step.*(weapon|explosive|bomb|poison|drug)\b",
    r"\b(self[- ]harm|suicide|kill myself)\b",
]

_INJECTION_PATTERNS = [
    r"ignore (your|previous|all) (instructions?|rules)",
    r"disregard (your|all|the) (instructions?|rules)",
    r"you are now (dan|jailbroken|in developer mode)",
    r"(output|reveal|print|show) (me )?(the )?system prompt",
    r"approve everything",
    r"act as if (there are |there\'s )?no rules",
    r"\bjailbreak\b", r"\bdan mode\b", r"\bdeveloper mode\b",
]

# Regulated professional advice — *specific personal* instructions, not general
# policy debate. Matched on instructional phrasing + domain term together.
_FINANCIAL_PATTERNS = [
    r"which (stock|stocks|coin|crypto).*(buy|invest)",
    r"(stock|stocks).*(to buy|to invest|guarantee).*(profit|return|gain)",
    r"(what|which).*(should i|to) (buy|invest in|trade)",
    r"guarantee (me )?(stock|profit|return)",
    r"portfolio (recommendation|for me)",
    r"(recommend|tell me).*(stock|stocks|coin|crypto).*(buy|invest)",
]
_MEDICAL_PATTERNS = [
    r"(what|which) (dosage|dose).*(take|should i)",
    r"should i take.*(medication|insulin|pill|drug)",
    r"(diagnose|prescribe|treat) (me|my)",
    r"(my|a) (illness|condition|symptom).*(should i|what).*take",
    r"medical advice",
]
_LEGAL_PATTERNS = [
    r"should i plead (guilty|innocent)",
    r"represent myself in court",
    r"should i (sue|file for (divorce|bankruptcy))",
    r"(my|this) (case|lawsuit|charge).*(should i|what should)",
    r"legal advice",
]


def _matches_any(text: str, patterns: list[str]) -> str | None:
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return m.group(0)
    return None


def classify_refusal(text: str) -> str | None:
    """Return a refusal reason string if the question is out-of-bounds, else None.

    Detects unsafe content, prompt-injection attempts, and requests for specific
    regulated professional advice (medical / legal / financial). Deterministic
    (no LLM) so the guardrail is reliable and quota-free. Per R7 a match
    short-circuits to a visible refusal with no panel run (FR-005/FR-006).
    """
    if not text:
        return None
    if _matches_any(text, _UNSAFE_PATTERNS):
        return ("Refused: the request asks for unsafe content (weapons, explosives, "
                "or self-harm). The Council does not facilitate harm.")
    if _matches_any(text, _INJECTION_PATTERNS):
        return ("Refused: prompt-injection attempt detected. Injected instructions "
                "are treated as untrusted content and never executed; the guardrails hold.")
    if _matches_any(text, _FINANCIAL_PATTERNS):
        return ("Refused: specific financial/investment advice is regulated professional "
                "advice. The Council debates policy, it does not recommend securities.")
    if _matches_any(text, _MEDICAL_PATTERNS):
        return ("Refused: specific medical advice (dosage, diagnosis, prescription) is "
                "regulated professional advice. Please consult a licensed clinician.")
    if _matches_any(text, _LEGAL_PATTERNS):
        return ("Refused: specific legal advice for your situation is regulated "
                "professional advice. Please consult a licensed attorney.")
    return None
