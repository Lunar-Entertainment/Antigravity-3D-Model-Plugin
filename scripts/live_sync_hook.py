#!/usr/bin/env python3
"""
3D Model & Parametric CAD Studio — PostToolUse Live Model Sync Hook
Automatically detects whenever any tool call creates or updates an .stl or .obj file
and streams the updated 3D mesh into `<artifactDirectoryPath>/live_model_data.js`
and `<artifactDirectoryPath>/live_cad_studio.html` in real time.
Camera angles and settings in the open viewer remain 100% locked.
"""

import json
import os
import re
import sys
import time
from typing import List, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(SCRIPT_DIR)
CAD_SCRIPTS_DIR = os.path.join(PLUGIN_ROOT, "skills", "parametric-cad-modeling", "scripts")
sys.path.insert(0, CAD_SCRIPTS_DIR)


def find_candidate_mesh_files(payload: dict) -> List[str]:
    candidates: List[str] = []
    raw_str = json.dumps(payload.get("toolCall", {}))

    # Extract any explicit .stl or .obj paths from tool arguments
    for match in re.findall(r'([A-Za-z0-9_./~-]+\.(?:stl|obj))', raw_str, flags=re.IGNORECASE):
        expanded = os.path.expanduser(match)
        if os.path.isabs(expanded) and os.path.isfile(expanded):
            candidates.append(os.path.abspath(expanded))
        else:
            for wp in payload.get("workspacePaths", []) or []:
                joined = os.path.abspath(os.path.join(wp, expanded))
                if os.path.isfile(joined):
                    candidates.append(joined)

    # Also scan workspace root and 1-level subdirectories for recently modified .stl/.obj files (<15s old)
    now = time.time()
    for wp in payload.get("workspacePaths", []) or []:
        if not os.path.isdir(wp):
            continue
        for root, dirs, files in os.walk(wp):
            # Keep scan ultra-fast: skip hidden dirs and deep trees
            dirs[:] = [d for d in dirs if not d.startswith(".") and d not in ("node_modules", "venv", "__pycache__")]
            rel_depth = root[len(wp):].count(os.sep)
            if rel_depth > 2:
                dirs[:] = []
                continue
            for fname in files:
                if fname.lower().endswith((".stl", ".obj")):
                    fpath = os.path.join(root, fname)
                    try:
                        if now - os.path.getmtime(fpath) <= 15.0:
                            candidates.append(os.path.abspath(fpath))
                    except OSError:
                        pass

    # Deduplicate and sort by modification time (newest first)
    unique = list(set(candidates))
    unique.sort(key=lambda p: os.path.getmtime(p) if os.path.exists(p) else 0.0, reverse=True)
    return unique


def main() -> None:
    try:
        raw_input = sys.stdin.read()
        if not raw_input.strip():
            sys.stdout.write("{}\n")
            return
        payload = json.loads(raw_input)
        artifact_dir = payload.get("artifactDirectoryPath")
        if not artifact_dir:
            sys.stdout.write("{}\n")
            return

        candidates = find_candidate_mesh_files(payload)
        if not candidates:
            sys.stdout.write("{}\n")
            return

        newest_mesh = candidates[0]
        mtime = os.path.getmtime(newest_mesh)

        os.makedirs(artifact_dir, exist_ok=True)
        stamp_file = os.path.join(artifact_dir, ".last_cad_sync_state.json")
        if os.path.isfile(stamp_file):
            try:
                with open(stamp_file, "r", encoding="utf-8") as f:
                    last_state = json.load(f)
                if last_state.get("mesh") == newest_mesh and abs(float(last_state.get("mtime", 0)) - mtime) < 1e-4:
                    sys.stdout.write("{}\n")
                    return
            except Exception:
                pass

        import generate_viewer

        live_html_path = os.path.join(artifact_dir, "live_cad_studio.html")
        model_name = os.path.splitext(os.path.basename(newest_mesh))[0].replace("_", " ").title()
        generate_viewer.sync_live_viewer(
            mesh_filepath=newest_mesh,
            output_html=live_html_path,
            title=f"Live CAD Studio — {model_name}",
            subtitle=f"Auto-Synced from {os.path.basename(newest_mesh)} · Camera & Settings Locked",
        )

        with open(stamp_file, "w", encoding="utf-8") as f:
            json.dump({"mesh": newest_mesh, "mtime": mtime, "synced_at": time.time()}, f)

    except Exception:
        # Never block or fail the agent tool loop
        pass

    sys.stdout.write("{}\n")
    sys.stdout.flush()


if __name__ == "__main__":
    main()
