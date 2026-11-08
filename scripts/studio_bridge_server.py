#!/usr/bin/env python3
"""
3D Model & Parametric CAD Studio — Local Studio Bridge Server
Provides a lightweight local HTTP bridge (127.0.0.1:19847) for the Live CAD Studio WebGL viewer:
  1. `GET /ping` -> Health check
  2. `GET /open-bambu?file=<path>` -> Launches Bambu Studio (Flatpak `com.bambulab.BambuStudio` or native binary)
     with the active 3D model (`.3mf` or `.stl`) loaded directly onto the build plate.
  3. `GET /export?file=<path>&format=stl|3mf|obj` -> Exports/converts the active 3D model into `.stl`, `.3mf`, or `.obj`
     and saves a copy directly to `~/Downloads/` (plus returns status JSON for the Live Studio HUD toast).
"""

import json
import os
import shutil
import socket
import subprocess
import sys
import urllib.parse
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Optional

BRIDGE_HOST = "127.0.0.1"
BRIDGE_PORT = 19847

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(SCRIPT_DIR)
CAD_SCRIPTS_DIR = os.path.join(PLUGIN_ROOT, "skills", "parametric-cad-modeling", "scripts")
if CAD_SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, CAD_SCRIPTS_DIR)


def is_port_in_use(port: int = BRIDGE_PORT, host: str = BRIDGE_HOST) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.25)
        return s.connect_ex((host, port)) == 0


def ensure_bridge_running() -> bool:
    """Ensure the background studio bridge daemon is listening on 127.0.0.1:19847."""
    if is_port_in_use(BRIDGE_PORT, BRIDGE_HOST):
        return True
    try:
        subprocess.Popen(
            [sys.executable, os.path.abspath(__file__), "--daemon"],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
        return True
    except Exception:
        return False


def ensure_format_file(src_file: str, fmt: str) -> str:
    """Given an existing mesh path (.stl/.3mf/.obj), ensure the requested format file exists and return its path."""
    fmt = fmt.lower().lstrip(".")
    if fmt not in ("stl", "3mf", "obj"):
        raise ValueError(f"Unsupported format: {fmt}")

    src_abs = os.path.abspath(os.path.expanduser(src_file))
    if not os.path.isfile(src_abs):
        raise FileNotFoundError(f"Source model not found: {src_abs}")

    base, _ = os.path.splitext(src_abs)
    target_path = f"{base}.{fmt}"
    if os.path.isfile(target_path) and os.path.getmtime(target_path) >= os.path.getmtime(src_abs) - 1.0:
        return target_path

    # Convert on the fly using verify_model + cad_engine
    import verify_model
    import cad_engine

    tris = verify_model.load_mesh_triangles(src_abs)
    mesh = cad_engine.ManifoldMeshBuilder()
    for a, b, c in tris:
        mesh.add_triangle(a, b, c)

    if fmt == "stl":
        mesh.export_binary_stl(target_path, solid_name=os.path.basename(base))
    elif fmt == "3mf":
        mesh.export_3mf(target_path, part_name=os.path.basename(base))
    elif fmt == "obj":
        mesh.export_obj(target_path)

    return target_path


def launch_bambu_studio(file_path: str) -> dict:
    """Launch Bambu Studio with the specified 3D model file."""
    src_abs = os.path.abspath(os.path.expanduser(file_path))
    if not os.path.isfile(src_abs):
        return {"status": "error", "message": f"File not found: {src_abs}"}

    # Prefer .stl or .3mf sibling if available
    base, ext = os.path.splitext(src_abs)
    launch_target = src_abs
    if ext.lower() not in (".stl", ".3mf", ".obj", ".step", ".stp"):
        if os.path.isfile(base + ".stl"):
            launch_target = base + ".stl"
        elif os.path.isfile(base + ".3mf"):
            launch_target = base + ".3mf"

    env = os.environ.copy()
    if "DISPLAY" not in env:
        env["DISPLAY"] = ":0"

    # 1. Check native binary in PATH
    bambu_bin = shutil.which("bambu-studio") or shutil.which("BambuStudio")
    if bambu_bin:
        subprocess.Popen(
            [bambu_bin, launch_target],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
        return {
            "status": "ok",
            "launcher": "native",
            "file": launch_target,
            "message": f"Opened {os.path.basename(launch_target)} in Bambu Studio",
        }

    # 2. Check Flatpak com.bambulab.BambuStudio
    flatpak_bin = shutil.which("flatpak") or "/usr/bin/flatpak"
    if os.path.isfile(flatpak_bin):
        cmd = [
            flatpak_bin,
            "run",
            "--branch=stable",
            "--arch=x86_64",
            "--command=entrypoint",
            "--file-forwarding",
            "com.bambulab.BambuStudio",
            "@@",
            launch_target,
            "@@",
        ]
        subprocess.Popen(
            cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
        return {
            "status": "ok",
            "launcher": "flatpak:com.bambulab.BambuStudio",
            "file": launch_target,
            "message": f"Launching Bambu Studio with {os.path.basename(launch_target)}...",
        }

    # 3. Fallback to xdg-open
    xdg_bin = shutil.which("xdg-open")
    if xdg_bin:
        subprocess.Popen(
            [xdg_bin, launch_target],
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
            env=env,
        )
        return {
            "status": "ok",
            "launcher": "xdg-open",
            "file": launch_target,
            "message": f"Opened {os.path.basename(launch_target)} via system handler",
        }

    return {"status": "error", "message": "Bambu Studio executable or Flatpak not found on system."}


class StudioBridgeHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        # Quiet operation
        pass

    def _send_json(self, data: dict, status: int = 200) -> None:
        raw = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(raw)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()
        self.wfile.write(raw)

    def do_OPTIONS(self) -> None:
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.end_headers()

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        qs = urllib.parse.parse_qs(parsed.query)

        if parsed.path == "/ping":
            self._send_json({"status": "ok", "service": "cad-studio-bridge", "port": BRIDGE_PORT})
            return

        if parsed.path == "/open-bambu":
            file_arg = (qs.get("file") or [""])[0]
            if not file_arg:
                self._send_json({"status": "error", "message": "Missing 'file' query parameter"}, 400)
                return
            res = launch_bambu_studio(file_arg)
            self._send_json(res, 200 if res.get("status") == "ok" else 404)
            return

        if parsed.path == "/export":
            file_arg = (qs.get("file") or [""])[0]
            fmt_arg = (qs.get("format") or ["stl"])[0].lower().lstrip(".")
            if not file_arg:
                self._send_json({"status": "error", "message": "Missing 'file' query parameter"}, 400)
                return
            try:
                target_file = ensure_format_file(file_arg, fmt_arg)
                downloads_dir = os.path.expanduser("~/Downloads")
                os.makedirs(downloads_dir, exist_ok=True)
                dest_path = os.path.join(downloads_dir, os.path.basename(target_file))
                if os.path.abspath(target_file) != os.path.abspath(dest_path):
                    shutil.copy2(target_file, dest_path)
                self._send_json({
                    "status": "ok",
                    "format": fmt_arg,
                    "source_file": target_file,
                    "saved_to": dest_path,
                    "display_path": f"~/Downloads/{os.path.basename(target_file)}",
                    "size_bytes": os.path.getsize(dest_path),
                    "message": f"Exported to ~/Downloads/{os.path.basename(target_file)}",
                })
            except Exception as e:
                self._send_json({"status": "error", "message": str(e)}, 500)
            return

        self._send_json({"status": "error", "message": f"Unknown endpoint: {parsed.path}"}, 404)


def run_server() -> None:
    if is_port_in_use(BRIDGE_PORT, BRIDGE_HOST):
        return
    server = HTTPServer((BRIDGE_HOST, BRIDGE_PORT), StudioBridgeHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server()
