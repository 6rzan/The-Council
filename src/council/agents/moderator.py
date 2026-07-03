"""Moderator (root) agent — guardrail gate + recruit step (T026).

Two responsibilities (contracts/agent-io-schemas.md):
  1. Guardrail gate (``before_agent_callback``): validate the question, refuse
     regulated/unsafe/injection inputs, neutralize injected instructions as
     untrusted content. Returning a ``Content`` short-circuits the agent — the
     model never runs and the loop surfaces a refusal/clarify event.
  2. Recruit step: ``output_schema=PanelRoster`` (research R6 — output_schema is
     allowed here because the Moderator holds NO tools).

FR-016/FR-018 retry→fallback is handled by the orchestration loop's
``recruit_with_fallback``, not by this agent.
"""
from __future__ import annotations

from typing import Callable, Optional

from google.adk.agents import LlmAgent
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from council.agents._instructions import load
from council.guardrails.input_guard import GuardOutcome, classify_refusal, validate_question
from council.schemas.roster import PanelRoster

OUTPUT_KEY = "roster"


def make_guard_callback(question: str) -> Callable[[CallbackContext], Optional[types.Content]]:
    """Build a ``before_agent_callback`` that guards the recruit step.

    Short-circuits (returns Content) on NEEDS_CLARIFICATION or REFUSE so the
    loop can emit the matching terminal SSE event. Returns None to continue.
    """

    def _guard(callback_context: CallbackContext) -> Optional[types.Content]:
        del callback_context  # not used; question is captured via closure
        result = validate_question(question)
        if result.outcome is GuardOutcome.NEEDS_CLARIFICATION:
            return types.Content(
                role="model",
                parts=[types.Part(text=result.clarifying_question or "Could you clarify your question?")],
            )
        if result.outcome is GuardOutcome.REFUSE:
            return types.Content(role="model", parts=[types.Part(text=result.reason or "Request declined.")])
        # ALLOW — run the regulated/unsafe/injection classifier (US3).
        reason = classify_refusal(result.question)
        if reason:
            return types.Content(role="model", parts=[types.Part(text=reason)])
        return None

    return _guard


def build_moderator(
    model,
    *,
    guard_callback: Callable[[CallbackContext], Optional[types.Content]] | None = None,
) -> LlmAgent:
    """The Moderator agent: guard (optional) + recruit (structured PanelRoster)."""
    return LlmAgent(
        name="moderator",
        model=model,
        instruction=load("recruiter"),
        output_schema=PanelRoster,
        output_key=OUTPUT_KEY,
        before_agent_callback=guard_callback,
    )
