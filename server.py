#!/usr/bin/env python3
"""Minimal stdlib HTTP server for the error-discovery review app."""
import json
import shutil
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "error_discovery_data"
BACKUPS = DATA / "backups"
APP_HTML = ROOT / "app.html"

FILES = {
    "/api/samples": "samples.json",
    "/api/annotations": "annotations.json",
    "/api/graph": "graph.json",
    "/api/patterns": "patterns.json",
    "/api/suggestions": "suggestions.json",
}


def reset_for_demo():
    """Back up annotations.json and suggestions.json with a timestamp, then clear
    all annotation highlights and dismiss all pending suggestions so the traces
    render as a blank slate."""
    BACKUPS.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")

    ann_path = DATA / "annotations.json"
    sugg_path = DATA / "suggestions.json"

    if ann_path.exists():
        shutil.copy(ann_path, BACKUPS / f"annotations.{ts}.json")
    if sugg_path.exists():
        shutil.copy(sugg_path, BACKUPS / f"suggestions.{ts}.json")

    ann_path.write_text(json.dumps({}, indent=2))

    suggestions = json.loads(sugg_path.read_text()) if sugg_path.exists() else []
    for sg in suggestions:
        sg["status"] = "dismissed"
    sugg_path.write_text(json.dumps(suggestions, indent=2))

    return ts


class Handler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        pass  # keep stdout quiet

    def _send_json(self, obj, status=200):
        body = json.dumps(obj).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/" or self.path == "/index.html":
            body = APP_HTML.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        if self.path in FILES:
            fp = DATA / FILES[self.path]
            data = json.loads(fp.read_text()) if fp.exists() else ({} if "annotations" in self.path else [])
            self._send_json(data)
            return
        self.send_response(404)
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/reset-demo":
            ts = reset_for_demo()
            self._send_json({"ok": True, "backup_timestamp": ts})
            return
        if self.path in FILES:
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                payload = json.loads(raw)
            except json.JSONDecodeError:
                self._send_json({"error": "invalid json"}, 400)
                return
            fp = DATA / FILES[self.path]
            fp.write_text(json.dumps(payload, indent=2))
            self._send_json({"ok": True})
            return
        self.send_response(404)
        self.end_headers()

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()


if __name__ == "__main__":
    port = 8934
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"error-discovery server running at http://127.0.0.1:{port}")
    server.serve_forever()
