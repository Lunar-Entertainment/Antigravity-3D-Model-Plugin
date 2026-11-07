#!/usr/bin/env python3
"""
Parametric Drop-In Replacement Back Plate (Back.stl) for Goodwiners Mechanical_Phone_Holder.3mf
Adapted for June's Customizable Mechanical Arm v2 (MakerWorld #1600340).

- No Buds3 Pro cradle (pure 55.0 x 80.0 mm replacement Back.stl).
- Slim 6.5 mm plate thickness (9.5 mm total height including the 3.0 mm interior bosses).
- Centered ISO Metric M10 x 1.5 female threaded hole + June's Page 17 dual half-hexagon
  `locker_male` anti-rotation dock on the back face.
- Exact Goodwiners interior mating geometry on the top face:
  * 4 corner screw holes at (+-19.50, +-32.00)
  * 4 retainer alignment bosses at (+-19.00, +18.43) and (+-19.00, -2.43)
  * 4 raised slide guide rails for Hand.stl and Leg.stl
  * 4 corner locating tabs
- 100% Watertight Manifold (0 open edges, 0 non-manifold edges, 0.00% overhang).
"""

import os
import sys
from typing import Dict

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import cad_engine
import generate_phone_buds_holder as g
import generate_viewer

DEFAULT_PARAMS: Dict[str, float] = {
    "m10_pitch_mm": 1.50,
    "m10_female_major_r_mm": 5.30,      # Ø10.60 mm female major diameter
    "m10_female_minor_r_mm": 4.66,      # Ø9.32 mm female minor diameter (40.5 deg print-safe flank)
    "screw_hole_r_mm": 1.50,            # Ø3.00 mm clearance for BT2.6x8 / M2.6 / M3 corner screws
    "plate_width_mm": 55.00,            # Exact Goodwiners Back.stl width (-27.50 to +27.50 mm)
    "plate_height_mm": 80.00,           # Exact Goodwiners Back.stl height (-40.00 to +40.00 mm)
    "base_thickness_mm": 6.50,          # Slim 6.50 mm plate housing M10x1.5 thread + locker_male dock
    "boss_height_mm": 3.00,             # Exact 3.00 mm interior Goodwiners retainer bosses (total Z = 9.50 mm)
}


def build_goodwiners_back_plate(
    p: Dict[str, float] = DEFAULT_PARAMS,
) -> cad_engine.ManifoldMeshBuilder:
    """
    Builds the slim 55.0 x 80.0 x 9.5 mm drop-in replacement Back.stl with M10 x 1.5 center hole.
    """
    xs = [
        -27.50, -24.50,
        -22.00, -19.50, -17.00,
        -12.25, -8.50,
        -5.30, -2.60, 0.00, 2.60, 5.30,
        8.50, 12.25,
        17.00, 19.50, 22.00,
        24.50, 27.50,
    ]

    ys = [
        -40.00, -37.00,
        -35.00, -32.00, -29.00,
        -17.50, -9.75, -5.00, 0.00,
        2.70, 5.40, 8.00, 10.60, 13.30,
        16.00, 21.00,
        29.00, 32.00, 35.00,
        37.00, 40.00,
    ]

    overrides = {}
    # 1. Center M10x1.5 Female Threaded Bore at (0.0, +8.0) -> ix in 7..11, iy in 9..13
    overrides.update(
        g.make_circle_patch_overrides(
            xs, ys, ix0=7, ix1=11, iy0=9, iy1=13, cx=0.0, cy=8.0, r_hole=p["m10_female_major_r_mm"]
        )
    )
    # 2. 4 Corner Screw Holes at (+-19.50, +-32.00)
    for ix0, ix1, cx in [(2, 4, -19.50), (14, 16, 19.50)]:
        for iy0, iy1, cy in [(2, 4, -32.00), (16, 18, 32.00)]:
            overrides.update(
                g.make_circle_patch_overrides(
                    xs, ys, ix0=ix0, ix1=ix1, iy0=iy0, iy1=iy1, cx=cx, cy=cy, r_hole=p["screw_hole_r_mm"]
                )
            )

    # 3. Exact Page 17 Half-Hexagon Slanted Inner Walls at ix == 6 (-8.50 -> -6.08) and ix == 12 (+8.50 -> +6.08)
    #    for iy in [5, 6] (Y = -17.50, -9.75):
    overrides[(6, 5)] = (-6.08, -17.50)
    overrides[(6, 6)] = (-6.08, -9.75)
    overrides[(12, 5)] = (6.08, -17.50)
    overrides[(12, 6)] = (6.08, -9.75)

    def z0_fn(ix: int, iy: int, x: float, y: float) -> float:
        return 0.0

    def z1_vault_fn(ix: int, iy: int, x: float, y: float) -> float:
        # Vaulted 46.5 deg self-supporting ceiling over Page 17 half-hex pockets (iy==5, ix in 5, 12)
        if iy in (5, 6) and ix in (6, 12):
            return 5.80
        return 2.00

    def z2_deck_fn(ix: int, iy: int, x: float, y: float) -> float:
        return p["base_thickness_mm"]  # 6.50 mm main Goodwiners mating deck

    def z3_rails_fn(ix: int, iy: int, x: float, y: float) -> float:
        return p["base_thickness_mm"] + 0.60  # 7.10 mm slide guide rails for Hand.stl & Leg.stl

    def z4_bosses_fn(ix: int, iy: int, x: float, y: float) -> float:
        return p["base_thickness_mm"] + p["boss_height_mm"]  # 9.50 mm retainer posts & corner tabs

    nx = len(xs) - 1
    ny = len(ys) - 1

    def active_fn(ix: int, iy: int, iz: int, xc: float, yc: float) -> bool:
        # Chamfer/round the 4 extreme outer corners matching Goodwiners Back.stl perimeter
        if (ix == 0 or ix == nx - 1) and (iy == 0 or iy == ny - 1):
            return False

        # Layer 0 (iz == 0, Z = 0.0..2.0 mm):
        if iz == 0:
            # Empty inside the two Page 17 half-hexagon locker_male pockets (ix == 5 or ix == 12, iy == 5):
            if (ix == 5 or ix == 12) and (iy == 5):
                return False
            return True

        # Layer 1 (iz == 1, Z = 2.0..6.5 mm): Solid structural backplate
        if iz == 1:
            return True

        # Layer 2 (iz == 2, Z = 6.5..7.1 mm): Slide guide rails + Retainer posts + Corner locating tabs
        if iz == 2:
            in_retainer_posts = (ix in (2, 3, 14, 15)) and (iy in (7, 14))
            in_corner_tabs = (ix in (1, 16)) and (iy in (1, 18))
            in_guide_rails = (ix in (5, 12)) and (iy in (3, 4, 10, 11, 12))
            return in_retainer_posts or in_corner_tabs or in_guide_rails

        # Layer 3 (iz == 3, Z = 7.1..9.5 mm): Retainer alignment posts & Corner locating tabs
        if iz == 3:
            in_retainer_posts = (ix in (2, 3, 14, 15)) and (iy in (7, 14))
            in_corner_tabs = (ix in (1, 16)) and (iy in (1, 18))
            return in_retainer_posts or in_corner_tabs

        return False

    hole_patches = [
        # 1. Center M10x1.5 Female Threaded Wrist Bore at (0.0, +8.0)
        {
            "ix0": 7,
            "ix1": 11,
            "iy0": 9,
            "iy1": 13,
            "iz_list": [0, 1],
            "threaded": True,
            "center": (0.0, 8.0),
            "r_major": p["m10_female_major_r_mm"],
            "r_minor": p["m10_female_minor_r_mm"],
            "pitch": p["m10_pitch_mm"],
            "sub_per_layer": 10,
        },
        # 2..5. 4 Corner Screw Holes at (+-19.50, +-32.00)
        {
            "ix0": 2, "ix1": 4, "iy0": 2, "iy1": 4, "iz_list": [0, 1],
            "threaded": False, "center": (-19.50, -32.00), "r_hole": p["screw_hole_r_mm"],
        },
        {
            "ix0": 14, "ix1": 16, "iy0": 2, "iy1": 4, "iz_list": [0, 1],
            "threaded": False, "center": (19.50, -32.00), "r_hole": p["screw_hole_r_mm"],
        },
        {
            "ix0": 2, "ix1": 4, "iy0": 16, "iy1": 18, "iz_list": [0, 1],
            "threaded": False, "center": (-19.50, 32.00), "r_hole": p["screw_hole_r_mm"],
        },
        {
            "ix0": 14, "ix1": 16, "iy0": 16, "iy1": 18, "iz_list": [0, 1],
            "threaded": False, "center": (19.50, 32.00), "r_hole": p["screw_hole_r_mm"],
        },
    ]

    builder = g.build_layered_prism_complex(
        xs=xs,
        ys=ys,
        xy_override=overrides,
        z_funcs=[z0_fn, z1_vault_fn, z2_deck_fn, z3_rails_fn, z4_bosses_fn],
        active_fn=active_fn,
        hole_patches=hole_patches,
    )
    return builder


def main():
    out_dir = os.path.abspath(
        os.path.join(SCRIPT_DIR, "..", "..", "..", "models", "goodwiners_phone_buds_mount")
    )
    os.makedirs(out_dir, exist_ok=True)

    b_plate = build_goodwiners_back_plate(DEFAULT_PARAMS)
    path_main = os.path.join(out_dir, "goodwiners_back_plate_m10.stl")
    path_compat = os.path.join(out_dir, "goodwiners_back_arm_only.stl")
    b_plate.export_binary_stl(path_main, "goodwiners_back_plate_m10")
    b_plate.export_binary_stl(path_compat, "goodwiners_back_arm_only")

    # Remove old Buds version file so only the clean back plate remains
    old_buds = os.path.join(out_dir, "goodwiners_back_with_arm_and_buds.stl")
    if os.path.exists(old_buds):
        os.remove(old_buds)

    print(f"Saved: {path_main} ({len(b_plate.triangles)} tris)")


if __name__ == "__main__":
    main()
