"""Smoke test for the fact-check MCP server tools (T015).

Calls both tools against a mocked Wikipedia transport and asserts the output
shapes plus the timeout→empty degradation path. No live network (contracts/mcp-factcheck.md).
"""
from __future__ import annotations

import httpx

from council.tools.factcheck_mcp import server


def test_search_encyclopedia_returns_results(mock_wikipedia):
    out = server.search_encyclopedia(query="leaf blower", limit=3)
    assert isinstance(out, dict)
    assert isinstance(out["results"], list)
    assert out["results"]
    first = out["results"][0]
    assert {"title", "snippet"} <= set(first.keys())


def test_search_encyclopedia_validates_args(mock_wikipedia):
    # query too long -> clamped/rejected gracefully (boundary validation FR-006)
    out = server.search_encyclopedia(query="x" * 500, limit=3)
    assert out == {"results": []}


def test_get_article_summary_returns_citable_extract(mock_wikipedia):
    out = server.get_article_summary(title="Leaf blower")
    assert out["title"] == "Leaf blower"
    assert out["url"].startswith("https://en.wikipedia.org/")
    assert isinstance(out["extract"], str) and out["extract"]


def test_get_article_summary_missing_page_returns_found_false(monkeypatch):
    from council.tools.factcheck_mcp import wikipedia as wiki

    def fake_get(self, url, **kw):
        r = type("R", (), {"status_code": 404, "json": lambda self: {}, "raise_for_status": lambda self: None})()
        return r

    monkeypatch.setattr(wiki.httpx.Client, "get", fake_get)
    out = server.get_article_summary(title="Nonexistent Page XYZ")
    assert out == {"found": False}


def test_timeout_degrades_to_empty(monkeypatch):
    from council.tools.factcheck_mcp import wikipedia as wiki

    def raise_timeout(self, url, **kw):
        raise httpx.TimeoutException("timed out")

    monkeypatch.setattr(wiki.httpx.Client, "get", raise_timeout)
    assert server.search_encyclopedia(query="x", limit=3) == {"results": []}
    assert server.get_article_summary(title="x") == {"found": False}
