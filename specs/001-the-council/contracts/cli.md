# Contract: Command-Line Interface

Primary surface for the MVP and demo (FR-017). Implemented in `src/council/cli/main.py`.

## Invocation

```text
council "<question>"                # one-shot deliberation
council                             # interactive prompt; supports follow-ups (P2)
python -m council "<question>"      # module form (no console script needed)
```

## Options

| Flag | Default | Effect |
|------|---------|--------|
| `--rounds N` | 2 | debate rounds (clamped to `MAX_ROUNDS`) |
| `--panel N` | 3 | target panel size (clamped to `[MIN_PANEL, MAX_PANEL]`) |
| `--no-stream` | off | print final Verdict Brief only (used by tests / plain capture) |
| `--json` | off | also emit the `VerdictBrief` as JSON to stdout (machine-readable) |
| `--trace` | off | print the full `DeliberationTrace` after the brief |

## Behavior (streamed, in order)

1. **Recruiting** — shows the roster as each panelist is summoned, with the recruitment reason;
   if recruitment fails, prints a "using fallback panel" notice (FR-016) and continues.
2. **Debate** — each round, each panelist's turn streams in; rebuttals are visually attributed.
3. **Fact-check** — each checked claim streams with its status badge + source link.
4. **Verdict Brief** — final formatted panel: positions, recommendation, confidence, dissents.

## Refusal path (US3 / FR-005)

For regulated-advice / unsafe / injection inputs: prints a **clear refusal card** explaining why,
runs **no panel**, and exits `2`.

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | Verdict Brief produced |
| 2 | Request refused by guardrails (expected, not an error) |
| 3 | Missing/invalid `GOOGLE_API_KEY` (points user to `.env.example`) |
| 1 | Unexpected internal error (with a friendly message; trace on `--trace`) |

## Non-goals

No accounts/auth, no multi-user, no persistence between process runs (session is per-invocation
or per interactive session only).
