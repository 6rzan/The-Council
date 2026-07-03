# Contract: Web UI + SSE Stream

Primary surface for the MVP and demo (FR-017), revised 2026-07-03 (supersedes the earlier
`cli.md` contract). Implemented in `src/council/web/server.py` (FastAPI app),
`src/council/web/static/index.html` (self-contained page), and `src/council/__main__.py`
(launcher).

## Launcher

```text
council                     # console script
python -m council           # module form (no console script needed)
```

Behavior:

1. Load config (`.env` via `python-dotenv`).
2. If `GOOGLE_API_KEY` is missing/empty → print a friendly message pointing to
   `config/.env.example` and exit **3**. The server MUST NOT start without a key.
3. Start uvicorn on `127.0.0.1` (default port 8400; `--port N` to override; if busy, pick the
   next free port and say so).
4. Open the system browser at the served URL (best-effort — print the URL either way).

The launcher binds to localhost only — the app is single-user and never exposed to the network.

## HTTP endpoints

### `GET /`

Serves `static/index.html` — one self-contained page: **inline CSS and JS only, no CDN, no
external requests, no build step, no JS toolchain**. `EventSource` is the only API it needs.

### `GET /api/deliberate/stream`

The deliberation endpoint. Server-Sent Events (`text/event-stream`).

| Query param | Default | Rule |
|-------------|---------|------|
| `question` | — (required) | untrusted; passes input guardrails (FR-006) before anything runs |
| `rounds` | 2 | clamped to `[1, MAX_ROUNDS]` |
| `panel` | 3 | clamped to `[MIN_PANEL, MAX_PANEL]` |
| `session_id` | new | reuse to continue a session (P2 follow-ups, FR-011); unknown id → new session |

All params are validated/clamped server-side at the trust boundary — the UI's values are never
trusted. Malformed request (missing/empty question after trim) → the stream immediately emits a
terminal `clarify` event (see below); the HTTP status stays 200 so the page renders the card.

## SSE event vocabulary

Each SSE message is `event: <kind>` + `data: <JSON>`. Streamed kinds map **1:1 to `TraceEvent`
kinds** (data-model.md): the `data` payload is the serialized `TraceEvent` plus any
kind-specific fields listed here.

| Event | When | Extra payload fields |
|-------|------|----------------------|
| `recruit` | each panelist summoned | `panelist` (full `Panelist` JSON incl. `recruitment_reason`, `is_challenger`) |
| `fallback` | recruitment failed → deterministic roster substituted (FR-016) | `roster` (`PanelRoster`, `source=fallback`) |
| `turn` | each debate turn completes | `round`, `panelist_name`, `content`, `references_prior` |
| `tool_call` | each MCP fact-check call | `tool`, `query` |
| `guardrail` | each guardrail decision | `rule`, `outcome` |
| `synthesize` | synthesis begins | — |
| `error` | recoverable degradation (e.g. source timeout → claim `uncertain`) | `detail` |

Terminal events (exactly one per stream; the server closes the stream after sending it):

| Event | When | Payload |
|-------|------|---------|
| `verdict` | happy path | the complete `VerdictBrief` JSON |
| `refusal` | guardrail refusal (US3 / FR-005): regulated advice, unsafe, injection | `reason` — shown as the refusal card; **no panel ran** |
| `clarify` | question empty / too short / undecipherable | `question_back` — one focused clarifying question |

Stream order on the happy path: `recruit`×N (or `fallback`) → (`turn` / `tool_call` /
`guardrail` / `error` interleaved per round) → `synthesize` → `verdict`.

## UI requirements (`index.html`)

The page is the demo visual (SC-008). It MUST render:

1. **Question bar** — input + submit; disabled while a deliberation streams.
2. **Panel assembly** — panelist cards appear one-by-one on `recruit`, each showing name,
   expertise, stance, the recruitment reason, and a visible **challenger badge** where
   `is_challenger`. On `fallback`, a clear "using fallback panel" notice (FR-016).
3. **Debate feed** — turns grouped by round; each panelist has a stable **color identity**;
   turns with `references_prior=true` are visually highlighted as rebuttals (the A2A signal).
4. **Fact-checks** — each claim with a status badge (`supported` / `unsupported` / `uncertain`)
   and a clickable source link when present.
5. **Verdict Brief card** — formal final card: positions, recommendation, a **confidence
   meter** (high/medium/low), dissents, and a **Download JSON** button (client-side download of
   the `verdict` payload; no server round-trip).
6. **Trace drawer** — collapsible panel listing every `TraceEvent` in order (FR-008
   observability made visible).
7. **Refusal card** — on `refusal`: prominent card with the reason; no panel/debate UI appears.
8. **Clarify card** — on `clarify`: shows the clarifying question and re-focuses the input.
9. **Follow-ups (P2)** — the page keeps its `session_id` and reuses it on the next question so
   the council can reference prior verdicts (FR-011).

## Refusal path (US3 / FR-005)

For regulated-advice / unsafe / injection inputs: the input guardrail short-circuits **before
any panel runs**; the stream emits only `guardrail` event(s) and the terminal `refusal`. The UI
renders the refusal card. (This replaces the old CLI exit-code-2 contract — process exit codes
now only apply to the launcher: `0` clean shutdown, `3` missing key, `1` unexpected startup
error.)

## Non-goals

No accounts/auth, no multi-user, no HTTPS/remote exposure (localhost only), no persistence —
session state is in-memory for the server process lifetime only (FR-012, Principle VII).
