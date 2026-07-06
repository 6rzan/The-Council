"""Launcher — starts uvicorn on localhost and opens the browser (T032).

``council`` (console script) or ``python -m council``. Loads config, binds
localhost only, picks a free port if the default is busy, and opens the system
browser (best-effort).

Feature 002: the server now starts even when no provider is configured — a key
is entered in the page's Settings panel (get-started state), so "no key in .env"
is a normal first-run state, not an error. The old exit-3 gate is retired; exit
codes 0 (clean shutdown) and 1 (unexpected startup error) remain.
"""
from __future__ import annotations

import socket
import sys
import webbrowser

import uvicorn

from council.app import any_provider_configured
from council.config import DEFAULT_PORT, HOST
from council.logging_config import configure_logging
from council.web.server import create_app


def _find_free_port(preferred: int) -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind((HOST, preferred))
            return preferred
        except OSError:
            # fall back to an OS-chosen free port
            s.bind((HOST, 0))
            return s.getsockname()[1]


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    port = DEFAULT_PORT
    if "--port" in argv:
        try:
            port = int(argv[argv.index("--port") + 1])
        except (ValueError, IndexError):
            print("--port requires an integer argument")
            return 1
    # T043: --quiet (WARNING) / --verbose (DEBUG); default INFO.
    level = "WARNING" if "--quiet" in argv else ("DEBUG" if "--verbose" in argv else "INFO")
    configure_logging(level)

    port = _find_free_port(port)
    if port != DEFAULT_PORT:
        print(f"Default port {DEFAULT_PORT} busy; using {port} instead.")
    url = f"http://{HOST}:{port}"
    print(f"The Council is starting at {url}  (Ctrl+C to stop)")
    if not any_provider_configured():
        print("No AI provider configured yet — open the page and use Settings to add one "
              "(free Google AI Studio key: https://aistudio.google.com/apikey).")

    try:
        webbrowser.open(url)  # best-effort
    except Exception:
        pass  # print the URL either way (done above)

    uvicorn.run(create_app(), host=HOST, port=port, log_level="warning" if level != "DEBUG" else "info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
