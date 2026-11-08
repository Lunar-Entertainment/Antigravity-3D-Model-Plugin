#!/usr/bin/env python3
"""
3D Model & Parametric CAD Studio — MCP Server (JSON-RPC 2.0 over Stdio)
Provides 4 precision CAD & structural engineering tools:
- cad_calculate_engineering_fit
- cad_generate_parametric_part
- cad_verify_mesh
- cad_render_interactive_viewer
"""

import json
import math
import os
import sys
from typing import Any, Dict, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PLUGIN_ROOT = os.path.dirname(SCRIPT_DIR)
CAD_SCRIPTS_DIR = os.path.join(PLUGIN_ROOT, "skills", "parametric-cad-modeling", "scripts")
sys.path.insert(0, CAD_SCRIPTS_DIR)

import cad_engine
import generate_viewer
import verify_model

# ============================================================================
# Engineering Reference Databases (ISO 273 / DIN 912 / CNC & FDM Calibrated)
# ============================================================================

METRIC_FASTENERS: Dict[str, Dict[str, float]] = {
    "M1.6": {
        "nominal_d": 1.6, "pitch": 0.35,
        "clearance_close": 1.75, "clearance_medium": 1.85, "clearance_free": 2.0,
        "cbore_d": 3.5, "cbore_depth": 1.8, "csink_d": 3.4,
        "nut_flats": 3.4, "nut_thickness": 1.5,
        "heatset_hole_d": 2.6, "heatset_boss_od": 5.2, "heatset_depth": 3.5,
        "selftap_hole_d": 1.4,
    },
    "M2": {
        "nominal_d": 2.0, "pitch": 0.40,
        "clearance_close": 2.2, "clearance_medium": 2.4, "clearance_free": 2.6,
        "cbore_d": 4.4, "cbore_depth": 2.2, "csink_d": 4.2,
        "nut_flats": 4.2, "nut_thickness": 1.8,
        "heatset_hole_d": 3.2, "heatset_boss_od": 6.0, "heatset_depth": 4.0,
        "selftap_hole_d": 1.75,
    },
    "M2.5": {
        "nominal_d": 2.5, "pitch": 0.45,
        "clearance_close": 2.7, "clearance_medium": 2.9, "clearance_free": 3.1,
        "cbore_d": 5.4, "cbore_depth": 2.7, "csink_d": 5.2,
        "nut_flats": 5.2, "nut_thickness": 2.2,
        "heatset_hole_d": 4.0, "heatset_boss_od": 7.0, "heatset_depth": 5.0,
        "selftap_hole_d": 2.2,
    },
    "M3": {
        "nominal_d": 3.0, "pitch": 0.50,
        "clearance_close": 3.2, "clearance_medium": 3.4, "clearance_free": 3.6,
        "cbore_d": 6.2, "cbore_depth": 3.2, "csink_d": 6.4,
        "nut_flats": 5.7, "nut_thickness": 2.6,
        "heatset_hole_d": 4.1, "heatset_boss_od": 8.0, "heatset_depth": 5.8,
        "selftap_hole_d": 2.7,
    },
    "M4": {
        "nominal_d": 4.0, "pitch": 0.70,
        "clearance_close": 4.3, "clearance_medium": 4.5, "clearance_free": 4.8,
        "cbore_d": 8.0, "cbore_depth": 4.2, "csink_d": 8.6,
        "nut_flats": 7.2, "nut_thickness": 3.4,
        "heatset_hole_d": 5.6, "heatset_boss_od": 10.4, "heatset_depth": 7.5,
        "selftap_hole_d": 3.6,
    },
    "M5": {
        "nominal_d": 5.0, "pitch": 0.80,
        "clearance_close": 5.3, "clearance_medium": 5.5, "clearance_free": 5.8,
        "cbore_d": 9.5, "cbore_depth": 5.2, "csink_d": 10.6,
        "nut_flats": 8.2, "nut_thickness": 4.2,
        "heatset_hole_d": 6.4, "heatset_boss_od": 12.0, "heatset_depth": 9.0,
        "selftap_hole_d": 4.5,
    },
    "M6": {
        "nominal_d": 6.0, "pitch": 1.00,
        "clearance_close": 6.4, "clearance_medium": 6.6, "clearance_free": 7.0,
        "cbore_d": 11.0, "cbore_depth": 6.2, "csink_d": 12.8,
        "nut_flats": 10.2, "nut_thickness": 5.2,
        "heatset_hole_d": 8.0, "heatset_boss_od": 15.0, "heatset_depth": 11.5,
        "selftap_hole_d": 5.4,
    },
    "M8": {
        "nominal_d": 8.0, "pitch": 1.25,
        "clearance_close": 8.4, "clearance_medium": 9.0, "clearance_free": 9.5,
        "cbore_d": 14.5, "cbore_depth": 8.2, "csink_d": 17.0,
        "nut_flats": 13.3, "nut_thickness": 6.8,
        "heatset_hole_d": 10.2, "heatset_boss_od": 19.0, "heatset_depth": 14.0,
        "selftap_hole_d": 7.2,
    },
    "M10": {
        "nominal_d": 10.0, "pitch": 1.50,
        "clearance_close": 10.5, "clearance_medium": 11.0, "clearance_free": 12.0,
        "cbore_d": 17.5, "cbore_depth": 10.2, "csink_d": 21.0,
        "nut_flats": 16.3, "nut_thickness": 8.4,
        "heatset_hole_d": 12.5, "heatset_boss_od": 23.0, "heatset_depth": 16.0,
        "selftap_hole_d": 9.0,
    },
    "M12": {
        "nominal_d": 12.0, "pitch": 1.75,
        "clearance_close": 12.5, "clearance_medium": 13.5, "clearance_free": 14.5,
        "cbore_d": 20.5, "cbore_depth": 12.2, "csink_d": 25.0,
        "nut_flats": 18.3, "nut_thickness": 10.4,
        "heatset_hole_d": 14.8, "heatset_boss_od": 27.0, "heatset_depth": 19.0,
        "selftap_hole_d": 10.8,
    },
}

MATERIAL_PROPS: Dict[str, Dict[str, float]] = {
    "PLA": {"shrinkage_pct": 0.25, "max_snap_strain": 0.018, "min_wall_mm": 1.6, "density_g_cm3": 1.24},
    "PETG": {"shrinkage_pct": 0.35, "max_snap_strain": 0.032, "min_wall_mm": 1.6, "density_g_cm3": 1.27},
    "ABS": {"shrinkage_pct": 0.70, "max_snap_strain": 0.028, "min_wall_mm": 2.0, "density_g_cm3": 1.04},
    "ASA": {"shrinkage_pct": 0.65, "max_snap_strain": 0.028, "min_wall_mm": 2.0, "density_g_cm3": 1.07},
    "NYLON": {"shrinkage_pct": 1.10, "max_snap_strain": 0.045, "min_wall_mm": 1.6, "density_g_cm3": 1.14},
    "RESIN": {"shrinkage_pct": 0.40, "max_snap_strain": 0.012, "min_wall_mm": 1.2, "density_g_cm3": 1.18},
    "ALUMINUM_CNC": {"shrinkage_pct": 0.00, "max_snap_strain": 0.004, "min_wall_mm": 1.5, "density_g_cm3": 2.70},
}


def calculate_engineering_fit(args: Dict[str, Any]) -> Dict[str, Any]:
    fastener = str(args.get("fastener_size", "M3")).upper().strip()
    fit_type = str(args.get("fit_type", "snug")).lower().strip()
    material = str(args.get("material", "PLA")).upper().strip()
    nominal_feature_mm = float(args.get("nominal_dimension_mm", 20.0))
    wall_thickness_mm = float(args.get("wall_thickness_mm", 2.4))
    snap_beam_length_mm = float(args.get("snap_beam_length_mm", 14.0))

    mat = MATERIAL_PROPS.get(material, MATERIAL_PROPS["PLA"])
    fast = METRIC_FASTENERS.get(fastener, METRIC_FASTENERS["M3"])

    # Fit clearances (radial and diametral)
    fit_radial_map = {
        "press": 0.03,
        "interference": 0.01,
        "snug": 0.16,
        "transition": 0.16,
        "sliding": 0.22,
        "loose": 0.35,
        "hinge": 0.40,
    }
    radial_gap = fit_radial_map.get(fit_type, 0.16)
    if material in ("ABS", "ASA", "NYLON"):
        radial_gap += 0.04

    # Snap-fit cantilever beam equations:
    # For rectangular cantilever beam of length L and root thickness t_beam:
    # Max allowable deflection y_max = 0.67 * epsilon_max * L^2 / t_beam (with tapered beam factor 1.09)
    t_beam = max(1.2, round(wall_thickness_mm * 0.75, 2))
    eps = mat["max_snap_strain"]
    safe_undercut_mm = round(0.75 * eps * (snap_beam_length_mm ** 2) / t_beam, 2)

    nut_corners = round(fast["nut_flats"] / math.cos(math.pi / 6.0), 3)

    return {
        "fastener_spec": {
            "designation": fastener,
            **fast,
            "nut_across_corners_mm": nut_corners,
            "recommended_min_edge_distance_mm": round(fast["nominal_d"] * 2.0, 2),
        },
        "mating_fit_spec": {
            "fit_class": fit_type,
            "material": material,
            "nominal_dimension_mm": nominal_feature_mm,
            "radial_clearance_per_side_mm": round(radial_gap, 3),
            "diametral_total_clearance_mm": round(2.0 * radial_gap, 3),
            "female_cavity_dimension_mm": round(nominal_feature_mm + 2.0 * radial_gap, 3),
            "male_plug_dimension_mm": round(nominal_feature_mm - 2.0 * radial_gap, 3),
            "shrinkage_compensation_scale_factor": round(1.0 + mat["shrinkage_pct"] / 100.0, 5),
        },
        "structural_sturdiness_spec": {
            "nominal_wall_thickness_mm": wall_thickness_mm,
            "optimal_rib_thickness_mm": round(wall_thickness_mm * 0.65, 2),
            "optimal_internal_fillet_radius_mm": round(max(1.5, wall_thickness_mm * 0.75), 2),
            "recommended_base_chamfer_mm": round(min(1.2, wall_thickness_mm * 0.4), 2),
            "snap_fit_cantilever": {
                "beam_length_mm": snap_beam_length_mm,
                "recommended_beam_root_thickness_mm": t_beam,
                "recommended_taper_tip_thickness_mm": round(t_beam * 0.6, 2),
                "max_safe_undercut_deflection_mm": safe_undercut_mm,
                "entry_ramp_angle_deg": 30.0,
                "retention_return_angle_deg": 60.0,
            },
        },
    }


TOOLS_SCHEMA = [
    {
        "name": "cad_calculate_engineering_fit",
        "description": (
            "Calculate exact mechanical engineering dimensions for 3D models: metric fasteners (M1.6-M10 "
            "clearance holes, counterbores, countersinks, hex nut traps, heat-set insert bosses, self-tap holes), "
            "mating fit clearances (press, snug, sliding, loose, hinge), shrinkage compensation, structural rib "
            "ratios, and snap-fit cantilever beam deflection limits."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "fastener_size": {
                    "type": "string",
                    "description": "Metric fastener size: M1.6, M2, M2.5, M3, M4, M5, M6, M8, or M10",
                },
                "fit_type": {
                    "type": "string",
                    "description": "Fit class: press, snug, sliding, loose, or hinge",
                },
                "material": {
                    "type": "string",
                    "description": "Target material: PLA, PETG, ABS, ASA, NYLON, RESIN, or ALUMINUM_CNC",
                },
                "nominal_dimension_mm": {
                    "type": "number",
                    "description": "Nominal mating feature dimension in mm (default: 20.0)",
                },
                "wall_thickness_mm": {
                    "type": "number",
                    "description": "Nominal structural wall thickness in mm (default: 2.4)",
                },
                "snap_beam_length_mm": {
                    "type": "number",
                    "description": "Cantilever snap-fit beam length in mm (default: 14.0)",
                },
            },
        },
    },
    {
        "name": "cad_init_live_studio",
        "description": (
            "Initialize the real-time 3D CAD Studio Inspector HTML artifact (<artifact_dir>/live_cad_studio.html) "
            "at the very beginning of a 3D modeling task with target [width_x, depth_y, height_z] mm caliper "
            "blueprint dimensions. Subsequent model generations automatically hot-swap the 3D mesh in place "
            "without resetting camera angles or inspector settings."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "target_dimensions_mm": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Target [width_x, depth_y, height_z] bounding dimensions in mm",
                },
                "output_html": {
                    "type": "string",
                    "description": "Absolute path to <artifact_dir>/live_cad_studio.html",
                },
                "title": {
                    "type": "string",
                    "description": "Display title for the Live 3D CAD Studio",
                },
                "subtitle": {
                    "type": "string",
                    "description": "Subtitle describing the model being constructed",
                },
            },
            "required": ["target_dimensions_mm", "output_html"],
        },
    },
    {
        "name": "cad_generate_parametric_part",
        "description": (
            "Generate an exact-dimension, 100% watertight manifold 3D model (.stl, .3mf, .scad, .obj) from "
            "12 parametric engineering templates: 'enclosure_box', 'enclosure_lid', 'l_bracket', 'flanged_spacer', "
            "'grid_organizer', 'mounting_plate', 'spur_gear', 'saddle_clamp', 'bearing_pillow_block', "
            "'pcb_standoff_frame', 'dovetail_rail_mount', or 'threaded_fastener'. Streams live stage updates if live_viewer_html is set."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "part_type": {
                    "type": "string",
                    "enum": list(cad_engine.GENERATORS.keys()),
                    "description": "Parametric template name",
                },
                "parameters": {
                    "type": "object",
                    "description": "Exact dimensional parameters in mm for the template",
                },
                "output_stl": {
                    "type": "string",
                    "description": "Absolute path for the output .stl file",
                },
                "output_scad": {
                    "type": "string",
                    "description": "Optional absolute path for the output .scad OpenSCAD script",
                },
                "output_obj": {
                    "type": "string",
                    "description": "Optional absolute path for the output .obj mesh",
                },
                "output_3mf": {
                    "type": "string",
                    "description": "Optional absolute path for the output .3mf package (Bambu Studio / OrcaSlicer ready)",
                },
                "live_viewer_html": {
                    "type": "string",
                    "description": "Optional path to <artifact_dir>/live_cad_studio.html to stream live model updates into",
                },
                "stream_stages_delay_sec": {
                    "type": "number",
                    "description": "Optional delay in seconds between construction stages for live visual streaming (e.g. 0.4)",
                },
            },
            "required": ["part_type", "output_stl"],
        },
    },
    {
        "name": "cad_verify_mesh",
        "description": (
            "Run a comprehensive engineering, bore/thread metrology, & DFM quality audit on any .stl, .obj, or .3mf 3D model: "
            "verifies manifold watertightness (0 open/non-manifold edges, Euler characteristic, floating shell check), "
            "automatically detects cylindrical holes and ISO metric threads (center XY, min/max diameter, Z span), "
            "checks exact bounding box against target dimensions, and optionally auto-repairs mesh defects."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "filepath": {
                    "type": "string",
                    "description": "Absolute path to the .stl, .obj, or .3mf mesh file",
                },
                "target_dimensions_mm": {
                    "type": "array",
                    "items": {"type": "number"},
                    "description": "Optional [width_x, depth_y, height_z] target dimensions in mm to verify against",
                },
                "tolerance_mm": {
                    "type": "number",
                    "description": "Allowed dimensional deviation in mm (default: 0.1)",
                },
                "repair_output_stl": {
                    "type": "string",
                    "description": "Optional output .stl path to write an auto-repaired mesh (welds micro-gaps, removes degenerate/duplicate faces, fixes inverted normals)",
                },
            },
            "required": ["filepath"],
        },
    },
    {
        "name": "cad_render_interactive_viewer",
        "description": (
            "Generate an interactive 3D CAD Inspector HTML artifact from an .stl or .obj file with "
            "3D orbit/zoom, caliper bounding-box overlays, Z-height cross-section slicer, wireframe/X-ray, "
            "and DFM overhang heatmap."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "mesh_filepath": {
                    "type": "string",
                    "description": "Absolute path to the .stl or .obj file to visualize",
                },
                "output_html": {
                    "type": "string",
                    "description": "Absolute path for the output .html viewer file",
                },
                "title": {
                    "type": "string",
                    "description": "Display title for the 3D CAD viewer card",
                },
                "subtitle": {
                    "type": "string",
                    "description": "Subtitle / engineering summary shown in the viewer header",
                },
            },
            "required": ["mesh_filepath", "output_html"],
        },
    },
]


def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "cad_calculate_engineering_fit":
        res = calculate_engineering_fit(arguments or {})
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}

    if name == "cad_init_live_studio":
        target_dims = arguments.get("target_dimensions_mm") or [100.0, 70.0, 35.0]
        out_html = str(arguments["output_html"])
        title = str(arguments.get("title", "Live 3D Parametric CAD Studio"))
        subtitle = str(arguments.get("subtitle", "Initializing Parametric Blueprint..."))
        res = generate_viewer.init_blueprint_viewer(target_dims, out_html, title, subtitle)
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}

    if name == "cad_generate_parametric_part":
        part_type = str(arguments["part_type"])
        params = arguments.get("parameters") or {}
        out_stl = str(arguments["output_stl"])
        out_scad = arguments.get("output_scad")
        out_obj = arguments.get("output_obj")
        out_3mf = arguments.get("output_3mf")
        live_html = arguments.get("live_viewer_html")
        delay_sec = float(arguments.get("stream_stages_delay_sec", 0.0))
        res = cad_engine.generate_part(
            part_type, params, out_stl, out_scad, out_obj,
            output_3mf=out_3mf,
            live_viewer_html=live_html, stream_stages_delay_sec=delay_sec
        )
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}

    if name == "cad_verify_mesh":
        filepath = str(arguments["filepath"])
        target_dims = arguments.get("target_dimensions_mm")
        tol = float(arguments.get("tolerance_mm", 0.1))
        repair_out = arguments.get("repair_output_stl")
        res = verify_model.audit_mesh(filepath, target_dims, tol, repair_out=repair_out)
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}

    if name == "cad_render_interactive_viewer":
        mesh_fp = str(arguments["mesh_filepath"])
        out_html = str(arguments["output_html"])
        title = str(arguments.get("title", "Live 3D Parametric CAD Studio"))
        subtitle = str(
            arguments.get("subtitle", "Real-Time Model Stream · Camera & Settings Locked")
        )
        res = generate_viewer.sync_live_viewer(mesh_fp, out_html, title, subtitle)
        return {"content": [{"type": "text", "text": json.dumps(res, indent=2)}]}

    raise ValueError(f"Unknown tool: {name}")


def handle_request(req: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    method = req.get("method", "")
    req_id = req.get("id")

    # Notifications have no id and expect no response
    if req_id is None:
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "serverInfo": {
                    "name": "3d-model-studio-mcp",
                    "version": "1.0.0",
                },
            },
        }

    if method == "ping":
        return {"jsonrpc": "2.0", "id": req_id, "result": {}}

    if method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {"tools": TOOLS_SCHEMA},
        }

    if method == "tools/call":
        params = req.get("params") or {}
        tname = params.get("name", "")
        targs = params.get("arguments") or {}
        try:
            result = handle_tool_call(tname, targs)
            return {"jsonrpc": "2.0", "id": req_id, "result": result}
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "isError": True,
                    "content": [{"type": "text", "text": f"Error executing {tname}: {exc}"}],
                },
            }

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    while True:
        line = sys.stdin.readline()
        if not line:
            break
        stripped = line.strip()
        if not stripped:
            continue
        try:
            req = json.loads(stripped)
            resp = handle_request(req)
            if resp is not None:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
        except Exception as exc:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {exc}"},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
