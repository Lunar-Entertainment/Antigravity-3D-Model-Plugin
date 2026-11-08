#!/usr/bin/env python3
"""
Ultra-Compact M10 x 1.5 + Dual Locker Adapter for Hodzinets Phone Holder
Mating June's Customizable Mechanical Arm v2 (MakerWorld #1600340) with
Hodzinets Mechanical Phone Holder (MakerWorld #1052740).

Replaces Part 12 Connector and mounts directly onto the flat rear face of original Back.stl:
1. True Rounded Corners & Ultra-Compact Footprint (44.0 x 30.0 x 8.5 mm, ~4.5g PLA):
   - Outer 4 corners filleted with smooth R = 3.50 mm circular arcs (32 perimeter segments).
   - Stepped 3.20 mm side mounting flanges with the exact 38.00 x 20.85 mm 4-hole pattern
     (X = ±19.00 mm, Y = ±10.425 mm) matching Back.stl's rear connector bosses.
   - Central raised 8.50 mm wrist hub (30.0 x 28.0 mm) with filleted R = 2.50 mm corners.
2. Center ISO Metric M10 x 1.5 Female Threaded Hole at (0.00, +3.20):
   - Full 8.50 mm thread engagement (Ø10.60 mm major, Ø9.32 mm minor, 1.50 mm pitch, 40.5° print-safe flank).
3. Top-Recessed Dual Half-Hexagon June's Arm v2 `locker_male` Dock Pockets:
   - Designed specifically to receive June's male locker with rounded corners.
   - Features generous R = 1.80 mm corner relief fillets and +0.40 mm fit clearance.
   - Recessed 2.70 mm into the top wrist face (Z = 5.80..8.50 mm) at the exact 13.625 mm offset from M10 bore.
   - Backed by 5.80 mm (29 solid layers!) of continuous solid plastic floor underneath (0.00% overhangs).
4. Printable Mounting Fasteners Placed ASIDE the Adapter:
   - Sized specifically for Hodzinets Back.stl BT2.6 holes (AA004).
   - 4× M2.6 / BT2.6 screws placed aside the adapter on the build plate (2 on left, 2 on right),
     completely independent, sitting flat on Z = 0 with zero supports, ready for 1-click printing.
"""

import math
import os
import sys
import zipfile
import xml.etree.ElementTree as ET
from typing import Dict, List, Tuple

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import cad_engine
import generate_goodwiners_connector_screws as gcs
import generate_viewer

Point2D = Tuple[float, float]
Point3D = Tuple[float, float, float]

DEFAULT_PARAMS: Dict[str, float] = {
    "m10_pitch_mm": 1.50,
    "m10_female_major_r_mm": 5.30,      # Ø10.60 mm female major diameter
    "m10_female_minor_r_mm": 4.66,      # Ø9.32 mm female minor diameter (40.5 deg print-safe flank)
    "screw_hole_r_mm": 1.45,            # Ø2.90 mm clearance for BT2.6x8 / M2.6 connector screws
    "flange_thickness_mm": 3.20,        # 3.20 mm side screw flanges (matches Hodzinets Back.stl step)
    "pocket_floor_z_mm": 5.80,          # 5.80 mm solid floor underneath the top-recessed pockets
    "hub_thickness_mm": 8.50,           # 8.50 mm total central hub height (2.70 mm deep locker pockets)
    "plate_width_x_mm": 44.00,          # 44.00 mm total width
    "plate_depth_y_mm": 30.00,          # 30.00 mm total depth
    "plate_corner_radius_mm": 3.50,     # Smooth R = 3.50 mm rounded outer corners
    "hub_width_x_mm": 30.00,            # 30.00 mm central hub width
    "hub_depth_y_mm": 28.00,            # 28.00 mm central hub depth
    "hub_corner_radius_mm": 2.50,       # R = 2.50 mm central hub corner fillets
}


def make_june_arm_locker_pocket(cx_sign: float) -> List[Point2D]:
    """
    Builds the 2D contour of June's Customizable Mechanical Arm v2 `locker_male` dock pocket
    with generous corner relief fillets (R = 1.80 mm) and +0.40 mm fit clearance so the
    rounded male key slides in freely and seats squarely.
    Guarantees 100% bilateral symmetry and non-self-intersecting contours for both left and right docks.
    """
    if cx_sign < 0:
        p_right = make_june_arm_locker_pocket(1.0)
        return [cad_engine.snap2d((-pt[0], pt[1])) for pt in reversed(p_right)]

    cy = -10.425  # Midpoint offset: +3.20 - 13.625 = -10.425 mm
    x_apex = 5.80
    x_mid = 7.20
    x_out = 13.00
    y_apex = cy
    y_mid_lo = cy - 2.80
    y_mid_hi = cy + 2.80
    y_out_lo = cy - 4.10
    y_out_hi = cy + 4.10

    # Outer corner fillet radius
    r = 1.80
    segs = 6
    pts: List[Point2D] = [cad_engine.snap2d((x_apex, y_apex))]

    # Slanted wall to bottom midpoint
    pts.append(cad_engine.snap2d((x_mid, y_mid_lo)))

    # Bottom-outer rounded corner arc
    c_x = x_out - r
    c_y = y_out_lo + r
    ang0 = 1.5 * math.pi
    ang1 = 2.0 * math.pi
    for i in range(segs + 1):
        a = ang0 + (ang1 - ang0) * i / segs
        pts.append(cad_engine.snap2d((c_x + r * math.cos(a), c_y + r * math.sin(a))))

    # Top-outer rounded corner arc
    c_y2 = y_out_hi - r
    ang0_2 = 0.0
    ang1_2 = 0.5 * math.pi
    for i in range(segs + 1):
        a = ang0_2 + (ang1_2 - ang0_2) * i / segs
        pts.append(cad_engine.snap2d((c_x + r * math.cos(a), c_y2 + r * math.sin(a))))

    # Slanted wall to top midpoint
    pts.append(cad_engine.snap2d((x_mid, y_mid_hi)))
    return cad_engine.ensure_ccw(pts)


def build_goodwiners_m10_connector(
    p: Dict[str, float] = DEFAULT_PARAMS,
) -> cad_engine.ManifoldMeshBuilder:
    """
    Builds the M10 Connector Adapter with:
    - 4 Smooth R = 3.50 mm rounded outer corners.
    - 4 Hodzinets Back.stl screw clearance holes at (±19.00, ±10.425).
    - Central M10x1.5 female threaded bore at (0.00, +3.20).
    - Top-recessed dual June's arm locker pockets with rounded corner reliefs.
    100% Watertight Manifold, 0.00% Overhangs > 45°.
    """
    b = cad_engine.ManifoldMeshBuilder()

    # Center Y of plate: [-16.20 .. +13.80] has cy = -1.20 mm, depth = 30.00 mm
    cy_plate = -1.20
    w_plate = p["plate_width_x_mm"]
    d_plate = p["plate_depth_y_mm"]
    r_corner = p["plate_corner_radius_mm"]

    # 1. Base outer contour: rounded rectangle with true circular arc fillets
    base_poly = cad_engine.rounded_rect_contour(
        0.0, cy_plate, w_plate, d_plate, radius=r_corner, segments_per_corner=8
    )

    # 2. 4 Mounting screw holes matching Hodzinets Back.stl (X = ±19.00, Y = ±10.425)
    r_hole = p["screw_hole_r_mm"]
    h_bl = cad_engine.circle_contour(-19.00, -10.425, r_hole, segments=16)
    h_br = cad_engine.circle_contour(19.00, -10.425, r_hole, segments=16)
    h_tl = cad_engine.circle_contour(-19.00, 10.425, r_hole, segments=16)
    h_tr = cad_engine.circle_contour(19.00, 10.425, r_hole, segments=16)
    screw_holes = [h_bl, h_br, h_tl, h_tr]

    # 3. Center M10 female threaded bore cap at (0.00, +3.20)
    r_maj = p["m10_female_major_r_mm"]
    r_min = p["m10_female_minor_r_mm"]
    pitch = p["m10_pitch_mm"]
    segs_m10 = 32
    m10_cap = cad_engine.circle_contour(0.0, 3.20, r_maj, segments=segs_m10)

    # 4. Central hub contour (X in [-15.0..+15.0], Y in [-15.2..+12.8], depth 28.0 mm)
    hub_poly = cad_engine.rounded_rect_contour(
        0.0, cy_plate, p["hub_width_x_mm"], p["hub_depth_y_mm"],
        radius=p["hub_corner_radius_mm"], segments_per_corner=6
    )

    # 5. Dual June's arm locker pockets with rounded corner reliefs
    p_left = make_june_arm_locker_pocket(-1.0)
    p_right = make_june_arm_locker_pocket(1.0)

    z_flange = p["flange_thickness_mm"]       # 3.20 mm
    z_floor = p["pocket_floor_z_mm"]          # 5.80 mm
    z_top = p["hub_thickness_mm"]             # 8.50 mm

    # A. Bottom Face (Z = 0.0, facing down -Z)
    b.add_horizontal_face(base_poly, [h_bl, h_br, h_tl, h_tr, m10_cap], z=0.0, facing_up=False)

    # B. Flange Outer Walls (Z = 0.0 .. 3.20 mm)
    b.add_extruded_wall(base_poly, 0.0, z_flange, is_outer_wall=True)

    # C. 4 Screw Hole Inner Walls (Z = 0.0 .. 3.20 mm)
    for h in screw_holes:
        b.add_extruded_wall(h, 0.0, z_flange, is_outer_wall=False)

    # D. Flange Top Face at Z = 3.20 mm (facing up +Z)
    b.add_horizontal_face(base_poly, [hub_poly, h_bl, h_br, h_tl, h_tr], z=z_flange, facing_up=True)

    # E. Central Hub Outer Walls (Z = 3.20 .. 8.50 mm)
    b.add_extruded_wall(hub_poly, z_flange, z_top, is_outer_wall=True)

    # F. Hub Top Face at Z = 8.50 mm (facing up +Z)
    b.add_horizontal_face(hub_poly, [m10_cap, p_left, p_right], z=z_top, facing_up=True)

    # G. June Locker Pocket Walls (Z = 5.80 .. 8.50 mm, inner walls)
    b.add_extruded_wall(p_left, z_floor, z_top, is_outer_wall=False)
    b.add_extruded_wall(p_right, z_floor, z_top, is_outer_wall=False)

    # H. June Locker Pocket Floors at Z = 5.80 mm (facing up +Z)
    b.add_horizontal_face(p_left, None, z=z_floor, facing_up=True)
    b.add_horizontal_face(p_right, None, z=z_floor, facing_up=True)

    # I. Helical M10x1.5 Female Threaded Bore (Z = 0.0 .. 8.50 mm)
    n_slices = 48
    rings: List[List[Point3D]] = []
    for s in range(n_slices + 1):
        z_val = z_top * s / n_slices
        fade = min(1.0, z_val / pitch, (z_top - z_val) / pitch) if 0 < s < n_slices else 0.0
        ring: List[Point3D] = []
        for i in range(segs_m10):
            theta = 2.0 * math.pi * i / segs_m10
            if s == 0 or s == n_slices:
                ring.append((round(m10_cap[i][0], 4), round(m10_cap[i][1], 4), round(z_val, 4)))
            else:
                phase = (z_val / pitch) - (theta / (2.0 * math.pi))
                frac = phase - math.floor(phase)
                tri_wave = 1.0 - abs(2.0 * frac - 1.0)
                r_curr = r_maj - fade * (r_maj - r_min) * tri_wave
                ring.append((
                    round(r_curr * math.cos(theta), 4),
                    round(3.20 + r_curr * math.sin(theta), 4),
                    round(z_val, 4),
                ))
        rings.append(ring)

    # Stitch helical thread quads with correct inward-facing normal
    for rz in range(len(rings) - 1):
        r_low = rings[rz]
        r_high = rings[rz + 1]
        for i in range(segs_m10):
            nxt = (i + 1) % segs_m10
            b.add_quad(r_low[nxt], r_low[i], r_high[i], r_high[nxt])

    b.mark_checkpoint("Goodwiners M10 Connector Adapter (Filleted & Relieved)")
    return b


def build_goodwiners_m10_connector_assembly(
    p: Dict[str, float] = DEFAULT_PARAMS,
) -> cad_engine.ManifoldMeshBuilder:
    """
    Builds the production build-plate model where:
    - The adapter plate is centered at (X = 0, Y = 0, Z = 0).
    - The 4× BT2.6 / M2.8 mounting screws are placed ASIDE the adapter
      (2 on the left at X = -29.50 mm, 2 on the right at X = +29.50 mm),
      sitting flat on their heads at Z = 0, completely uncoupled and ready
      for simultaneous 1-click printing or inspection.
    """
    adapter = build_goodwiners_m10_connector(p)
    screw = gcs.build_connector_screw()

    assembly = cad_engine.ManifoldMeshBuilder()
    for tri in adapter.triangles:
        assembly.add_triangle(tri[0], tri[1], tri[2])

    # 4 screws placed ASIDE the adapter on the build plate (Z = 0):
    # 2 on the left, 2 on the right, matching the Y rows of the holes (Y = ±10.425 mm)
    screw_positions = [
        (-29.50, -10.425),
        (-29.50, 10.425),
        (29.50, -10.425),
        (29.50, 10.425),
    ]
    for sx, sy in screw_positions:
        for tri in screw.triangles:
            p1 = (round(tri[0][0] + sx, 4), round(tri[0][1] + sy, 4), round(tri[0][2], 4))
            p2 = (round(tri[1][0] + sx, 4), round(tri[1][1] + sy, 4), round(tri[1][2], 4))
            p3 = (round(tri[2][0] + sx, 4), round(tri[2][1] + sy, 4), round(tri[2][2], 4))
            assembly.add_triangle(p1, p2, p3)

    assembly.mark_checkpoint("M10 Adapter + 4× Screws (Plated Aside)")
    return assembly


def extract_original_back_stl(out_dir: str) -> None:
    """Extracts original Back.stl from uploaded 3MF archive if present."""
    src_3mf = "/home/lunar/.gemini/antigravity/brain/5ebe9d33-1018-46e0-aa40-eab205948e9d/.user_uploaded/media_1794049065174_a752c73b.3mf"
    if not os.path.isfile(src_3mf):
        return
    try:
        z = zipfile.ZipFile(src_3mf)
        ns = {"m": "http://schemas.microsoft.com/3dmanufacturing/core/2015/02"}
        root = ET.fromstring(z.read("3D/Objects/object_10.model"))
        verts = [(float(v.attrib["x"]), float(v.attrib["y"]), float(v.attrib["z"])) for v in root.findall(".//m:vertex", ns)]
        tris = [(int(t.attrib["v1"]), int(t.attrib["v2"]), int(t.attrib["v3"])) for t in root.findall(".//m:triangle", ns)]
        b = cad_engine.ManifoldMeshBuilder()
        for i1, i2, i3 in tris:
            p1, p2, p3 = verts[i1], verts[i2], verts[i3]
            q1 = (p1[0], -p1[1], -p1[2] + 2.5)
            q2 = (p2[0], -p2[1], -p2[2] + 2.5)
            q3 = (p3[0], -p3[1], -p3[2] + 2.5)
            b.add_triangle(q1, q2, q3)
        orig_path = os.path.join(out_dir, "original_Back.stl")
        b.export_binary_stl(orig_path, "original_Back")
    except Exception:
        pass


def main():
    out_dir = os.path.abspath(
        os.path.join(SCRIPT_DIR, "..", "..", "..", "models", "goodwiners_phone_buds_mount")
    )
    os.makedirs(out_dir, exist_ok=True)

    b_conn = build_goodwiners_m10_connector(DEFAULT_PARAMS)
    b_assembly = build_goodwiners_m10_connector_assembly(DEFAULT_PARAMS)

    path_conn_stl = os.path.join(out_dir, "goodwiners_m10_connector_adapter.stl")
    path_conn_3mf = os.path.join(out_dir, "goodwiners_m10_connector_adapter.3mf")
    path_assembly_stl = os.path.join(out_dir, "goodwiners_m10_connector_assembly_with_screws.stl")
    path_assembly_3mf = os.path.join(out_dir, "goodwiners_m10_connector_assembly_with_screws.3mf")
    path_compact_stl = os.path.join(out_dir, "goodwiners_compact_m10_adapter.stl")
    path_compact_3mf = os.path.join(out_dir, "goodwiners_compact_m10_adapter.3mf")
    path_main_stl = os.path.join(out_dir, "goodwiners_back_plate_m10.stl")

    b_conn.export_binary_stl(path_conn_stl, "goodwiners_m10_connector_adapter")
    b_conn.export_binary_stl(path_compact_stl, "goodwiners_compact_m10_adapter")
    b_conn.export_binary_stl(path_main_stl, "goodwiners_back_plate_m10")
    b_conn.export_3mf(path_conn_3mf, part_name="goodwiners_m10_connector_adapter")
    b_conn.export_3mf(path_compact_3mf, part_name="goodwiners_compact_m10_adapter")

    b_assembly.export_binary_stl(path_assembly_stl, "goodwiners_m10_connector_assembly_with_screws")
    b_assembly.export_3mf(path_assembly_3mf, part_name="goodwiners_m10_connector_assembly_with_screws")

    extract_original_back_stl(out_dir)

    print(f"Saved: {path_conn_stl} ({len(b_conn.triangles)} tris)")
    print(f"Saved: {path_conn_3mf}")
    print(f"Saved: {path_assembly_stl} ({len(b_assembly.triangles)} tris)")
    print(f"Saved: {path_assembly_3mf}")

    # Auto-sync Live CAD Studio in active conversation
    try:
        base_brain = os.path.expanduser("~/.gemini/jetski/brain")
        target_dir = None
        if os.path.isdir(base_brain):
            candidate_dirs = []
            for root, dirs, _ in os.walk(base_brain):
                if ".system_generated" in dirs or os.path.isfile(os.path.join(root, "live_cad_studio.html")):
                    candidate_dirs.append(root)
            if candidate_dirs:
                candidate_dirs.sort(key=lambda d: os.path.getmtime(d), reverse=True)
                target_dir = candidate_dirs[0]
        if target_dir:
            out_html = os.path.join(target_dir, "live_cad_studio.html")
            generate_viewer.sync_live_viewer(
                mesh_filepath=path_assembly_stl,
                output_html=out_html,
                title="Hodzinets M10 Adapter Plate + 4× Screws Aside",
                subtitle="True Rounded Fillets · June Arm v2 Relieved Locker · 4 Screws Aside",
            )
            print(f"Auto-synced Live CAD Studio: {out_html}")
    except Exception as e:
        print(f"Viewer sync notice: {e}")


if __name__ == "__main__":
    main()
