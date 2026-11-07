#!/usr/bin/env python3
"""
Parametric Hand-Cranked 15-Tooth Gear & Drop-In Bearing Stand Generator
ZERO SUPPORTS ARCHITECTURE (0.00% Overhang >45 deg):
1. Part 1: 15-Tooth Spur Gear + 8mm Stem Shaft + D-Shaft / Hex Interlock Tip (Prints flat on gear face, 0% overhang)
2. Part 2: Ergonomic Crank Arm & Spinner Knob with Matching Interlock Bore (Prints flat on arm face, 0% overhang)
3. Part 3: Sturdy Pedestal Stand with Drop-In U-Cradle (Prints flat on wide base, 0% overhang)
4. Part 4: Removable Retaining Bearing Lock Cap (Prints flat on top face, 0% overhang)
5. Full Plated Assembly Kit: All 4 parts laid out for a single print with ZERO SUPPORTS!
"""

import math
import os
import sys
from typing import Dict, List, Tuple

sys.path.insert(0, "/home/lunar/Documents/Projects/3d-model-plugin/skills/parametric-cad-modeling/scripts")
import cad_engine
import generate_viewer
import verify_model


def generate_zero_support_gear_assembly(output_dir: str, live_viewer_html: str = None) -> Dict[str, str]:
    os.makedirs(output_dir, exist_ok=True)

    # ---------------------------------------------------------
    # 1. PARAMETERS (Exact Millimeters, Zero Magic Numbers)
    # ---------------------------------------------------------
    module_m = 2.5
    teeth_z = 15
    gear_thickness = 8.0
    pitch_d = module_m * teeth_z        # 37.5 mm
    outer_d = pitch_d + 2.0 * module_m   # 42.5 mm
    root_d = pitch_d - 2.5 * module_m    # 31.25 mm

    stem_d = 8.0                         # Sturdy 8.0 mm shaft diameter
    journal_len = 16.0                   # Section resting in stand journal
    shoulder_d = 12.0
    shoulder_t = 3.0

    # Interlocking drive key between shaft tip and crank arm (Hex or D-Shaft profile)
    # Using 6.0mm hexagonal drive tip: strong, positive torque lock, 0% overhang
    hex_flats = 6.0
    hex_tip_len = 6.0                    # Matches crank arm thickness + chamfer

    # Crank Arm & Knob specifications:
    crank_throw = 22.0                   # Center-to-center offset
    crank_arm_t = 5.0                    # 5mm thick sturdy cantilever arm
    crank_arm_w = 12.0                   # 12mm width with rounded ends
    knob_d = 10.0                        # 10mm cylindrical finger knob
    knob_h = 16.0                        # 16mm height to spin comfortably
    bore_fit_clearance = 0.18            # 0.18mm radial snug transition fit for drive hex

    # Stand specifications:
    base_w = 60.0
    base_d = 50.0
    base_t = 5.0
    upright_w = 20.0
    upright_t = 14.0
    shaft_center_z = 35.0                # Gear radius 21.25 mm -> >13mm clearance above base
    journal_bore_d = 8.5                 # 8.0mm stem + 0.50mm running clearance
    r_j = journal_bore_d / 2.0

    # ---------------------------------------------------------
    # PART 1: 15T GEAR WITH STEM & DRIVE HEX TIP (Zero Overhangs!)
    # Built upwards in Z: Gear base (Z=0) -> Gear Top (Z=8) -> Shoulder (Z=11) -> Stem (Z=27) -> Hex Tip (Z=33)
    # Every cross-section is smaller than or equal to the previous one -> STRICT 0% OVERHANG!
    # ---------------------------------------------------------
    gear_mesh = cad_engine.ManifoldMeshBuilder()

    pitch_r = pitch_d / 2.0
    outer_r = outer_d / 2.0
    root_r = root_d / 2.0
    pitch_ang = 2.0 * math.pi / teeth_z
    half_tooth = pitch_ang / 4.0
    tip_half = half_tooth * 0.62
    root_half = half_tooth * 1.28

    gear_pts: List[Tuple[float, float]] = []
    for i in range(teeth_z):
        center_ang = i * pitch_ang
        angles_radii = [
            (center_ang - pitch_ang * 0.5, root_r),
            (center_ang - root_half, root_r),
            (center_ang - half_tooth, pitch_r),
            (center_ang - tip_half, outer_r),
            (center_ang + tip_half, outer_r),
            (center_ang + half_tooth, pitch_r),
            (center_ang + root_half, root_r),
        ]
        for ang, rad in angles_radii:
            pt = cad_engine.snap2d((rad * math.cos(ang), rad * math.sin(ang)))
            if not gear_pts or gear_pts[-1] != pt:
                gear_pts.append(pt)

    c_gear = cad_engine.ensure_ccw(gear_pts)
    c_shoulder = cad_engine.circle_contour(0, 0, shoulder_d / 2.0, segments=36)
    c_stem = cad_engine.circle_contour(0, 0, stem_d / 2.0, segments=36)
    c_hex_tip = cad_engine.hex_across_flats_contour(0, 0, hex_flats, angle_deg=0.0)

    # 1. Gear Body (Z = 0 to 8)
    gear_mesh.add_horizontal_face(c_gear, holes=None, z=0.0, facing_up=False)
    gear_mesh.add_extruded_wall(c_gear, 0.0, gear_thickness, is_outer_wall=True)
    gear_mesh.mark_checkpoint("Stage 1: 15-Tooth Module 2.5 Gear Face (Flat on Bed)")

    # 2. Thrust Shoulder Collar (Z = 8 to 11)
    gear_mesh.add_horizontal_face(c_gear, holes=[c_shoulder], z=gear_thickness, facing_up=True)
    gear_mesh.add_extruded_wall(c_shoulder, gear_thickness, gear_thickness + shoulder_t, is_outer_wall=True)
    gear_mesh.mark_checkpoint("Stage 2: Thrust Shoulder Collar")

    # 3. Stem / Journal Shaft (Z = 11 to 27)
    z_stem_top = gear_thickness + shoulder_t + journal_len
    gear_mesh.add_horizontal_face(c_shoulder, holes=[c_stem], z=gear_thickness + shoulder_t, facing_up=True)
    gear_mesh.add_extruded_wall(c_stem, gear_thickness + shoulder_t, z_stem_top, is_outer_wall=True)
    gear_mesh.mark_checkpoint("Stage 3: Precision 8mm Center Shaft")

    # 4. Hexagonal Drive Lock Tip (Z = 27 to 33)
    z_hex_top = z_stem_top + hex_tip_len
    gear_mesh.add_horizontal_face(c_stem, holes=[c_hex_tip], z=z_stem_top, facing_up=True)
    gear_mesh.add_extruded_wall(c_hex_tip, z_stem_top, z_hex_top, is_outer_wall=True)
    gear_mesh.add_horizontal_face(c_hex_tip, holes=None, z=z_hex_top, facing_up=True)
    gear_mesh.mark_checkpoint("Stage 4: Positive-Lock Hex Drive Tip")

    gear_stl = os.path.join(output_dir, "gear_and_shaft.stl")
    gear_mesh.export_binary_stl(gear_stl)

    # ---------------------------------------------------------
    # PART 2: CRANK ARM & KNOB (Zero Overhangs!)
    # Printed flat on its arm face at Z = 0 with vertical spinner knob rising up
    # Has mating hex socket hole with 0.18mm snug transition clearance
    # ---------------------------------------------------------
    crank_mesh = cad_engine.ManifoldMeshBuilder()

    crank_slot_len = crank_throw + crank_arm_w
    c_crank_outer = cad_engine.slot_contour(crank_throw / 2.0, 0, crank_slot_len, crank_arm_w, angle_deg=0.0, segments=32)
    # Hex bore with calibrated clearance (across flats = hex_flats + 2*clearance = 6.36mm)
    c_hex_bore = cad_engine.hex_across_flats_contour(0, 0, hex_flats + 2.0 * bore_fit_clearance, angle_deg=0.0)
    c_knob = cad_engine.circle_contour(crank_throw, 0, knob_d / 2.0, segments=32)

    # Arm extrusion from Z = 0 to crank_arm_t (5mm) with through-hex bore
    crank_mesh.add_horizontal_face(c_crank_outer, holes=[c_hex_bore], z=0.0, facing_up=False)
    crank_mesh.add_extruded_wall(c_crank_outer, 0.0, crank_arm_t, is_outer_wall=True)
    crank_mesh.add_extruded_wall(c_hex_bore, 0.0, crank_arm_t, is_outer_wall=False)
    crank_mesh.mark_checkpoint("Stage 1: Flat Crank Arm with Hex Drive Socket")

    # Spinner knob rising from Z = crank_arm_t to crank_arm_t + knob_h
    z_knob_top = crank_arm_t + knob_h
    crank_mesh.add_horizontal_face(c_crank_outer, holes=[c_hex_bore, c_knob], z=crank_arm_t, facing_up=True)
    crank_mesh.add_extruded_wall(c_knob, crank_arm_t, z_knob_top, is_outer_wall=True)
    crank_mesh.add_horizontal_face(c_knob, holes=None, z=z_knob_top, facing_up=True)
    crank_mesh.mark_checkpoint("Stage 2: Ergonomic Spinner Knob Handle")

    crank_stl = os.path.join(output_dir, "crank_arm_and_knob.stl")
    crank_mesh.export_binary_stl(crank_stl)

    # ---------------------------------------------------------
    # PART 3: STAND BASE WITH U-BEARING CRADLE (Zero Overhangs!)
    # Flared base on build plate, vertical column rising to U-cradle
    # ---------------------------------------------------------
    stand_mesh = cad_engine.ManifoldMeshBuilder()

    c_base_plate = cad_engine.rounded_rect_contour(0, 0, base_w, base_d, 6.0, segments_per_corner=8)
    c_base_chamf = cad_engine.rounded_rect_contour(0, 0, base_w - 1.6, base_d - 1.6, 5.2, segments_per_corner=8)

    hw = upright_w / 2.0
    hd = upright_t / 2.0
    tower_h = 8.0
    z_tower_top = shaft_center_z + tower_h

    c_upright = cad_engine.ensure_ccw([
        (-hw, -hd),
        (-r_j, -hd),
        (r_j, -hd),
        (hw, -hd),
        (hw, hd),
        (r_j, hd),
        (-r_j, hd),
        (-hw, hd),
    ])
    left_tower_rect = cad_engine.ensure_ccw([
        (-hw, -hd),
        (-r_j, -hd),
        (-r_j, hd),
        (-hw, hd),
    ])
    right_tower_rect = cad_engine.ensure_ccw([
        (r_j, -hd),
        (hw, -hd),
        (hw, hd),
        (r_j, hd),
    ])
    cradle_floor_rect = cad_engine.ensure_ccw([
        (-r_j, -hd),
        (r_j, -hd),
        (r_j, hd),
        (-r_j, hd),
    ])

    # Base with 45-degree elephant's foot chamfer
    stand_mesh.add_horizontal_face(c_base_chamf, holes=None, z=0.0, facing_up=False)
    stand_mesh.add_lofted_contour_wall(c_base_chamf, 0.0, c_base_plate, 0.8, is_outer_wall=True)
    stand_mesh.add_extruded_wall(c_base_plate, 0.8, base_t, is_outer_wall=True)
    stand_mesh.mark_checkpoint("Stage 1: Flared Anti-Tip Pedestal Base")

    stand_mesh.add_horizontal_face(c_base_plate, holes=[c_upright], z=base_t, facing_up=True)
    stand_mesh.add_extruded_wall(c_upright, base_t, shaft_center_z, is_outer_wall=True)

    stand_mesh.add_horizontal_face(cradle_floor_rect, holes=None, z=shaft_center_z, facing_up=True)
    stand_mesh.add_extruded_wall(left_tower_rect, shaft_center_z, z_tower_top, is_outer_wall=True)
    stand_mesh.add_horizontal_face(left_tower_rect, holes=None, z=z_tower_top, facing_up=True)

    stand_mesh.add_extruded_wall(right_tower_rect, shaft_center_z, z_tower_top, is_outer_wall=True)
    stand_mesh.add_horizontal_face(right_tower_rect, holes=None, z=z_tower_top, facing_up=True)
    stand_mesh.mark_checkpoint("Stage 2: Drop-In Journal Bearing Cradle & Guide Towers")

    stand_stl = os.path.join(output_dir, "stand_base.stl")
    stand_mesh.export_binary_stl(stand_stl)

    # ---------------------------------------------------------
    # PART 4: RETAINING BEARING LOCK CAP (Zero Overhangs!)
    # Built from top plate at Z=0 stepping up to central plug
    # ---------------------------------------------------------
    cap_mesh = cad_engine.ManifoldMeshBuilder()
    cap_outer_w = upright_w + 3.0
    cap_outer_d = upright_t + 3.0
    cap_plate_t = 4.0
    plug_h = 7.5

    c_cap_plate = cad_engine.rounded_rect_contour(0, 0, cap_outer_w, cap_outer_d, 2.5, 6)
    plug_clearance = 0.22
    plug_w = 2.0 * (r_j - plug_clearance)
    plug_d = upright_t - 2.0 * plug_clearance
    c_plug = cad_engine.rounded_rect_contour(0, 0, plug_w, plug_d, 1.2, 4)

    cap_mesh.add_horizontal_face(c_cap_plate, holes=None, z=0.0, facing_up=False)
    cap_mesh.add_extruded_wall(c_cap_plate, 0.0, cap_plate_t, is_outer_wall=True)
    cap_mesh.add_horizontal_face(c_cap_plate, holes=[c_plug], z=cap_plate_t, facing_up=True)
    cap_mesh.add_extruded_wall(c_plug, cap_plate_t, cap_plate_t + plug_h, is_outer_wall=True)
    cap_mesh.add_horizontal_face(c_plug, holes=None, z=cap_plate_t + plug_h, facing_up=True)
    cap_mesh.mark_checkpoint("Stage 1: Drop-In Retaining Journal Lock Cap")

    cap_stl = os.path.join(output_dir, "retaining_cap.stl")
    cap_mesh.export_binary_stl(cap_stl)

    # ---------------------------------------------------------
    # PART 5: FULL PRINT-READY PLATED ASSEMBLY (100% ZERO SUPPORTS!)
    # Layout on single build plate:
    # Gear at (-25, 0), Stand at (25, -5), Crank at (-25, 32), Cap at (25, 32)
    # ---------------------------------------------------------
    full_mesh = cad_engine.auto_plate_parts(
        [
            ("Part 1: 15T Spur Gear with 8mm Stem & Hex Drive Tip", gear_mesh),
            ("Part 2: Stable Pedestal Stand with Drop-In U-Cradle", stand_mesh),
            ("Part 3: Interlocking Crank Arm with Ergonomic Spinner Knob", crank_mesh),
            ("Part 4: Removable Drop-In Retaining Journal Lock Cap", cap_mesh),
        ],
        min_gap_mm=14.0,
        max_row_width_mm=160.0,
    )

    full_stl = os.path.join(output_dir, "gear_crank_full_kit_zero_supports.stl")
    full_mesh.export_binary_stl(full_stl)

    # Stream to Live Studio Viewer
    if live_viewer_html:
        generate_viewer.sync_live_viewer(
            mesh_filepath=full_stl,
            output_html=live_viewer_html,
            title="15T Crank Gear & Stand Kit — 100% Zero Supports",
            subtitle="Zero Supports (0.00% Overhang) · 15T Gear + 8mm Hex Shaft + Crank Arm + Drop-In Stand & Lock Cap",
            checkpoints=full_mesh.checkpoints,
            stream_delay_sec=0.25,
        )

    return {
        "gear_stl": gear_stl,
        "crank_stl": crank_stl,
        "stand_stl": stand_stl,
        "cap_stl": cap_stl,
        "full_kit_stl": full_stl,
    }


if __name__ == "__main__":
    out_dir = "/home/lunar/Documents/Projects/3d-model-plugin/models/gear_crank_stand"
    live_html = "/home/lunar/.gemini/antigravity/brain/5ebe9d33-1018-46e0-aa40-eab205948e9d/live_cad_studio.html"
    res = generate_zero_support_gear_assembly(out_dir, live_viewer_html=live_html)
    print("Generated zero-support assembly parts:", res)
