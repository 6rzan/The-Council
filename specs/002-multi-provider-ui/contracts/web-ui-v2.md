# Contract: Web UI v2 — Live Deliberation Experience

**Feature**: 002-multi-provider-ui. Extends `specs/001-the-council/contracts/web-ui.md`;
only the deltas below supersede it — everything not mentioned (SSE vocabulary, terminal
semantics, `/api/deliberate/stream` params, refusal path) is unchanged and binding.

## Delta 1 — Static assets (supersedes "inline CSS and JS only")

`GET /` serves `index.html`, which may load **same-origin** `static/app.js` and
`static/style.css` (served by the FastAPI app). Retained invariants: **no CDN, no
external requests of any kind, no build step, no JS toolchain**. Each of the three
files stays under 500 lines (repo rule). `EventSource` + `fetch` are the only APIs used.

## Delta 2 — Launcher (supersedes exit-3 gate)

The launcher starts the server even when no provider is configured anywhere; exit code 3
is retired (0 = clean shutdown, 1 = unexpected startup error remain). The missing-key
guidance moves into the page's get-started state.

## Delta 3 — New SSE event: `run_config`

Every stream emits `run_config` as its **first** event:

```
event: run_config
data: {"provider": "openai", "model": "gpt-4o", "panel": 3, "rounds": 2}
```

Additive only — clients of the 001 vocabulary that ignore unknown kinds keep working.
If no provider is configured, the stream instead emits a single terminal `error` event
(providers-api.md) and closes.

## UI requirements (the demo visual — SC-006)

The page MUST render, in priority order:

1. **Stage timeline** — a persistent stepper: *Assembling panel → Debate (round N of M)
   → Fact-check → Synthesis → Verdict*, derived client-side from event kinds
   (data-model.md mapping). The active stage is visually alive (continuous CSS
   animation) so no active run ever shows a dead screen (FR-010, SC-003); stage changes
   render within 2 s of the event (FR-009, SC-003 — immediate on event receipt).
2. **Provider chip** — active provider + model from `run_config`, visible in the header
   during and after the run (FR-011).
3. **Settings panel** — slide-over or modal, openable anytime, driven by
   `GET /api/providers`: provider select, model select with free-text override, key
   input (`type="password"`, masked once entered — FR-006), base-URL field only for
   `custom`, "configured via environment" badge with no key reveal (US1 #4), Save →
   `POST /api/providers/active` with inline typed errors (`message` + `hint`) rendered
   in the panel (US1 #3, #5). Runs are blocked with a pointer to exactly what is
   missing while unconfigured (US1 #5).
4. **Get-started state** — shown when `configured_any` is false: brief welcome,
   one-click path into the settings panel, link text for obtaining a free Google AI
   Studio key (content moved from the old launcher exit-3 message).
5. **Panelist cards** — appear one-by-one on `recruit`; name, expertise, stance,
   recruitment reason, challenger badge, stable per-panelist color identity; fallback
   notice on `fallback` (all carried over from 001).
6. **Debate feed** — turns grouped by round in persona-attributed cards (US2 #2);
   `references_prior=true` highlighted as rebuttals (001).
7. **Fact-check badges** — claim status (`supported` / `unsupported` / `uncertain`) +
   source link (001; US2 #3).
8. **Verdict card** — visually distinct terminal card (positions, recommendation,
   confidence meter, dissents, Download JSON) — clearly not "more text in the same
   stream" (US2 #4).
9. **Error card** — on `error`: human-readable cause + suggested next step (FR-012);
   never an infinite spinner (spec edge case).
10. **Trace drawer, refusal card, clarify card, follow-up session reuse** — unchanged
    from 001.

## Behavior notes

- **Browser refresh mid-run**: the EventSource closes and the run is abandoned
  server-side (generator cancellation — existing behavior). The page reloads to idle,
  preserving its `session_id` for follow-ups; no resume is attempted (out of scope).
- **Two tabs**: both see the same server-wide config (last write wins); each run binds
  its config at submission (clarification 2026-07-03).
- Question bar stays disabled while a stream is open (001).

## Test hooks (FR-015 — offline)

- SSE contract test: first event is `run_config` with the active provider/model;
  unconfigured → single terminal `error`.
- Static asset test: `/`, `/static/app.js`, `/static/style.css` all 200, and the HTML
  references only same-origin URLs (no `http(s)://` external references).
- Existing 001 stream tests stay green unmodified (FR-014).
