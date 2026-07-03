"""Green-on-main E2E through the web API (T020, FR-014, contracts/web-ui.md).

Drives ``GET /api/deliberate/stream`` with the ASGI TestClient (fake model +
mocked wiki) and asserts the SSE event order:
``recruit``×N → ``turn``/``tool_call`` → ``synthesize`` → terminal ``verdict``
carrying a schema-valid ``VerdictBrief``.
"""
from __future__ import annotations

import json

from council.schemas.verdict import VerdictBrief


def _parse_sse(iter_lines):
    """Yield (event_kind, data_dict) from an SSE byte stream."""
    kind, data_buf = None, []
    for line in iter_lines:
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        if line == "":
            if kind is not None:
                data = json.loads("".join(data_buf)) if data_buf else {}
                yield kind, data
            kind, data_buf = None, []
            continue
        if line.startswith("event:"):
            kind = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            data_buf.append(line.split(":", 1)[1].strip())
    if kind is not None:
        yield kind, json.loads("".join(data_buf)) if data_buf else {}


def test_happy_path_sse_order(web_client):
    with web_client.stream(
        "GET", "/api/deliberate/stream",
        params={"question": "Should a mid-size city ban gas leaf blowers by 2030?", "rounds": 2, "panel": 3},
    ) as r:
        assert r.status_code == 200
        events = list(_parse_sse(r.iter_lines()))

    kinds = [k for k, _ in events]
    # exactly one terminal event, and it is the verdict
    assert kinds[-1] == "verdict"
    assert "refusal" not in kinds and "clarify" not in kinds

    # recruit events come before any turn
    first_turn = kinds.index("turn") if "turn" in kinds else len(kinds)
    assert all(k == "recruit" for k in kinds[:first_turn])
    assert kinds.count("recruit") == 3

    # synthesize immediately precedes the terminal verdict
    assert kinds[-2] == "synthesize"

    # the verdict payload is a schema-valid VerdictBrief
    verdict = VerdictBrief.model_validate(events[-1][1])
    assert verdict.question.startswith("Should a mid-size city")
    assert len(verdict.positions) >= 2
    assert any(p.is_challenger for p in verdict.roster.panelists)
    # no unsupported claim presented as fact (FR-005)
    assert all(c.status != "unsupported" for c in verdict.fact_checks)
