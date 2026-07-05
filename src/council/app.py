"""Runner / SessionService wiring — the app shell's entry into a deliberation.

No agent logic lives here (T012 skeleton). Provides:

* ``make_session_service`` — an ADK ``InMemorySessionService`` (in-memory only,
  FR-012 / Principle VII; nothing is written to disk).
* ``CouncilApp`` — owns the session service + config, resolves the production
  Gemini model, creates/looks-up sessions, and runs a single agent turn via a
  short-lived ``Runner`` (the session service is shared across turns so state
  carries forward within a session).

The fake-model injection path for tests (research R5) does NOT go through here:
tests construct ``LlmAgent`` instances with ``model=FakeLlm(...)`` directly and
call ``CouncilApp.run_agent`` with them, so the offline suite never touches the
network or a key.
"""
from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator

from google.adk.agents import LlmAgent
from google.adk.runners import Runner
from google.adk.sessions import BaseSessionService, InMemorySessionService, Session
from google.genai import types

from council.config import APP_NAME, MODEL, USER_ID, google_api_key


def make_session_service() -> InMemorySessionService:
    """A fresh in-memory session service (nothing persists past the process)."""
    return InMemorySessionService()


def production_model() -> str:
    """The Gemini model string for production agents (research R4)."""
    return MODEL


class CouncilApp:
    """Owns session state and runs individual agent turns (R1 app-shell loop)."""

    def __init__(
        self,
        session_service: BaseSessionService | None = None,
        app_name: str = APP_NAME,
        user_id: str = USER_ID,
    ) -> None:
        self.session_service = session_service or make_session_service()
        self.app_name = app_name
        self.user_id = user_id

    # -- sessions -------------------------------------------------------

    async def create_session(self, session_id: str | None = None) -> Session:
        return await self.session_service.create_session(
            app_name=self.app_name, user_id=self.user_id, session_id=session_id
        )

    async def get_session(self, session_id: str) -> Session | None:
        return await self.session_service.get_session(
            app_name=self.app_name, user_id=self.user_id, session_id=session_id
        )

    async def get_or_create_session(self, session_id: str | None = None) -> Session:
        if session_id:
            existing = await self.get_session(session_id)
            if existing is not None:
                return existing
        return await self.create_session(session_id=session_id)

    # -- agent turns ----------------------------------------------------

    async def run_agent(
        self,
        agent: LlmAgent,
        session: Session,
        message_text: str,
        *,
        state_delta: dict[str, Any] | None = None,
    ) -> AsyncIterator:
        """Run one agent turn over the shared session, yielding ADK Events.

        A short-lived Runner is created per turn (the session service is shared
        so state carries forward). Callers consume the async generator; the
        final event (``event.is_final_response()``) carries structured output
        in ``actions.state_delta[agent.output_key]`` (verified ADK 2.3.0 path).
        """
        runner = Runner(
            app_name=self.app_name,
            agent=agent,
            session_service=self.session_service,
        )
        new_message = types.Content(
            role="user", parts=[types.Part(text=message_text)]
        )
        try:
            async for event in runner.run_async(
                user_id=self.user_id,
                session_id=session.id,
                new_message=new_message,
                state_delta=state_delta,
            ):
                yield event
        finally:
            await runner.close()


def has_api_key() -> bool:
    """True if a GOOGLE_API_KEY is configured (legacy 001 helper; kept for compat)."""
    return google_api_key() is not None


def any_provider_configured() -> bool:
    """True if any provider is usable via UI/env precedence (feature 002 launcher gate).

    The launcher no longer refuses to start without a key — this just informs the
    friendly startup note; the page's get-started state handles the unconfigured case.
    """
    from council import providers

    return providers.resolve_effective() is not None


# Free-tier Gemini caps gemini-2.5-flash at ~5 req/min; a full deliberation fires
# ~10 calls and routinely hits 429 mid-run. Retry transient quota/server errors so
# the run completes with real grounded fact-checks instead of degrading. Offline
# tests inject a fake model that never raises, so this path is never exercised in CI.
_TRANSIENT_MARKERS = ("429", "resource_exhausted", "503", "unavailable", "high demand")


def _is_transient(exc: BaseException) -> bool:
    msg = str(exc).lower()
    return any(m in msg for m in _TRANSIENT_MARKERS)


async def run_agent_for_output(
    app: "CouncilApp",
    agent: LlmAgent,
    session: Session,
    message_text: str,
    *,
    state_delta: dict[str, Any] | None = None,
    max_transient_retries: int = 4,
) -> tuple[str, dict | list | None]:
    """Run one agent turn and return ``(final_text, structured_output)``.

    ``structured_output`` is the parsed dict/list from the final event's
    ``actions.state_delta[agent.output_key]`` when the agent declares an
    ``output_schema`` + ``output_key`` (verified ADK 2.3.0 path), else ``None``.
    Raises ``RuntimeError`` if no final response was produced.

    Retries transient quota/server errors (429/503) with a backoff so a
    free-tier run completes with real grounded output (FR-018 degrade is the
    last resort, not the first).
    """
    backoff = 20.0
    last_exc: BaseException | None = None
    for attempt in range(max_transient_retries + 1):
        try:
            return await _run_once(app, agent, session, message_text, state_delta=state_delta)
        except Exception as exc:
            last_exc = exc
            if not _is_transient(exc) or attempt == max_transient_retries:
                raise
            await asyncio.sleep(backoff)
            backoff = min(backoff + 10.0, 40.0)
    raise RuntimeError(f"agent {agent.name!r} failed after retries") from last_exc


async def _run_once(
    app: "CouncilApp",
    agent: LlmAgent,
    session: Session,
    message_text: str,
    *,
    state_delta: dict[str, Any] | None = None,
) -> tuple[str, dict | list | None]:
    """Single attempt of ``run_agent_for_output`` (no retry)."""
    final_text = ""
    structured: dict | list | None = None
    got_final = False
    async for event in app.run_agent(agent, session, message_text, state_delta=state_delta):
        if event.is_final_response():
            got_final = True
            if event.content and event.content.parts:
                final_text = " ".join(
                    p.text for p in event.content.parts if getattr(p, "text", None)
                )
            delta = event.actions.state_delta or {}
            if agent.output_key and agent.output_key in delta:
                structured = delta[agent.output_key]
    if not got_final:
        raise RuntimeError(f"agent {agent.name!r} produced no final response")
    return final_text, structured
