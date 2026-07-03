"""Run a single Council agent in isolation (FR-013/FR-015, Principle V).

Proof that each agent is independently addressable and reproducible: drive one
agent turn with a real model and print its structured output. No web server,
no full loop — just one agent over a fresh session.

Usage:
    python scripts/run_one_agent.py moderator   "Should a city ban gas leaf blowers by 2030?"
    python scripts/run_one_agent.py panelist    "Two-stroke blowers pollute. Your turn."
    python scripts/run_one_agent.py factchecker "Claim: leaf blowers emit disproportionate pollutants."
    python scripts/run_one_agent.py synthesizer '<JSON payload>'

Requires a configured GOOGLE_API_KEY (.env). Exits 3 if the key is missing.
"""
from __future__ import annotations

import asyncio
import json
import sys

from council.app import CouncilApp, has_api_key, run_agent_for_output
from council.config import MODEL
from council.agents.factchecker import build_claim_structurer, build_factchecker, build_factcheck_toolset
from council.agents.moderator import build_moderator, make_guard_callback
from council.agents.panelist import build_panelist
from council.agents.synthesizer import build_synthesizer
from council.schemas.roster import PanelRoster


async def _run(agent_name: str, message: str) -> int:
    app = CouncilApp()
    session = await app.create_session()
    if agent_name == "moderator":
        agent = build_moderator(MODEL, guard_callback=make_guard_callback(message))
    elif agent_name == "panelist":
        persona = PanelRoster.model_validate({
            "panelists": [{"name": "Solo Panelist", "expertise": "generalist", "stance": "neutral",
                           "recruitment_reason": "isolated test", "is_challenger": False}], "source": "recruited",
        }).panelists[0]
        agent = build_panelist(MODEL, persona=persona)
    elif agent_name == "factchecker":
        agent = build_factchecker(MODEL, toolset=build_factcheck_toolset())
    elif agent_name == "structurer":
        agent = build_claim_structurer(MODEL)
    elif agent_name == "synthesizer":
        agent = build_synthesizer(MODEL)
    else:
        print(f"unknown agent: {agent_name!r} (try moderator|panelist|factchecker|structurer|synthesizer)")
        return 1

    text, structured = await run_agent_for_output(app, agent, session, message)
    print("=== final text ===")
    print(text)
    if structured is not None:
        print("=== structured output ===")
        print(json.dumps(structured, indent=2, default=str))
    return 0


def main() -> int:
    if not has_api_key():
        print("GOOGLE_API_KEY missing — copy config/.env.example to .env and set your key.")
        return 3
    if len(sys.argv) < 3:
        print(__doc__)
        return 1
    return asyncio.run(_run(sys.argv[1], sys.argv[2]))


if __name__ == "__main__":
    raise SystemExit(main())
