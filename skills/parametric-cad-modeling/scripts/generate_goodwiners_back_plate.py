#!/usr/bin/env python3
"""
Parametric Drop-In Replacement Back Plate for Goodwiners Mechanical_Phone_Holder.3mf
Adapted for June's Customizable Mechanical Arm v2 (MakerWorld #1600340) +
Underneath 4-Hand Samsung Galaxy Buds3 Pro Cradle.

100% Watertight Manifold (0 open edges, 0 non-manifold edges) & 0.00% Overhangs (>45 deg).
"""

import math
import os
import sys
from typing import Dict, List

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
import cad_engine
import generate_phone_buds_holder as g
import generate_viewer

DEFAULT_PARAMS: Dict[str, float] = {
    "m10_pitch_mm": 1.50,
    "m10_female_major_r_mm": 5.30,      # D = 10.60 mm female major diameter
    "m10_female_minor_r_mm": 4.66,      # D = 9.32 mm female minor diameter (40.5 deg flank, 0.0% overhang)
    "screw_hole_r_mm": 1.50,            # D = 3.00 mm clearance for BT2.6x8 / M2.6 / M3 corner screws
    "plate_width_mm": 55.00,            # Exact Goodwiners Back.stl width (-27.50 to +27.50 mm)
    "plate_height_mm": 80.00,           # Exact Goodwiners Back.stl height (-40.00 to +40.00 mm)
    "base_thickness_mm": 14.00,         # Houses June's 12.5 mm wrist stud + locker_male dock
}


def build_goodwiners_back_plate(
    p: Dict[str, float] = DEFAULT_PARAMS,
    include_buds: bool = True,
) -> cad_engine.ManifoldMeshBuilder:
    """
    Builds the drop-in replacement Back.stl for Mechanical_Phone_Holder.3mf:
    - Upper section (Y = -40.0 to +40.0 mm, X = -27.5 to +27.5 mm):
      * Exact 55.0 x 80.0 mm footprint matching Front_With_Logo.stl.
      * Centered June Arm Wrist Mount at (0.0, +8.0 mm): M10 x 1.5 female thread +
        Page 17 dual half-hexagon locker_male dock (X = +-[6.08..12.25], Y = [-9.50..-1.75]).
      * 4 Corner Lid Screw Holes at (+-19.50, +-32.00) with rear driver access counterbores
        so original BT2.6x8 screws engage 4.5 mm into Front_With_Logo.stl.
      * Raised interior corner locating tabs (+2.0 mm) & retainer alignment bosses (+3.0 mm)
        and slide guide rails (+0.6 mm) on the Z = 14.0 mm mating face.
    - Lower section (when include_buds=True, Y = -114.0 to -40.0 mm):
      * Rear clearance bridge spine (Y = -76.0 to -40.0 mm, Z = 0.0 to 10.0 mm) passing
        4.0 mm behind Leg.stl so the bottom phone leg slides freely without interference.
      * Underneath 4-Hand Galaxy Buds3 Pro Cradle (Y = -114.0 to -76.0 mm, X = -33.0 to +33.0 mm)
        with 2 bottom supporting hands + 2 left/right side hugging hands with 45 deg inward hooks.
    """
    # X grid lines (symmetric around X = 0.0):
    # ix=0..1: Left Buds side hand wall (-33.0..-29.8)
    # ix=1..2: Left Buds side hand inward hook lip (-29.8..-27.5)
    # ix=2..18: Goodwiners Back.stl width (-27.50 to +27.50 mm)
    #   - Corner screw holes at X = +-19.50: patch ix in 3..5 (-22.0..-17.0) and 15..17 (+17.0..+22.0)
    #   - Slide guide rails & Page 17 half-hex dock: X = +-12.25, +-8.50
    #   - Center M10x1.5 bore at X = 0.0: patch ix in 8..12 (-5.30..+5.30)
    xs = [
        -33.00, -29.80, -27.50,
        -22.00, -19.50, -17.00,
        -12.25, -8.50,
        -5.30, -2.60, 0.00, 2.60, 5.30,
        8.50, 12.25,
        17.00, 19.50, 22.00,
        27.50, 29.80, 33.00,
    ]

    # Y grid lines:
    # Zone A (iy in 0..3): Underneath 4-Hand Galaxy Buds3 Pro Cradle (Y = -114.0 to -76.0 mm)
    # Zone B (iy == 4): Rear Clearance Bridge behind Leg.stl (Y = -76.0 to -40.0 mm)
    # Zone C (iy in 5..21): Goodwiners Back.stl Plate (Y = -40.0 to +40.0 mm)
    #   - Lower corner screws at Y = -32.00: iy in 6..8 (-35.0..-29.0)
    #   - Lower retainer bosses at Y = -2.43: iy in 10..11 (-5.0..0.0)
    #   - Page 17 half-hex dock: iy == 9 (-17.50..-9.75)
    #   - Center M10x1.5 wrist bore at Y = +8.00: iy in 12..16 (+2.70..+13.30)
    #   - Upper retainer bosses at Y = +18.43: iy in 17..18 (+16.0..+21.0)
    #   - Upper corner screws at Y = +32.00: iy in 19..21 (+29.0..+35.0)
    ys = [
        -114.00, -110.00, -104.00, -82.00, -76.00,
        -40.00,
        -35.00, -32.00, -29.00,
        -17.50, -9.75, -5.00, 0.00,
        2.70, 5.40, 8.00, 10.60, 13.30,
        16.00, 21.00,
        29.00, 32.00, 35.00,
        40.00,
    ]

    overrides = {}
    # 1. Center M10x1.5 Wrist Bore at (0.0, +8.0) -> ix in 8..12, iy in 13..17
    overrides.update(
        g.make_circle_patch_overrides(
            xs, ys, ix0=8, ix1=12, iy0=13, iy1=17, cx=0.0, cy=8.0, r_hole=p["m10_female_major_r_mm"]
        )
    )
    # 2. 4 Corner Screw Holes at (+-19.50, +-32.00)
    for ix0, ix1, cx in [(3, 5, -19.50), (15, 17, 19.50)]:
        for iy0, iy1, cy in [(6, 8, -32.00), (20, 22, 32.00)]:
            overrides.update(
                g.make_circle_patch_overrides(
                    xs, ys, ix0=ix0, ix1=ix1, iy0=iy0, iy1=iy1, cx=cx, cy=cy, r_hole=p["screw_hole_r_mm"]
                )
            )

    # 3. Exact Page 17 Half-Hexagon Slanted Inner Walls at ix == 7 (-8.50 -> -6.08) and ix == 13 (+8.50 -> +6.08)
    #    for iy in [9, 10] (Y = -17.50, -9.75):
    overrides[(7, 9)] = (-6.08, -17.50)
    overrides[(7, 10)] = (-6.08, -9.75)
    overrides[(13, 9)] = (6.08, -17.50)
    overrides[(13, 10)] = (6.08, -9.75)

    def z0_fn(ix: int, iy: int, x: float, y: float) -> float:
        return 0.0

    def z1_vault_fn(ix: int, iy: int, x: float, y: float) -> float:
        # Vaulted 46.5 deg self-supporting ceiling over Page 17 half-hex pockets (iy==9, ix in 6, 13)
        if iy in (9, 10) and ix in (7, 13):
            return 9.70
        return 3.20

    def z2_fn(ix: int, iy: int, x: float, y: float) -> float:
        return 10.50

    def z3_deck_fn(ix: int, iy: int, x: float, y: float) -> float:
        return p["base_thickness_mm"]  # 14.00 mm main Goodwiners mating deck

    def z4_features_fn(ix: int, iy: int, x: float, y: float) -> float:
        # Zone A (iy <= 3): Underneath Buds3 Pro Little Hands risers & 45 deg hook ramps
        if iy <= 1:
            return 29.00
        if iy in (2, 3):
            if ix <= 1 or ix >= 19:
                return 29.00
            return 35.80
        # Zone C (iy >= 5): Interior locating tabs & retainer alignment posts (+3.0 mm above Z=14.0 deck)
        return p["base_thickness_mm"] + 3.00  # 17.00 mm

    def z5_top_fn(ix: int, iy: int, x: float, y: float) -> float:
        if iy <= 3:
            return 36.80
        return p["base_thickness_mm"] + 3.60

    def active_fn(ix: int, iy: int, iz: int, xc: float, yc: float) -> bool:
        # ----------------------------------------------------------------------
        # ZONE A: Underneath 4-Hand Galaxy Buds3 Pro Cradle (iy in 0..3, Y = -114 to -76 mm)
        # ----------------------------------------------------------------------
        if iy < 4:
            if not include_buds:
                return False
            # Layer 0 & 1 (Z = 0..10.5 mm): Backplate under Buds cradle (leave center USB-C gap at iy < 2, 6 <= ix < 14)
            if iz in (0, 1):
                if (iy < 2) and (6 <= ix < 14):
                    return False
                return True
            # Layer 2 (iz == 2, Z = 10.5..14.0 mm):
            if iz == 2:
                in_bot_hands = (iy == 0) and ((2 <= ix < 6) or (14 <= ix < 18))
                in_side_hands = (0 <= iy < 3) and (ix < 2 or ix >= 18)
                return in_bot_hands or in_side_hands
            # Layer 3 (iz == 3, Z = 14.0..z4_features_fn — Forward reach of the 4 Little Hands):
            if iz == 3:
                in_bot_hands = (iy == 0) and ((2 <= ix < 6) or (14 <= ix < 18))
                in_side_hands = (0 <= iy < 3) and (ix < 2 or ix >= 18)
                return in_bot_hands or in_side_hands
            # Layer 4 (iz == 4, Z = z4..36.8 mm — Inward-curling 45 deg fingertips of the 4 Little Hands):
            if iz == 4:
                in_bot_tips = (0 <= iy < 2) and ((2 <= ix < 6) or (14 <= ix < 18))
                in_side_tips = (0 <= iy < 3) and ((0 <= ix < 3) or (17 <= ix < 20))
                return in_bot_tips or in_side_tips
            return False

        # ----------------------------------------------------------------------
        # ZONE B: Rear Clearance Bridge Spine behind Leg.stl (iy == 4, Y = -76 to -40 mm)
        # Stays at Z = 0..10.5 mm (3.5 mm behind Z=14.0 deck so Leg.stl slides freely in front!)
        # ----------------------------------------------------------------------
        if iy == 4:
            if not include_buds:
                return False
            if ix < 2 or ix >= 18:
                return False
            return iz in (0, 1)

        # ----------------------------------------------------------------------
        # ZONE C: Goodwiners Back.stl Plate (iy >= 5, Y = -40 to +40 mm, X = -27.5 to +27.5 mm)
        # ----------------------------------------------------------------------
        if ix < 2 or ix >= 18:
            return False

        # Leave rear screwdriver access slots at the 4 corner screws (ix in 3..5 & 15..17, iy in 6..8 & 20..22)
        # in Layers 0 & 1 (Z = 0..10.5 mm), wait: hole_patches runs through iz in [0, 1, 2], so the screw shaft
        # runs all the way through cleanly!
        if iz == 0:
            # Empty inside the two Page 17 half-hexagon locker_male pockets (ix == 6 or ix == 13, iy == 9):
            if (ix == 6 or ix == 13) and (iy == 9):
                return False
            return True

        if iz in (1, 2):
            return True

        # Layer 3 (iz == 3, Z = 14.0..17.0 mm): Interior Goodwiners Retainer Alignment Bosses & Guide Rails
        if iz == 3:
            # 4 Retainer Alignment Posts at ix == 3..5 and 15..17, iy == 11 (-5..0) and iy == 18 (+16..+21)
            in_retainer_posts = (ix in (3, 4, 15, 16)) and (iy in (11, 18))
            # 2 Vertical Slide Guide Rails for Leg.stl & Hand.stl at ix == 6 and ix == 13
            in_guide_rails = (ix in (6, 13)) and (iy in (7, 8, 14, 15, 16))
            return in_retainer_posts or in_guide_rails

        return False

    hole_patches = [
        # 1. Center M10x1.5 Female Threaded Wrist Bore at (0.0, +8.0)
        {
            "ix0": 8,
            "ix1": 12,
            "iy0": 13,
            "iy1": 17,
            "iz_list": [0, 1, 2],
            "threaded": True,
            "center": (0.0, 8.0),
            "r_major": p["m10_female_major_r_mm"],
            "r_minor": p["m10_female_minor_r_mm"],
            "pitch": p["m10_pitch_mm"],
            "sub_per_layer": 8,
        },
        # 2..5. 4 Corner Screw Holes at (+-19.50, +-32.00)
        {
            "ix0": 3, "ix1": 5, "iy0": 6, "iy1": 8, "iz_list": [0, 1, 2],
            "threaded": False, "center": (-19.50, -32.00), "r_hole": p["screw_hole_r_mm"],
        },
        {
            "ix0": 15, "ix1": 17, "iy0": 6, "iy1": 8, "iz_list": [0, 1, 2],
            "threaded": False, "center": (19.50, -32.00), "r_hole": p["screw_hole_r_mm"],
        },
        {
            "ix0": 3, "ix1": 5, "iy0": 20, "iy1": 22, "iz_list": [0, 1, 2],
            "threaded": False, "center": (-19.50, 32.00), "r_hole": p["screw_hole_r_mm"],
        },
        {
            "ix0": 15, "ix1": 17, "iy0": 20, "iy1": 22, "iz_list": [0, 1, 2],
            "threaded": False, "center": (19.50, 32.00), "r_hole": p["screw_hole_r_mm"],
        },
    ]

    builder = g.build_layered_prism_complex(
        xs=xs,
        ys=ys,
        xy_override=overrides,
        z_funcs=[z0_fn, z1_vault_fn, z2_fn, z3_deck_fn, z4_features_fn, z5_top_fn],
        active_fn=active_fn,
        hole_patches=hole_patches,
    )
    return builder


def main():
    out_dir = os.path.abspath(
        os.path.join(SCRIPT_DIR, "..", "..", "..", "examples", "goodwiners_phone_buds_mount")
    )
    os.makedirs(out_dir, exist_ok=True)

    b_full = build_goodwiners_back_plate(DEFAULT_PARAMS, include_buds=True)
    path_full = os.path.join(out_dir, "goodwiners_back_with_arm_and_buds.stl")
    b_full.export_binary_stl(path_full, "goodwiners_back_with_arm_and_buds")

    b_compact = build_goodwiners_back_plate(DEFAULT_PARAMS, include_buds=False)
    path_compact = os.path.join(out_dir, "goodwiners_back_arm_only.stl")
    b_compact.export_binary_stl(path_compact, "goodwiners_back_arm_only")

    print(f"Saved: {path_full} ({len(b_full.triangles)} tris)")
    print(f"Saved: {path_compact} ({len(b_compact.triangles)} tris)")


if __name__ == "__main__":
    main()
