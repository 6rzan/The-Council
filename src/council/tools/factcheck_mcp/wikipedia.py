"""Wikipedia backing calls for the fact-check MCP server (research R3, T022).

Keyless + free. Search via the Action API; citable extract via the REST summary
endpoint. Every call honors ``FACTCHECK_TIMEOUT_S`` so deliberations always
terminate (FR-009). On any error/timeout the helpers return empty/``found:false``
across the tool boundary so the agent degrades the claim to ``uncertain`` (spec
Edge Cases) — they NEVER raise across the boundary.

**Untrusted data (FR-006):** fetched article extracts are length-capped and
returned as plain quoted text. They are never interpolated as instructions.
"""
from __future__ import annotations

import httpx

from council.config import FACTCHECK_TIMEOUT_S

SEARCH_URL = "https://en.wikipedia.org/w/api.php"
SUMMARY_URL = "https://en.wikipedia.org/api/rest_v1/page/summary/{title}"

# Boundary limits for tool arguments (FR-006).
MAX_QUERY_CHARS = 300
MAX_LIMIT = 5
MIN_LIMIT = 1
DEFAULT_LIMIT = 3
MAX_TITLE_CHARS = 200
MAX_EXTRACT_CHARS = 1000  # length-cap untrusted extracts


def _timeout() -> float:
    return FACTCHECK_TIMEOUT_S


def search_encyclopedia(query: str, limit: int = DEFAULT_LIMIT) -> dict:
    """Wikipedia Action API ``list=search``. Returns ``{"results": [...]}``.

    On network/timeout returns ``{"results": []}`` (never raises).
    """
    q = (query or "").strip()
    if not q or len(q) > MAX_QUERY_CHARS:
        return {"results": []}
    try:
        lim = max(MIN_LIMIT, min(MAX_LIMIT, int(limit)))
    except (TypeError, ValueError):
        lim = DEFAULT_LIMIT
    try:
        with httpx.Client(timeout=_timeout()) as client:
            resp = client.get(
                SEARCH_URL,
                params={
                    "action": "query",
                    "list": "search",
                    "srsearch": q,
                    "srlimit": lim,
                    "format": "json",
                    "origin": "*",
                },
            )
            resp.raise_for_status()
            data = resp.json()
        hits = data.get("query", {}).get("search", [])
        return {
            "results": [
                {"title": h.get("title", ""), "snippet": (h.get("snippet") or "")[:500]}
                for h in hits
            ]
        }
    except Exception:
        return {"results": []}


def get_article_summary(title: str) -> dict:
    """Wikipedia REST summary. Returns ``{title,url,extract}`` or ``{found:false}``.

    The ``url`` is the canonical desktop page URL — the citable source recorded
    on the ``Claim``. On missing page / timeout returns ``{"found": false}``.
    """
    t = (title or "").strip()
    if not t or len(t) > MAX_TITLE_CHARS:
        return {"found": False}
    try:
        with httpx.Client(timeout=_timeout()) as client:
            resp = client.get(SUMMARY_URL.format(title=t.replace(" ", "_")))
            if resp.status_code == 404:
                return {"found": False}
            resp.raise_for_status()
            data = resp.json()
    except Exception:
        return {"found": False}
    url = (data.get("content_urls") or {}).get("desktop", {}).get("page")
    if not url:
        url = f"https://en.wikipedia.org/wiki/{t.replace(' ', '_')}"
    extract = (data.get("extract") or "")[:MAX_EXTRACT_CHARS]
    return {
        "title": data.get("title") or t,
        "url": url,
        # Plain quoted text — untrusted, never executed as instructions (FR-006).
        "extract": extract,
    }
