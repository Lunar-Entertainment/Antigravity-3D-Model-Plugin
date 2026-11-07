#!/usr/bin/env python3
"""
3D Model & Parametric CAD Studio — Universal STL / OBJ Mesh & Dimensional Verifier
Parses Binary STL, ASCII STL, or Wavefront OBJ files and runs an engineering audit:
- Exact Bounding Box (X, Y, Z in mm) & target dimension deviation check
- Watertight / Manifold edge-incidence topology check
- Signed Volume, Surface Area, Center of Mass, and Filament/Metal Mass estimates
- Printability Overhang Audit (>45 deg unsupported downward area)
- Structural Sturdiness Score & Diagnostic Recommendations
"""

import argparse
import json
import math
import os
import struct
import sys
from typing import Dict, List, Optional, Tuple

Point3D = Tuple[float, float, float]
Triangle3D = Tuple[Point3D, Point3D, Point3D]


def snap3d(pt: Point3D, tol: int = 4) -> Point3D:
    return (round(float(pt[0]), tol), round(float(pt[1]), tol), round(float(pt[2]), tol))


def parse_stl(filepath: str) -> List[Triangle3D]:
    with open(filepath, "rb") as f:
        data = f.read()
    if len(data) < 84:
        return []
    # Check if binary STL size matches 84 + 50 * tri_count
    tri_count = struct.unpack("<I", data[80:84])[0]
    if 84 + tri_count * 50 == len(data):
        tris: List[Triangle3D] = []
        offset = 84
        for _ in range(tri_count):
            vals = struct.unpack("<12fH", data[offset : offset + 50])
            p1 = snap3d((vals[3], vals[4], vals[5]))
            p2 = snap3d((vals[6], vals[7], vals[8]))
            p3 = snap3d((vals[9], vals[10], vals[11]))
            tris.append((p1, p2, p3))
            offset += 50
        return tris

    # Fallback: ASCII STL
    text = data.decode("utf-8", errors="ignore")
    tris = []
    curr_verts: List[Point3D] = []
    for line in text.splitlines():
        parts = line.strip().split()
        if len(parts) >= 4 and parts[0].lower() == "vertex":
            curr_verts.append(snap3d((float(parts[1]), float(parts[2]), float(parts[3]))))
            if len(curr_verts) == 3:
                tris.append((curr_verts[0], curr_verts[1], curr_verts[2]))
                curr_verts = []
    return tris


def parse_obj(filepath: str) -> List[Triangle3D]:
    verts: List[Point3D] = []
    tris: List[Triangle3D] = []
    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if parts[0] == "v" and len(parts) >= 4:
                verts.append(snap3d((float(parts[1]), float(parts[2]), float(parts[3]))))
            elif parts[0] == "f" and len(parts) >= 4:
                idxs = []
                for tok in parts[1:]:
                    v_idx = int(tok.split("/")[0])
                    if v_idx < 0:
                        v_idx = len(verts) + 1 + v_idx
                    idxs.append(verts[v_idx - 1])
                for i in range(1, len(idxs) - 1):
                    tris.append((idxs[0], idxs[i], idxs[i + 1]))
    return tris


def load_mesh_triangles(filepath: str) -> List[Triangle3D]:
    ext = os.path.splitext(filepath)[1].lower()
    if ext == ".obj":
        return parse_obj(filepath)
    return parse_stl(filepath)


def audit_mesh(
    filepath: str,
    target_dims: Optional[List[float]] = None,
    tolerance_mm: float = 0.1,
) -> Dict[str, object]:
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"Mesh file not found: {filepath}")

    triangles = load_mesh_triangles(filepath)
    if not triangles:
        return {
            "filepath": os.path.abspath(filepath),
            "status": "FAIL",
            "error": "No valid triangles found in mesh file.",
        }

    directed_edges: Dict[Tuple[Point3D, Point3D], int] = {}
    min_x = min_y = min_z = float("inf")
    max_x = max_y = max_z = float("-inf")
    total_area = 0.0
    overhang_area = 0.0
    bed_contact_area = 0.0
    signed_volume = 0.0
    cx_weighted = cy_weighted = cz_weighted = 0.0
    degenerate_faces = 0

    for a, b, c in triangles:
        for pt in (a, b, c):
            min_x = min(min_x, pt[0])
            max_x = max(max_x, pt[0])
            min_y = min(min_y, pt[1])
            max_y = max(max_y, pt[1])
            min_z = min(min_z, pt[2])
            max_z = max(max_z, pt[2])

    for a, b, c in triangles:
        if a == b or b == c or c == a:
            degenerate_faces += 1
            continue

        for e in ((a, b), (b, c), (c, a)):
            directed_edges[e] = directed_edges.get(e, 0) + 1

        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        norm_len = math.sqrt(nx * nx + ny * ny + nz * nz)
        if norm_len < 1e-10:
            degenerate_faces += 1
            continue

        tri_area = 0.5 * norm_len
        total_area += tri_area
        nz_unit = nz / norm_len
        avg_z = (a[2] + b[2] + c[2]) / 3.0

        if abs(avg_z - min_z) < 0.05 and nz_unit < -0.95:
            bed_contact_area += tri_area
        elif nz_unit < -0.708 and avg_z > min_z + 0.15:
            overhang_area += tri_area

        v_tet = (
            a[0] * (b[1] * c[2] - b[2] * c[1])
            - a[1] * (b[0] * c[2] - b[2] * c[0])
            + a[2] * (b[0] * c[1] - b[1] * c[0])
        ) / 6.0
        signed_volume += v_tet
        cx_weighted += v_tet * (a[0] + b[0] + c[0]) / 4.0
        cy_weighted += v_tet * (a[1] + b[1] + c[1]) / 4.0
        cz_weighted += v_tet * (a[2] + b[2] + c[2]) / 4.0

    open_edges = 0
    non_manifold_edges = 0
    for (u, v), count in directed_edges.items():
        if count != 1:
            non_manifold_edges += 1
        rev_count = directed_edges.get((v, u), 0)
        if rev_count == 0:
            open_edges += 1
        elif rev_count != 1:
            non_manifold_edges += 1

    width_x = round(max_x - min_x, 4)
    depth_y = round(max_y - min_y, 4)
    height_z = round(max_z - min_z, 4)
    vol_mm3 = abs(signed_volume)
    bbox_vol = max(width_x * depth_y * height_z, 1e-6)
    solidity_ratio = vol_mm3 / bbox_vol

    # Connected-component / multi-part XY collision & spacing audit
    vert_to_comp: Dict[Point3D, int] = {}
    comp_parent: List[int] = []

    def find_root(i: int) -> int:
        while comp_parent[i] != i:
            comp_parent[i] = comp_parent[comp_parent[i]]
            i = comp_parent[i]
        return i

    for a, b, c in triangles:
        for pt in (a, b, c):
            if pt not in vert_to_comp:
                cid = len(comp_parent)
                vert_to_comp[pt] = cid
                comp_parent.append(cid)
        ra = find_root(vert_to_comp[a])
        rb = find_root(vert_to_comp[b])
        rc = find_root(vert_to_comp[c])
        comp_parent[rb] = ra
        comp_parent[rc] = ra

    comp_bboxes: Dict[int, List[float]] = {}
    for pt, cid in vert_to_comp.items():
        r = find_root(cid)
        if r not in comp_bboxes:
            comp_bboxes[r] = [pt[0], pt[0], pt[1], pt[1], pt[2], pt[2]]
        else:
            bb = comp_bboxes[r]
            bb[0] = min(bb[0], pt[0])
            bb[1] = max(bb[1], pt[0])
            bb[2] = min(bb[2], pt[1])
            bb[3] = max(bb[3], pt[1])
            bb[4] = min(bb[4], pt[2])
            bb[5] = max(bb[5], pt[2])

    shell_list = list(comp_bboxes.values())
    min_inter_part_gap_mm: Optional[float] = None
    part_collision_detected = False
    if len(shell_list) > 1:
        min_gap = float("inf")
        for i in range(len(shell_list)):
            for j in range(i + 1, len(shell_list)):
                b1, b2 = shell_list[i], shell_list[j]
                gap_x = max(0.0, b1[0] - b2[1], b2[0] - b1[1])
                gap_y = max(0.0, b1[2] - b2[3], b2[2] - b1[3])
                xy_dist = math.hypot(gap_x, gap_y)
                if b1[0] < b2[1] and b1[1] > b2[0] and b1[2] < b2[3] and b1[3] > b2[2]:
                    xy_dist = -min(b1[1] - b2[0], b2[1] - b1[0], b1[3] - b2[2], b2[3] - b1[2])
                    part_collision_detected = True
                min_gap = min(min_gap, xy_dist)
        min_inter_part_gap_mm = round(min_gap, 3)

    if abs(signed_volume) > 1e-9:
        com = [
            round(cx_weighted / signed_volume, 3),
            round(cy_weighted / signed_volume, 3),
            round(cz_weighted / signed_volume, 3),
        ]
    else:
        com = [round((min_x + max_x) / 2, 3), round((min_y + max_y) / 2, 3), round((min_z + max_z) / 2, 3)]

    is_watertight = (open_edges == 0 and non_manifold_edges == 0 and degenerate_faces == 0)
    overhang_pct = round(100.0 * overhang_area / max(total_area, 1e-6), 2)

    # Dimensional comparison against target_dims
    dim_check = {"checked": False}
    if target_dims and len(target_dims) == 3:
        tx, ty, tz = float(target_dims[0]), float(target_dims[1]), float(target_dims[2])
        dx = round(width_x - tx, 4)
        dy = round(depth_y - ty, 4)
        dz = round(height_z - tz, 4)
        within_tol = (abs(dx) <= tolerance_mm and abs(dy) <= tolerance_mm and abs(dz) <= tolerance_mm)
        dim_check = {
            "checked": True,
            "target_mm": [tx, ty, tz],
            "actual_mm": [width_x, depth_y, height_z],
            "deviation_mm": [dx, dy, dz],
            "tolerance_mm": tolerance_mm,
            "within_tolerance": within_tol,
        }

    # Engineering recommendations & sturdiness rating
    warnings: List[str] = []
    score = 100
    if not is_watertight:
        score -= 35
        warnings.append(
            f"Mesh is NOT manifold ({open_edges} open boundary edges, {non_manifold_edges} non-manifold edges). Repair before slicing."
        )
    if signed_volume < 0:
        score -= 15
        warnings.append("Mesh normals are inverted (negative signed volume). Flip triangle winding.")
    if min(width_x, depth_y, height_z) < 1.6:
        score -= 15
        warnings.append(
            f"Minimum bounding dimension ({min(width_x, depth_y, height_z):.2f} mm) is below 1.6 mm structural threshold."
        )
    if overhang_pct > 8.0:
        score -= 10
        warnings.append(
            f"Overhang area is {overhang_pct:.1f}% of surface area (>45 deg). Consider adding 45-deg chamfers, teardrops, or re-orienting."
        )
    if bed_contact_area < 25.0:
        score -= 10
        warnings.append(
            f"Low build-plate contact area ({bed_contact_area:.1f} mm^2). Consider re-orienting or using a brim."
        )
    if dim_check.get("checked") and not dim_check.get("within_tolerance"):
        score -= 25
        warnings.append(
            f"Bounding box {dim_check['actual_mm']} deviates from target {dim_check['target_mm']} by {dim_check['deviation_mm']} mm."
        )
    if part_collision_detected:
        score -= 40
        warnings.append(
            f"Multi-part XY bounding box collision/overlap detected (min_inter_part_gap_mm = {min_inter_part_gap_mm} mm). Space plated parts >= 8.0 mm apart."
        )
    elif min_inter_part_gap_mm is not None and min_inter_part_gap_mm < 4.0:
        score -= 15
        warnings.append(
            f"Plated parts are very close ({min_inter_part_gap_mm} mm XY gap). Recommend >= 8.0 mm spacing to prevent brim/elephant-foot fusing."
        )

    score = max(0, score)
    status = "PASS" if (is_watertight and not part_collision_detected and score >= 75 and (not dim_check["checked"] or dim_check["within_tolerance"])) else "WARN/FAIL"

    return {
        "filepath": os.path.abspath(filepath),
        "status": status,
        "structural_quality_score": score,
        "is_watertight_manifold": is_watertight,
        "topology": {
            "triangle_count": len(triangles),
            "shell_count": len(shell_list),
            "min_inter_part_gap_mm": min_inter_part_gap_mm,
            "part_collision_detected": part_collision_detected,
            "open_boundary_edges": open_edges,
            "non_manifold_edges": non_manifold_edges,
            "degenerate_faces": degenerate_faces,
            "normals_outward": signed_volume > 0,
        },
        "dimensions_mm": {
            "width_x": width_x,
            "depth_y": depth_y,
            "height_z": height_z,
            "min_point": [round(min_x, 4), round(min_y, 4), round(min_z, 4)],
            "max_point": [round(max_x, 4), round(max_y, 4), round(max_z, 4)],
        },
        "dimensional_verification": dim_check,
        "physical_properties": {
            "volume_mm3": round(vol_mm3, 2),
            "volume_cm3": round(vol_mm3 / 1000.0, 3),
            "surface_area_mm2": round(total_area, 2),
            "bed_contact_area_mm2": round(bed_contact_area, 2),
            "overhang_area_mm2": round(overhang_area, 2),
            "overhang_ratio_pct": overhang_pct,
            "solidity_fill_ratio": round(solidity_ratio, 3),
            "center_of_mass_mm": com,
            "estimated_mass_grams": {
                "PLA_solid": round((vol_mm3 / 1000.0) * 1.24, 2),
                "PLA_functional_4walls_25pct": round((vol_mm3 / 1000.0) * 1.24 * 0.45, 2),
                "PETG_solid": round((vol_mm3 / 1000.0) * 1.27, 2),
                "ABS_ASA_solid": round((vol_mm3 / 1000.0) * 1.05, 2),
                "Aluminum_6061": round((vol_mm3 / 1000.0) * 2.70, 2),
            },
        },
        "engineering_recommendations": warnings if warnings else [
            "Mesh is 100% watertight manifold with outward normals.",
            "Wall proportions, bed adhesion footprint, and overhang geometry meet DFM standards.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit an STL or OBJ 3D model for manifoldness, exact dimensions, and DFM.")
    parser.add_argument("mesh_file", help="Path to .stl or .obj file")
    parser.add_argument(
        "--target",
        nargs=3,
        type=float,
        metavar=("X", "Y", "Z"),
        default=None,
        help="Optional target bounding box dimensions in mm (e.g., --target 100 70 35)",
    )
    parser.add_argument("--tol", type=float, default=0.1, help="Dimensional tolerance in mm (default: 0.1)")
    args = parser.parse_args()

    result = audit_mesh(args.mesh_file, args.target, args.tol)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
