#!/usr/bin/env python3
"""Serve the generated GitHub Pages training site (docs/) on 0.0.0.0:3000."""

from __future__ import annotations

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
import mimetypes
import os
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parent
DOCS_DIR = ROOT / "docs"

mimetypes.add_type("text/markdown; charset=utf-8", ".md")
mimetypes.add_type("application/toml; charset=utf-8", ".toml")
mimetypes.add_type("image/svg+xml", ".svg")


class DocsRequestHandler(SimpleHTTPRequestHandler):
    """Serve static files from docs/ with clean defaults for GitHub Pages paths."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DOCS_DIR), **kwargs)

    def log_message(self, format: str, *args) -> None:
        pass

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        super().end_headers()

    def do_GET(self) -> None:
        parsed = urlsplit(self.path)
        clean_path = unquote(parsed.path)

        if clean_path in ("/api/health", "/health"):
            payload = json.dumps({"status": "ok", "site": "docs"}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
            return

        if clean_path in ("", "/"):
            self.path = "/index.html" + (f"?{parsed.query}" if parsed.query else "")
        else:
            candidate = (DOCS_DIR / clean_path.lstrip("/")).resolve()
            if DOCS_DIR in candidate.parents and not candidate.exists():
                html_candidate = candidate.with_suffix(".html")
                if html_candidate.is_file():
                    self.path = (
                        "/"
                        + str(html_candidate.relative_to(DOCS_DIR))
                        + (f"?{parsed.query}" if parsed.query else "")
                    )

        super().do_GET()


def main() -> None:
    port = int(os.environ.get("PORT", "3000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), DocsRequestHandler)
    print(f"Serving OpsDesk Academy GitHub Pages site from {DOCS_DIR} on http://0.0.0.0:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
