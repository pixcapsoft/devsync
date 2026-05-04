"""
http_bridge.py - HTTP server fallback for WiFi file transfer.

Serves tracked files/folders as an HTTP file server.
Android can pull files using:
  - Any web browser (browse & download)
  - "Cx File Explorer" or "Solid Explorer" via network
  - Custom fetch if using Termux

This mode does NOT push to Android — it serves so Android can pull.
For automatic push, use ADB mode.
"""

import os
import socket
import threading
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from utils import log_info, log_success, log_error


def get_local_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


class FileServerHandler(BaseHTTPRequestHandler):
    """Serves files and directories over HTTP with a simple browser UI."""

    roots: list[dict] = []   # set by HTTPBridge

    def log_message(self, format, *args):
        # Suppress default server logging; use our own
        pass

    def do_GET(self):
        path = urllib.parse.unquote(self.path.lstrip("/"))

        # Root: list all sync pairs
        if not path or path == "/":
            self._serve_root_index()
            return

        # Try to resolve path within any sync root
        for pair in self.roots:
            local_base = pair["local"]
            name = os.path.basename(local_base.rstrip("/\\"))

            if path == name or path.startswith(name + "/"):
                rel = path[len(name):].lstrip("/")
                full = os.path.join(local_base, rel) if rel else local_base

                if not os.path.exists(full):
                    self._404()
                    return
                if os.path.isdir(full):
                    self._serve_dir(full, path)
                else:
                    self._serve_file(full)
                return

        self._404()

    def _serve_root_index(self):
        """Show root listing of all synced items."""
        items = ""
        for pair in self.roots:
            name = os.path.basename(pair["local"].rstrip("/\\"))
            kind = "📁" if os.path.isdir(pair["local"]) else "📄"
            items += f'<li>{kind} <a href="/{urllib.parse.quote(name)}">{name}</a></li>\n'

        html = self._html_page("DevSync", f"""
        <h1>📱 DevSync File Server</h1>
        <p>These files are available for download:</p>
        <ul>{items}</ul>
        <p style="color:#888;font-size:0.85em">
        Server is running on your PC. Use this page from your Android browser to download files.
        </p>
        """)
        self._respond(200, html, "text/html")

    def _serve_dir(self, full_path: str, url_path: str):
        """Show directory listing."""
        entries = sorted(os.scandir(full_path), key=lambda e: (not e.is_dir(), e.name))
        rows = ""

        if "/" in url_path:
            parent = "/".join(url_path.rstrip("/").split("/")[:-1]) or "/"
            rows += f'<tr><td><a href="/{parent}">⬆ ..</a></td><td></td></tr>\n'

        for entry in entries:
            icon = "📁" if entry.is_dir() else "📄"
            href = f"/{url_path.rstrip('/')}/{urllib.parse.quote(entry.name)}"
            size = ""
            if entry.is_file():
                sz = entry.stat().st_size
                size = self._fmt_size(sz)
            rows += f'<tr><td>{icon} <a href="{href}">{entry.name}</a></td><td>{size}</td></tr>\n'

        html = self._html_page(url_path, f"""
        <h1>📁 {url_path}</h1>
        <table>
        <tr><th>Name</th><th>Size</th></tr>
        {rows}
        </table>
        """)
        self._respond(200, html, "text/html")

    def _serve_file(self, full_path: str):
        """Stream a file for download."""
        try:
            size = os.path.getsize(full_path)
            filename = os.path.basename(full_path)
            log_info(f"  ↓ Android pulling: {filename} ({self._fmt_size(size)})")

            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.send_header("Content-Length", str(size))
            self.end_headers()

            with open(full_path, "rb") as f:
                while chunk := f.read(65536):
                    self.wfile.write(chunk)

            log_success(f"  ✓ Sent: {filename}")
        except Exception as e:
            log_error(f"Error serving {full_path}: {e}")

    def _404(self):
        html = self._html_page("Not Found", "<h1>404 — Not Found</h1>")
        self._respond(404, html, "text/html")

    def _respond(self, code: int, body: str, content_type: str):
        data = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", f"{content_type}; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def _html_page(self, title: str, body: str) -> str:
        return f"""<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — DevSync</title>
<style>
  body {{ font-family: system-ui, sans-serif; padding: 20px; background:#0f0f0f; color:#eee; }}
  a {{ color:#4af; text-decoration:none; }}
  a:hover {{ text-decoration:underline; }}
  table {{ width:100%; border-collapse:collapse; }}
  th, td {{ text-align:left; padding:8px; border-bottom:1px solid #333; }}
  th {{ color:#888; font-size:0.85em; text-transform:uppercase; }}
  h1 {{ font-size:1.4em; margin-bottom:0.5em; }}
</style>
</head>
<body>{body}</body>
</html>"""

    @staticmethod
    def _fmt_size(size: int) -> str:
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


class HTTPBridge:
    """HTTP file server that lets Android pull files from this PC."""

    def __init__(self, port: int = 8765, pairs: list = None):
        self.port = port
        self.pairs = pairs or []
        self._server = None
        FileServerHandler.roots = self.pairs

    def push(self, local_path: str, remote_path: str) -> tuple[bool, str]:
        """In HTTP mode, 'push' just means the file is available to serve."""
        # Nothing to do — the server always serves what's on disk live
        name = os.path.basename(local_path)
        return True, f"{name} available at /{name}"

    def delete_remote(self, remote_path: str) -> tuple[bool, str]:
        return True, "HTTP mode: remote delete not applicable"

    def rename_remote(self, old: str, new: str) -> tuple[bool, str]:
        return True, "HTTP mode: remote rename not applicable"

    def print_access_urls(self):
        ip = get_local_ip()
        print(f"\n  → http://{ip}:{self.port}\n")

    def serve_forever(self):
        """Start the HTTP server (blocking)."""
        FileServerHandler.roots = self.pairs
        self._server = HTTPServer(("0.0.0.0", self.port), FileServerHandler)
        ip = get_local_ip()
        log_success(f"Serving at http://{ip}:{self.port}")
        self._server.serve_forever()

    def start_background(self):
        """Start the HTTP server in a background thread."""
        FileServerHandler.roots = self.pairs
        self._server = HTTPServer(("0.0.0.0", self.port), FileServerHandler)
        thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        thread.start()
        ip = get_local_ip()
        log_success(f"HTTP server running at http://{ip}:{self.port}")

    def stop(self):
        if self._server:
            self._server.shutdown()
