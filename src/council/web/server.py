"""FastAPI web server — SSE deliberation stream, provider config API, static page.

Implements contracts/web-ui.md (001) plus feature 002 deltas
(contracts/providers-api.md, contracts/web-ui-v2.md):

* serves ``index.html`` and its same-origin ``static/app.js`` / ``static/style.css``
  (no CDN, no external requests, no build step — research R7);
* ``GET /api/providers`` and ``POST /api/providers/active`` manage the one
  server-wide active provider config (credentials in memory only, never logged);
* ``GET /api/deliberate/stream`` binds the active provider once at stream start,
  emits ``run_config`` as the first event, and — when unconfigured — emits a
  single terminal ``error`` event (HTTP still 200) and closes.

All query params are validated and clamped to config bounds server-side; the
page's values are never trusted (Principle IV). Request bodies are never logged.
"""
from __future__ import annotations

import json
from pathlib import Path

from fastapi import FastAPI, Query
from fastapi.responses import HTMLResponse, JSONResponse, Response, StreamingResponse
from pydantic import BaseModel

from council import providers
from council.app import CouncilApp
from council.config import DEFAULT_PANEL, MAX_PANEL, MAX_ROUNDS, MIN_PANEL
from council.guardrails.input_guard import clamp
from council.orchestration import deliberation

_STATIC_DIR = Path(__file__).resolve().parent / "static"
_INDEX = _STATIC_DIR / "index.html"

# SSE terminal kinds — exactly one per stream, then the stream closes.
_TERMINAL = {"verdict", "refusal", "clarify"}

_ASSETS = {
    "app.js": "application/javascript",
    "style.css": "text/css",
}


class ProviderActiveRequest(BaseModel):
    """Untrusted body for POST /api/providers/active (validated in providers.py)."""

    provider: str
    model: str | None = None
    api_key: str | None = None
    base_url: str | None = None


def _providers_payload() -> dict:
    """The GET /api/providers body (contracts/providers-api.md). No key material."""
    sources = providers.configured_providers()
    active = providers.resolve_effective()
    provs = []
    for pid, spec in providers.PROVIDERS.items():
        provs.append({
            "id": spec.id,
            "display_name": spec.display_name,
            "default_model": spec.default_model,
            "curated_models": list(spec.curated_models),
            "allows_custom_base_url": spec.allows_custom_base_url,
            "requires_key": spec.requires_key,
            "configured": sources[pid] is not None,
            "key_source": sources[pid],
        })
    active_out = None
    if active is not None:
        active_out = {"provider": active.provider_id, "model": active.model, "source": active.source}
    configured_any = active is not None or any(s is not None for s in sources.values())
    return {"providers": provs, "active": active_out, "configured_any": configured_any}


def create_app(*, app: CouncilApp | None = None) -> FastAPI:
    """Build the FastAPI app. ``app`` (CouncilApp) is injectable for tests."""
    council_app = app or CouncilApp()
    fastapi = FastAPI(title="The Council", docs_url=None, redoc_url=None, openapi_url=None)

    @fastapi.get("/", response_class=HTMLResponse)
    async def index() -> HTMLResponse:
        return HTMLResponse(_INDEX.read_text(encoding="utf-8"))

    @fastapi.get("/static/{name}")
    async def static_asset(name: str) -> Response:
        media = _ASSETS.get(name)
        target = (_STATIC_DIR / name).resolve()
        # Same-origin only; never serve outside the static dir.
        if media is None or _STATIC_DIR not in target.parents:
            return Response(status_code=404)
        return Response(target.read_text(encoding="utf-8"), media_type=media)

    @fastapi.get("/api/providers")
    async def list_providers() -> dict:
        return _providers_payload()

    @fastapi.post("/api/providers/active")
    async def set_active_provider(req: ProviderActiveRequest):
        # 1. Structural validation — fails fast with 400, no network.
        try:
            cfg = providers.build_config(req.provider, req.model, req.api_key, req.base_url)
        except providers.ProviderError as err:
            return JSONResponse(status_code=400, content={"error": err.to_dict()})

        # 2. Probe only when a new key/base-URL/provider warrants it.
        prev = providers.get_active()
        need_probe = (
            req.api_key is not None
            or prev is None
            or prev.provider_id != cfg.provider_id
            or prev.base_url != cfg.base_url
        )
        if need_probe:
            try:
                await providers.validate_and_probe(providers.binding_from_config(cfg))
            except providers.ProviderError as err:
                return JSONResponse(status_code=400, content={"error": err.to_dict()})

        # 3. Store (memory only) and report.
        providers.set_active(cfg)
        return {"ok": True, "active": {"provider": cfg.provider_id, "model": cfg.model, "source": cfg.source}}

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
        # Bind the active provider ONCE at stream start (research R4, FR-016).
        binding = providers.bind_run()

        async def event_stream():
            if binding is None:
                detail = ("No AI provider is configured. Open Settings to choose a "
                          "provider and add a key, then ask again.")
                err = json.dumps({"detail": detail, "code": "unconfigured"})
                yield f"event: error\ndata: {err}\n\n"
                return

            # run_config is the FIRST event on every configured stream (Delta 3).
            cfg = json.dumps({"provider": binding.provider_id, "model": binding.model,
                              "panel": panel, "rounds": rounds})
            yield f"event: run_config\ndata: {cfg}\n\n"

            models = deliberation.resolve_models(binding)
            terminal = None
            try:
                async for ev in deliberation.run_deliberation(
                    council_app, session, question, rounds, panel, models=models
                ):
                    payload = json.dumps(ev.data) if ev.data else "{}"
                    yield f"event: {ev.kind}\ndata: {payload}\n\n"
                    if ev.kind in _TERMINAL:
                        terminal = ev.kind
                        break
            except Exception as exc:  # never crash/hang the stream (FR-018 spirit)
                err = json.dumps({"detail": f"{type(exc).__name__}: {exc}"})
                yield f"event: error\ndata: {err}\n\n"
                return
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
