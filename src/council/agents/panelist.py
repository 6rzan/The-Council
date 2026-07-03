"""Panelist agent — persona-parameterized debater factory (T027).

Each recruited persona gets a Panelist agent with the persona injected into the
instruction. No tools → ``output_schema=PanelistTurn`` is allowed (research R6).
The deliberation loop runs one Panelist per panelist per round, threading the
running transcript so panelists can rebut each other (A2A, spec US1 #4).
"""
from __future__ import annotations

import re

from google.adk.agents import LlmAgent

from council.agents._instructions import load
from council.schemas.roster import Panelist
from council.schemas.trace import PanelistTurn

OUTPUT_KEY = "turn"


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    if not slug or not slug[0].isalpha():
        slug = f"p_{slug}"
    # must be a valid Python identifier (ADK requirement)
    return slug or "panelist"


def _render_instruction(persona: Panelist) -> str:
    tmpl = load("panelist")
    return (
        tmpl.replace("{persona_name}", persona.name)
        .replace("{persona_expertise}", persona.expertise)
        .replace("{persona_stance}", persona.stance)
        .replace("{persona_recruitment_reason}", persona.recruitment_reason)
        .replace("{persona_is_challenger}", "yes" if persona.is_challenger else "no")
    )


def build_panelist(model, *, persona: Panelist) -> LlmAgent:
    """A persona-parameterized debater returning ``{content, references_prior}``."""
    return LlmAgent(
        name=f"panelist_{_slug(persona.name)}",
        model=model,
        instruction=_render_instruction(persona),
        output_schema=PanelistTurn,
        output_key=OUTPUT_KEY,
        # No tools — structured output is allowed (research R6).
    )
