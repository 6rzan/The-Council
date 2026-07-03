"""Synthesizer agent — emits the structured Verdict Brief (T030, FR-007).

``output_schema=VerdictBrief`` and NO tools (research R6). The orchestration
loop's ``synthesize_with_retry`` handles the FR-018 retry→degrade path: on an
invalid brief it retries once, then degrades to a minimal well-formed brief
that flags the degradation.
"""
from __future__ import annotations

from google.adk.agents import LlmAgent

from council.agents._instructions import load
from council.schemas.verdict import VerdictBrief

OUTPUT_KEY = "verdict"


def build_synthesizer(model, *, prior_context: str = "") -> LlmAgent:
    """The Verdict Brief author (structured, no tools)."""
    instruction = load("synthesizer")
    if prior_context:
        instruction = (
            "PRIOR SESSION CONTEXT (build on it; do not restate verbatim):\n"
            f"{prior_context}\n\n---\n\n{instruction}"
        )
    return LlmAgent(
        name="synthesizer",
        model=model,
        instruction=instruction,
        output_schema=VerdictBrief,
        output_key=OUTPUT_KEY,
    )
