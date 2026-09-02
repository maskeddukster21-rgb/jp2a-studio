#!/usr/bin/env python3
"""jp2a Studio - a local GUI server that wraps the jp2a CLI.

Pure standard library (no pip installs needed). Serves a small web UI on
localhost and shells out to the real `jp2a` binary for every conversion so
you're always looking at genuine jp2a output.
"""
from __future__ import annotations

import base64
import io
import json
import mimetypes
import os
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    Image = None

VERSION = "1.0.0"

# When run from source, static/ lives next to this file. When frozen into a
# PyInstaller onedir build, bundled data lives under sys._MEIPASS instead and
# the real app directory (where we look for a bundled jp2a binary) is next to
# the executable.
if getattr(sys, "frozen", False):
    BASE_DIR = Path(sys._MEIPASS)  # type: ignore[attr-defined]
    APP_DIR = Path(sys.executable).resolve().parent
else:
    BASE_DIR = Path(__file__).resolve().parent
    APP_DIR = BASE_DIR

STATIC_DIR = BASE_DIR / "static"

_bundled_name = "jp2a.exe" if os.name == "nt" else "jp2a"
_bundled_jp2a = APP_DIR / _bundled_name
JP2A_BIN = str(_bundled_jp2a) if _bundled_jp2a.exists() else shutil.which("jp2a")

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
MAX_URL_BYTES = 20 * 1024 * 1024
FETCH_TIMEOUT = 12
JP2A_TIMEOUT = 10

STATIC_FILES = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/style.css": ("style.css", "text/css; charset=utf-8"),
}

CHAR_PRESETS = {
    "default": None,  # jp2a's built-in palette
    "blocks": " .:-=+*#%@",
    "shading": " ░▒▓█",
    "binary": " 01",
    "minimal": " .oO#",
}


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def sanitize_opts(raw: dict) -> dict:
    """Turn untrusted client JSON into a small, bounded, typed options dict."""
    opts = {}

    def as_int(key, default, lo, hi):
        try:
            v = int(raw.get(key, default))
        except (TypeError, ValueError):
            v = default
        return clamp(v, lo, hi)

    def as_float(key, default, lo, hi):
        try:
            v = float(raw.get(key, default))
        except (TypeError, ValueError):
            v = default
        return clamp(v, lo, hi)

    opts["width"] = as_int("width", 100, 10, 300)

    height = raw.get("height")
    opts["height"] = as_int("height", 0, 10, 200) if height not in (None, "", 0, "0") else None

    for flag in ("colors", "fill", "invert", "border", "flipx", "flipy", "edgesOnly"):
        opts[flag] = bool(raw.get(flag))

    opts["edgeThreshold"] = as_float("edgeThreshold", 3.0, 0.0, 30.0)

    preset = raw.get("charPreset", "default")
    if preset not in CHAR_PRESETS:
        preset = "default"
    opts["charPreset"] = preset

    custom_chars = str(raw.get("customChars", ""))[:32]
    # Strip anything that isn't a plain printable character; jp2a needs >=2.
    custom_chars = "".join(ch for ch in custom_chars if 32 <= ord(ch) < 0x110000 and ch != "\n")
    opts["customChars"] = custom_chars

    return opts


def build_jp2a_args(image_path: str, opts: dict) -> list[str]:
    args = [JP2A_BIN, f"--width={opts['width']}"]
    if opts["height"]:
        args.append(f"--height={opts['height']}")
    if opts["invert"]:
        args.append("--invert")
    if opts["border"]:
        args.append("--border")
    if opts["flipx"]:
        args.append("--flipx")
    if opts["flipy"]:
        args.append("--flipy")
    if opts["edgesOnly"]:
        args.append("--edges-only")
    args.append(f"--edge-threshold={opts['edgeThreshold']}")

    chars = None
    if opts["charPreset"] == "custom":
        if len(opts["customChars"]) >= 2:
            chars = opts["customChars"]
    else:
        chars = CHAR_PRESETS.get(opts["charPreset"])
    if chars:
        args.append(f"--chars={chars}")

    if opts["colors"]:
        args.append("--colors")
        args.append("--html-raw")
        if opts["fill"]:
            args.append("--fill")

    args.append(image_path)
    return args


def friendly_command(opts: dict, filename: str) -> str:
    args = build_jp2a_args(filename, opts)
    args[0] = "jp2a"
    return " ".join(args)


def convert_image(image_bytes: bytes, opts: dict, tmp_dir: str) -> dict:
    if not JP2A_BIN:
        return {"ok": False, "error": "jp2a is not installed or not on PATH."}

    # Normalize through Pillow so any format the browser can decode (gif,
    # bmp, tiff, heic-via-pillow, etc.) becomes a PNG that jp2a definitely
    # understands.
    src_path = os.path.join(tmp_dir, f"src_{time.time_ns()}.png")
    try:
        if Image is not None:
            with Image.open(io.BytesIO(image_bytes)) as im:
                im = im.convert("RGBA") if im.mode in ("P", "LA") else im.convert("RGB")
                width, height = im.size
                im.save(src_path, format="PNG")
        else:
            src_path = os.path.join(tmp_dir, f"src_{time.time_ns()}.bin")
            with open(src_path, "wb") as f:
                f.write(image_bytes)
            width = height = None
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": f"Could not read that as an image ({exc})."}

    args = build_jp2a_args(src_path, opts)
    try:
        proc = subprocess.run(
            args, capture_output=True, timeout=JP2A_TIMEOUT
        )
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "jp2a timed out."}
    finally:
        try:
            os.remove(src_path)
        except OSError:
            pass

    if proc.returncode != 0:
        err = proc.stderr.decode("utf-8", "replace").strip() or "jp2a failed."
        return {"ok": False, "error": err}

    raw = proc.stdout.decode("utf-8", "replace")
    result = {
        "ok": True,
        "mode": "html" if opts["colors"] else "plain",
        "command": friendly_command(opts, "image.png"),
        "sourceSize": {"width": width, "height": height},
        "plain_for_copy": None,
    }
    if opts["colors"]:
        normalized = raw.replace("\r\n", "\n")
        result["output"] = normalized.replace("\n", "<br/>")
        # Derive a plain-text copy: turn every line break (both real \n and
        # <br/> tags) into \n *before* stripping tags, or rows collapse together.
        import re

        plain = normalized.replace("<br/>", "\n").replace("<br />", "\n")
        plain = re.sub(r"<[^>]+>", "", plain).replace("&nbsp;", " ")
        result["plain_for_copy"] = plain
    else:
        result["output"] = raw
        result["plain_for_copy"] = raw

    return result


def fetch_url_bytes(url: str) -> bytes:
    if not (url.startswith("http://") or url.startswith("https://")):
        raise ValueError("URL must start with http:// or https://")
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "jp2a-studio/1.0 (local GUI; +https://github.com)"},
    )
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
        data = resp.read(MAX_URL_BYTES + 1)
    if len(data) > MAX_URL_BYTES:
        raise ValueError("Remote image is too large.")
    return data


class Handler(BaseHTTPRequestHandler):
    server_version = "jp2aStudio/1.0"

    def log_message(self, fmt, *args):  # quieter default logging
        pass

    def _send_json(self, payload: dict, status: int = 200):
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?", 1)[0]
        if path in STATIC_FILES:
            fname, ctype = STATIC_FILES[path]
            fpath = STATIC_DIR / fname
            try:
                data = fpath.read_bytes()
            except FileNotFoundError:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)
            return
        if path == "/api/health":
            self._send_json({"ok": True, "jp2a": bool(JP2A_BIN)})
            return
        self.send_error(404)

    def do_POST(self):
        if self.path != "/api/convert":
            self.send_error(404)
            return

        length = int(self.headers.get("Content-Length", 0))
        if length <= 0 or length > MAX_UPLOAD_BYTES + (1024 * 1024):
            self._send_json({"ok": False, "error": "Request too large."}, 413)
            return

        try:
            body = json.loads(self.rfile.read(length))
        except json.JSONDecodeError:
            self._send_json({"ok": False, "error": "Bad request body."}, 400)
            return

        opts = sanitize_opts(body.get("opts", {}))
        source = body.get("source")

        try:
            if source == "upload":
                data_url = body.get("dataUrl", "")
                if "," not in data_url:
                    raise ValueError("No image data received.")
                b64 = data_url.split(",", 1)[1]
                image_bytes = base64.b64decode(b64, validate=False)
                if len(image_bytes) > MAX_UPLOAD_BYTES:
                    raise ValueError("Image is too large (20MB max).")
            elif source == "url":
                image_bytes = fetch_url_bytes(str(body.get("url", "")).strip())
            else:
                raise ValueError("Unknown image source.")
        except (ValueError, urllib.error.URLError, urllib.error.HTTPError) as exc:
            self._send_json({"ok": False, "error": str(exc)})
            return
        except Exception as exc:  # noqa: BLE001
            self._send_json({"ok": False, "error": f"Could not load image ({exc})"})
            return

        with tempfile.TemporaryDirectory(prefix="jp2a_gui_") as tmp_dir:
            result = convert_image(image_bytes, opts, tmp_dir)
        self._send_json(result)


def find_free_port(preferred=8731):
    for port in range(preferred, preferred + 20):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    return 0


def main():
    import argparse

    parser = argparse.ArgumentParser(description="jp2a Studio - a local GUI for jp2a.")
    parser.add_argument("--port", type=int, default=8731, help="preferred port (default: 8731)")
    parser.add_argument("--no-browser", action="store_true", help="don't auto-open a browser tab")
    parser.add_argument("--version", action="version", version=f"jp2a Studio {VERSION}")
    args = parser.parse_args()

    if not JP2A_BIN:
        hint = "install it first: e.g. `sudo apt install jp2a` / `sudo pacman -S jp2a`"
        print(f"WARNING: jp2a was not found ({hint}).")

    port = find_free_port(args.port)
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    url = f"http://127.0.0.1:{port}/"
    print(f"jp2a Studio {VERSION} running at {url}  (Ctrl+C to stop)")
    if not args.no_browser:
        try:
            webbrowser.open(url)
        except Exception:
            pass
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping.")


if __name__ == "__main__":
    main()
