"""Fact-check MCP stdio server (T023, contracts/mcp-factcheck.md).

The **single required MCP integration** (constitution Principle III). A local
server spoken over stdio, consumed by the Fact-Checker agent via ADK
``McpToolset``. Least-privilege: only the Fact-Checker receives this toolset.

Run as a subprocess: ``python -m council.tools.factcheck_mcp.server``.

Tools:
  * ``search_encyclopedia(query, limit=3)`` → ``{"results": [{title, snippet}]}``
  * ``get_article_summary(title)`` → ``{title, url, extract}`` or ``{"found": false}``

Both are read-only, keyless, timeout-bounded, and validate their arguments at
the boundary (FR-006). Wikipedia extracts are untrusted, length-capped, quoted
text — never executed as instructions.
"""
from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from council.tools.factcheck_mcp import wikipedia

mcp: FastMCP = FastMCP("council-factcheck")


@mcp.tool()
def search_encyclopedia(query: str, limit: int = 3) -> dict:
    """Find candidate encyclopedia articles for a query (Wikipedia Action API).

    On network/timeout returns ``{"results": []}`` so the agent degrades the
    claim to ``uncertain`` (never raises across the tool boundary).
    """
    return wikipedia.search_encyclopedia(query, limit)


@mcp.tool()
def get_article_summary(title: str) -> dict:
    """Fetch a citable extract for an article title (Wikipedia REST summary).

    Returns ``{"title", "url", "extract"}`` or ``{"found": false}``.
    """
    return wikipedia.get_article_summary(title)


def main() -> None:
    """Entry point for ``python -m council.tools.factcheck_mcp.server``."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
