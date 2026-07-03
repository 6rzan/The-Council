"""FastAPI web server — SSE deliberation stream + static page (T032, FR-017).

Implements contracts/web-ui.md: serves the self-contained ``index.html`` and
``GET /api/deliberate/stream`` emitting SSE events mapped 1:1 from the
deliberation loop's ``StreamEvent`` kinds, plus exactly one terminal event
(``verdict`` / ``refusal`` / ``clarify``). All query params are validated and
clamped to config bounds server-side — the UI's values are never trusted.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, StreamingResponse

from council.app import CouncilApp
from council.config import DEFAULT_PANEL, DEFAULT_PORT, HOST, MAX_PANEL, MAX_ROUNDS, MIN_PANEL
from council.guardrails.input_guard import clamp
from council.orchestration.deliberation import run_deliberation

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_INDEX = _STATIC_DIR / "index.html"

# SSE terminal kinds — exactly one per stream, then the stream closes.
_TERMINAL = {"verdict", "refusal", "clarify"}


def create_app(*, app: CouncilApp | None = None) -> FastAPI:
    """Build the FastAPI app. ``app`` (CouncilApp) is injectable for tests."""
    council_app = app or CouncilApp()
    fastapi = FastAPI(title="The Council", docs_url=None, redoc_url=None, openapi_url=None)

    @fastapi.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return HTMLResponse(_INDEX.read_text(encoding="utf-8"))

    @fastapi.get("/api/deliberate/stream")
    async def deliberate_stream(
        question: str = Query("", description="The question to deliberate"),
        rounds: int = Query(2, ge=1, le=MAX_ROUNDS),
        panel: int = Query(DEFAULT_PANEL, ge=MIN_PANEL, le=MAX_PANEL),
        session_id: str | None = Query(None),
    ):
        # Clamp server-side (never trust the page) — FR-009.
        rounds = clamp(rounds, 1, MAX_ROUNDS)
        panel = clamp(panel, MIN_PANEL, MAX_PANEL)

        session = await council_app.get_or_create_session(session_id=session_id)

        async def event_stream():
            terminal = None
            try:
                async for ev in run_deliberation(council_app, session, question, rounds, panel):
                    payload = json.dumps(ev.data) if ev.data else "{}"
                    yield f"event: {ev.kind}\ndata: {payload}\n\n"
                    if ev.kind in _TERMINAL:
                        terminal = ev.kind
                        break
            except Exception as exc:  # never crash/hang the stream (FR-018 spirit)
                err = json.dumps({"detail": f"{type(exc).__name__}: {exc}"})
                yield f"event: error\ndata: {err}\n\n"
            if terminal is None:
                # safety net: always emit a terminal event so the page can finish
                yield f"event: error\ndata: {json.dumps({'detail': 'stream ended without a terminal event'})}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @fastapi.get("/healthz")
    async def healthz() -> dict:
        return {"ok": True}

    return fastapi
