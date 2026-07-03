"""Launcher — starts uvicorn on localhost and opens the browser (T032).

``council`` (console script) or ``python -m council``. Loads config, exits **3**
with a friendly ``.env.example`` pointer when ``GOOGLE_API_KEY`` is missing (the
server never starts without a key), binds localhost only, picks a free port if
the default is busy, and opens the system browser (best-effort).
"""
from __future__ import annotations

import socket
import sys
import webbrowser

import uvicorn

from council.app import has_api_key
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


def _missing_key_message() -> str:
    return (
        "GOOGLE_API_KEY is not set. The Council needs a free Google AI Studio key.\n"
        "  1. Get one at https://aistudio.google.com/apikey\n"
        "  2. Copy config/.env.example to .env  (Windows: copy config\\.env.example .env)\n"
        "  3. Set GOOGLE_API_KEY=<your key> in .env\n"
        "  4. Run `council` again.\n"
        "The server did not start."
    )


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

    if not has_api_key():
        print(_missing_key_message())
        return 3

    port = _find_free_port(port)
    if port != DEFAULT_PORT:
        print(f"Default port {DEFAULT_PORT} busy; using {port} instead.")
    url = f"http://{HOST}:{port}"
    print(f"The Council is starting at {url}  (Ctrl+C to stop)")

    try:
        webbrowser.open(url)  # best-effort
    except Exception:
        pass  # print the URL either way (done above)

    uvicorn.run(create_app(), host=HOST, port=port, log_level="warning" if level != "DEBUG" else "info")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
