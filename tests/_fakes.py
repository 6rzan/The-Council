"""Shared offline test fakes (research R5).

* ``ScriptedLlm`` — a ``BaseLlm`` subclass that returns canned, schema-valid
  responses in order. Each call to ``generate_content_async`` pops the next
  response. Used to drive the real ADK ``Runner`` deterministically offline.
* ``build_happy_path_models()`` — per-agent scripted models for a full
  recruit → debate → fact-check → synthesis run.
* Canned Wikipedia evidence for the mocked MCP transport.

Nothing here touches the network, a key, or a browser.
"""
from __future__ import annotations

import json
from collections.abc import Iterable

from pydantic import PrivateAttr
from google.adk.models import BaseLlm
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.genai import types

# ---- Canned roster (schema-valid PanelRoster) ----
ROSTER = {
    "panelists": [
        {
            "name": "Dr. Ada Economic",
            "expertise": "energy-systems economist",
            "stance": "net-positive economics",
            "recruitment_reason": "quantifies the cost-benefit of the transition",
            "is_challenger": False,
        },
        {
            "name": "Dr. Bo Climate",
            "expertise": "climate policy scientist",
            "stance": "emissions-critical",
            "recruitment_reason": "grounds the emissions case for the ban",
            "is_challenger": False,
        },
        {
            "name": "Vex the Contrarian",
            "expertise": "ratepayer advocate",
            "stance": "affordability skeptic",
            "recruitment_reason": "challenges the consensus on ratepayer cost",
            "is_challenger": True,
        },
    ],
    "source": "recruited",
}

FALLBACK_ROSTER = {
    "panelists": [
        {
            "name": "The Advocate",
            "expertise": "generalist advocate",
            "stance": "favorable",
            "recruitment_reason": "argues the strongest case for the proposal",
            "is_challenger": False,
        },
        {
            "name": "The Skeptic",
            "expertise": "generalist skeptic",
            "stance": "critical",
            "recruitment_reason": "argues the strongest case against the proposal",
            "is_challenger": True,
        },
        {
            "name": "The Pragmatist",
            "expertise": "implementation realist",
            "stance": "pragmatic",
            "recruitment_reason": "weighs feasibility and trade-offs",
            "is_challenger": False,
        },
    ],
    "source": "fallback",
}

# ---- Canned panelist turns (3 panelists x 2 rounds = 6) ----
PANELIST_TURNS = [
    {"content": "Round 1: the economics favor a transition; declining renewable costs make the ban affordable.", "references_prior": False},
    {"content": "Round 1: the emissions case is urgent; two-stroke blowers are disproportionately polluting.", "references_prior": False},
    {"content": "Round 1: but the ratepayer cost falls hardest on small operators; we must challenge the affordability claim.", "references_prior": True},
    {"content": "Round 2: I take the skeptic's cost point, yet phased subsidies offset it; net economics still positive.", "references_prior": True},
    {"content": "Round 2: the emissions data stands; the ban is a measurable climate win.", "references_prior": True},
    {"content": "Round 2: even with subsidies, enforcement costs are real; I maintain my dissent on affordability.", "references_prior": True},
]

# ---- Canned Fact-Checker free-form evidence (free-form text; no tools in tests) ----
FACTCHECKER_EVIDENCE = (
    "Claim: 'Two-stroke leaf blowers emit disproportionate pollutants.' "
    "Verdict: supported. Source title: Leaf blower. URL: https://en.wikipedia.org/wiki/Leaf_blower. "
    "Extract: Two-stroke gasoline leaf blowers emit significant pollutants relative to their size.\n"
    "Claim: 'Renewable energy costs have declined.' "
    "Verdict: supported. Source title: Renewable energy. URL: https://en.wikipedia.org/wiki/Renewable_energy. "
    "Extract: The cost of renewable energy technologies has declined sharply over the past decade.\n"
    "Claim: 'The ban is universally popular.' Verdict: uncertain — no corroborating source found."
)

# ---- Canned structured Claims (output_schema=list[Claim]) ----
CLAIMS = [
    {
        "text": "Two-stroke leaf blowers emit disproportionate pollutants.",
        "status": "supported",
        "source_title": "Leaf blower",
        "source_url": "https://en.wikipedia.org/wiki/Leaf_blower",
        "evidence": "Two-stroke gasoline leaf blowers emit significant pollutants relative to their size.",
    },
    {
        "text": "Renewable energy costs have declined sharply over the past decade.",
        "status": "supported",
        "source_title": "Renewable energy",
        "source_url": "https://en.wikipedia.org/wiki/Renewable_energy",
        "evidence": "The cost of renewable energy technologies has declined sharply over the past decade.",
    },
    {
        "text": "The ban is universally popular.",
        "status": "uncertain",
        "source_title": None,
        "source_url": None,
        "evidence": None,
    },
]

# ---- Canned VerdictBrief ----
VERDICT = {
    "question": "Should a mid-size city ban gas leaf blowers by 2030?",
    "roster": ROSTER,
    "positions": [
        {"label": "Ban", "strongest_argument": "Emissions and declining renewable costs justify a phased ban."},
        {"label": "Don't ban", "strongest_argument": "Ratepayer and enforcement costs fall hardest on small operators."},
    ],
    "fact_checks": CLAIMS,
    "recommendation": "Adopt a phased ban with subsidies, acknowledging ratepayer trade-offs.",
    "confidence": "medium",
    "dissents": [
        {"panelist_name": "Vex the Contrarian", "objection": "Affordability for small operators remains under-addressed."},
    ],
}

# ---- Canned Wikipedia evidence for mocked transport (T015) ----
WIKI_SEARCH = {
    "results": [
        {"title": "Leaf blower", "snippet": "A leaf blower is a gardening tool..."},
        {"title": "Renewable energy", "snippet": "Renewable energy technologies..."},
    ]
}
WIKI_SUMMARY = {
    "title": "Leaf blower",
    "url": "https://en.wikipedia.org/wiki/Leaf_blower",
    "extract": "Two-stroke gasoline leaf blowers emit significant pollutants relative to their size.",
}


class ScriptedLlm(BaseLlm):
    """A fake model that yields canned responses in order (research R5).

    ``responses`` may be ``str`` (returned as a text part) or ``dict``/``list``
    (JSON-encoded, for structured-output agents). Raises if exhausted so tests
    fail loudly on an unexpected extra call.
    """

    model: str = "scripted-fake"
    _responses: list = PrivateAttr(default_factory=list)
    _cursor: int = PrivateAttr(default=0)
    _calls: list = PrivateAttr(default_factory=list)

    def __init__(self, responses: Iterable):
        super().__init__()
        self._responses = list(responses)

    async def generate_content_async(self, llm_request: LlmRequest, stream: bool = False):
        self._calls.append(llm_request)
        if self._cursor >= len(self._responses):
            raise AssertionError("ScriptedLlm exhausted: an agent made an unexpected extra call")
        payload = self._responses[self._cursor]
        self._cursor += 1
        if isinstance(payload, (dict, list)):
            text = json.dumps(payload)
        else:
            text = str(payload)
        yield LlmResponse(
            content=types.Content(role="model", parts=[types.Part(text=text)]),
            turn_complete=True,
            partial=False,
        )

    @property
    def exhausted(self) -> bool:
        return self._cursor >= len(self._responses)


def _llm(payloads):
    return ScriptedLlm(payloads)


def build_happy_path_models() -> dict:
    """Per-agent scripted models for a full happy-path run."""
    return {
        "moderator": _llm([ROSTER]),
        "panelist": _llm(PANELIST_TURNS),
        "factchecker": _llm([FACTCHECKER_EVIDENCE]),
        "structurer": _llm([CLAIMS]),
        "synthesizer": _llm([VERDICT]),
    }


def build_fallback_models() -> dict:
    """Models where the moderator returns an INVALID roster → fallback (FR-016)."""
    return {
        "moderator": _llm([{"panelists": [], "source": "recruited"}]),  # invalid → fallback
        "panelist": _llm(PANELIST_TURNS),
        "factchecker": _llm([FACTCHECKER_EVIDENCE]),
        "structurer": _llm([CLAIMS]),
        "synthesizer": _llm([{**VERDICT, "roster": FALLBACK_ROSTER}]),
    }


# ---- Follow-up run (US2): second verdict explicitly references the prior ----
VERDICT_FOLLOWUP = {
    **VERDICT,
    "question": "Given the phased ban, how should subsidies be targeted at small operators?",
    "recommendation": (
        "Building on the prior phased-ban verdict, target subsidies at the smallest "
        "operators first to address the ratepayer trade-off flagged earlier."
    ),
}


def build_followup_models() -> dict:
    """Per-agent scripted models with enough responses for TWO full runs on one
    session (US2 follow-up E2E). The second verdict references the prior one."""
    return {
        "moderator": _llm([ROSTER, ROSTER]),
        "panelist": _llm(PANELIST_TURNS + PANELIST_TURNS),
        "factchecker": _llm([FACTCHECKER_EVIDENCE, FACTCHECKER_EVIDENCE]),
        "structurer": _llm([CLAIMS, CLAIMS]),
        "synthesizer": _llm([VERDICT, VERDICT_FOLLOWUP]),
    }
