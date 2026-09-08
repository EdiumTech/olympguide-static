"""Run the desktop web viewer: python web/server.py (Python 3.10+, no packages)."""
import argparse
import json
import mimetypes
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit

from catalog import Catalog, DEFAULT_CATALOG, ROOT


def make_handler(catalog):
    bootstrap = json.dumps(catalog.bootstrap, ensure_ascii=False).encode()
    static = ROOT / "static"

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.respond()

        def do_HEAD(self):
            self.respond(head=True)

        def send_data(self, data, content_type, head=False, status=200):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
            self.end_headers()
            if not head:
                try:
                    self.wfile.write(data)
                except (BrokenPipeError, ConnectionResetError, ConnectionAbortedError):
                    pass

        def respond(self, head=False):
            url = urlsplit(self.path)
            path = unquote(url.path)
            if path == "/api/catalog":
                return self.send_data(bootstrap, "application/json; charset=utf-8", head)
            if path == "/api/rules":
                try:
                    data = catalog.query(parse_qs(url.query))
                except ValueError:
                    return self.send_data(b'{"error":"Invalid pagination"}', "application/json", head, 400)
                return self.send_data(json.dumps(data, ensure_ascii=False).encode(), "application/json; charset=utf-8", head)
            if path.startswith("/sources/"):
                source = catalog.sources.get(path.removeprefix("/sources/"))
                if source:
                    file = (catalog.path.parent / source["file"]).resolve()
                    if file.is_relative_to(catalog.path.parent.resolve()) and file.is_file():
                        return self.send_data(file.read_bytes(), mimetypes.guess_type(file.name)[0] or "application/octet-stream", head)
                return self.send_error(404)
            if path in ("/app.js", "/styles.css", "/favicon.svg"):
                file = static / path[1:]
            elif path == "/" or path in ("/universities", "/olympiads", "/fields", "/favorites") or any(path.startswith(prefix) for prefix in ("/universities/", "/olympiads/", "/fields/", "/programs/", "/units/")):
                file = static / "index.html"
            else:
                return self.send_error(404)
            mime = {".js": "text/javascript", ".css": "text/css", ".html": "text/html", ".svg": "image/svg+xml"}[file.suffix]
            self.send_data(file.read_bytes(), mime + "; charset=utf-8", head)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    args = parser.parse_args()
    catalog = Catalog(args.catalog)
    server = ThreadingHTTPServer((args.host, args.port), make_handler(catalog))
    print(f"OlympGuide: http://{args.host}:{server.server_port} | {len(catalog.rules)} rules", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
