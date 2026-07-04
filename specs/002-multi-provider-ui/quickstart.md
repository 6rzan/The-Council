# Quickstart: Multi-Provider Model Choice & Live Deliberation UI

**Feature**: 002-multi-provider-ui | validates SC-001, SC-002, SC-005

## Run it

```bash
pip install -r requirements.txt
council                # or: python -m council
```

The browser opens at `http://127.0.0.1:8400`. With no key configured anywhere the page
shows a **get-started** panel (the server no longer refuses to launch).

## Path A — configure a provider in the UI (SC-001: under 2 minutes)

1. Open **Settings** (or follow the get-started prompt).
2. Pick a provider — Google Gemini, OpenAI, Anthropic, OpenCode Zen, or Custom
   (any OpenAI-compatible endpoint; Custom also needs a base URL).
3. Pick a model from the list or type any model name the provider accepts.
4. Paste the API key (masked immediately; held in server memory only — never on disk).
5. **Save** — the key is validated right away; errors name the cause and the fix.
6. Ask a question. The header chip shows the provider/model powering the run; the stage
   timeline, panelist cards, fact-check badges, and verdict card fill in live.

Switching provider/model between runs is just steps 2–5 again — no restart (SC-002).

## Path B — environment file (existing path, unchanged)

```bash
# .env (gitignored — never commit)
GOOGLE_API_KEY=...          # existing behavior: Gemini default, works as before
# optional non-default env setup:
COUNCIL_PROVIDER=openai     # google | openai | anthropic | opencode | custom
COUNCIL_MODEL=gpt-4o-mini   # optional; provider default otherwise
OPENAI_API_KEY=...          # key var matching the provider
# custom endpoints only:
# COUNCIL_BASE_URL=http://localhost:11434/v1
```

Precedence: UI choice → environment default → built-in default (Gemini). A key entered
in the UI wins for the rest of the process lifetime; restart returns to env config.

## Tests (offline — no key required, SC-005)

```bash
pytest            # full suite: existing 001 tests + new provider/UI tests, all offline
```

New coverage: provider registry + precedence, credential validation error codes,
masking (no key ever appears in a response), one full deliberation on a non-default
provider via fake-model injection, `run_config` SSE contract, static asset serving.

## Demo script outline (SC-006)

1. Start with nothing configured → get-started state.
2. Configure OpenAI in settings (key masked on entry) → save → validated.
3. Ask a question → point at the provider chip, the live stage timeline, panelist
   cards appearing, fact-check badges resolving, then the distinct verdict card.
4. Switch to Gemini in settings → second run → chip updates, no restart.
