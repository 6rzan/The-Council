# Contract: Fact-Check MCP Server

The **single required MCP integration** (Principle III). A local server spoken over **stdio**,
implemented in `src/council/tools/factcheck_mcp/server.py` using the `mcp` SDK. Consumed by the
Fact-Checker agent via ADK `MCPToolset(StdioServerParameters(command="python", args=["-m",
"council.tools.factcheck_mcp.server"]))`. Least-privilege: only the Fact-Checker receives it.

## Tool: `search_encyclopedia`

Find candidate encyclopedia articles for a query.

- **Input**: `{ "query": string (1..300 chars), "limit": integer = 3 (1..5) }`
- **Output**: `{ "results": [ { "title": string, "snippet": string } ] }`
- **Backing call**: Wikipedia Action API `list=search` on `en.wikipedia.org/w/api.php`.
- **Errors**: on network/timeout (> `FACTCHECK_TIMEOUT_S`) returns `{ "results": [] }` (never raises
  across the tool boundary) so the agent degrades the claim to `uncertain`.

## Tool: `get_article_summary`

Fetch a citable extract for an article title.

- **Input**: `{ "title": string (1..200 chars) }`
- **Output**: `{ "title": string, "url": string, "extract": string } | { "found": false }`
- **Backing call**: Wikipedia REST `GET /api/rest_v1/page/summary/{title}`.
- **`url`**: canonical `content_urls.desktop.page` — the citable source recorded on the `Claim`.
- **Errors**: missing page → `{ "found": false }`; timeout → same, plus a trace event.

## Boundaries & guarantees

- **Read-only**: no writes, no side effects (aligns with advisory-only scope, Principle IV).
- **Keyless / free**: no credentials; nothing secret crosses the boundary.
- **Typed I/O**: inputs validated at the boundary (FR-006); outputs are JSON-serializable.
- **Timeout-bounded**: every call honors `FACTCHECK_TIMEOUT_S` so deliberations always terminate
  (FR-009).

## Smoke test (FR-014)

A test starts the server, calls both tools against a **mocked** Wikipedia transport, and asserts
the output shapes + the timeout-degradation path. No live network in CI.
