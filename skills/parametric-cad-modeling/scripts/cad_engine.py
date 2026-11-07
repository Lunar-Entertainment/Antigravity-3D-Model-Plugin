#!/usr/bin/env python3
"""
3D Model & Parametric CAD Studio — Pure-Python Parametric CAD & Mesh Engine
Generates exact-dimension, 100% watertight manifold 3D meshes (.stl, .obj) and
parametric source scripts (.scad) with structural engineering features
(fillets, chamfers, gussets, bosses, counterbores, hex traps, teardrops)
and real-time progressive construction checkpoints for the Live Studio Inspector.
"""

import argparse
import json
import math
import os
import struct
import sys
import time
from typing import Dict, List, Optional, Tuple

Point2D = Tuple[float, float]
Point3D = Tuple[float, float, float]
Triangle3D = Tuple[Point3D, Point3D, Point3D]


# ============================================================================
# 1. Exact 2D Contour Generators (CCW Orientation by default)
# ============================================================================

def snap2d(pt: Point2D, tol: int = 5) -> Point2D:
    return (round(float(pt[0]), tol), round(float(pt[1]), tol))


def snap3d(pt: Point3D, tol: int = 5) -> Point3D:
    return (round(float(pt[0]), tol), round(float(pt[1]), tol), round(float(pt[2]), tol))


def signed_area_2d(poly: List[Point2D]) -> float:
    area = 0.0
    n = len(poly)
    for i in range(n):
        x1, y1 = poly[i]
        x2, y2 = poly[(i + 1) % n]
        area += (x1 * y2 - x2 * y1)
    return 0.5 * area


def ensure_ccw(poly: List[Point2D]) -> List[Point2D]:
    if signed_area_2d(poly) < 0:
        return list(reversed(poly))
    return list(poly)


def ensure_cw(poly: List[Point2D]) -> List[Point2D]:
    if signed_area_2d(poly) > 0:
        return list(reversed(poly))
    return list(poly)


def circle_contour(cx: float, cy: float, r: float, segments: int = 48) -> List[Point2D]:
    if r <= 0:
        raise ValueError(f"Circle radius must be > 0, got {r}")
    pts = []
    for i in range(segments):
        theta = 2.0 * math.pi * i / segments
        pts.append(snap2d((cx + r * math.cos(theta), cy + r * math.sin(theta))))
    return ensure_ccw(pts)


def regular_polygon_contour(
    cx: float, cy: float, r_circum: float, sides: int = 6, angle_deg: float = 0.0
) -> List[Point2D]:
    pts = []
    ang0 = math.radians(angle_deg)
    for i in range(sides):
        theta = ang0 + 2.0 * math.pi * i / sides
        pts.append(snap2d((cx + r_circum * math.cos(theta), cy + r_circum * math.sin(theta))))
    return ensure_ccw(pts)


def hex_across_flats_contour(
    cx: float, cy: float, across_flats: float, angle_deg: float = 0.0
) -> List[Point2D]:
    r_circum = (across_flats / 2.0) / math.cos(math.pi / 6.0)
    return regular_polygon_contour(cx, cy, r_circum, sides=6, angle_deg=angle_deg)


def teardrop_contour(
    cx: float, cy: float, r: float, segments: int = 48, point_angle_deg: float = 90.0
) -> List[Point2D]:
    """Teardrop hole profile (+Y pointed crown) for supportless horizontal printing."""
    half_angle = math.radians(point_angle_deg / 2.0)
    t_start = math.pi / 2.0 + half_angle
    t_end = 2.0 * math.pi + (math.pi / 2.0 - half_angle)
    apex_y = cy + r / math.sin(half_angle)
    pts = [snap2d((cx, apex_y))]
    arc_segments = max(12, segments - 1)
    for i in range(arc_segments + 1):
        theta = t_start + (t_end - t_start) * i / arc_segments
        pts.append(snap2d((cx + r * math.cos(theta), cy + r * math.sin(theta))))
    return ensure_ccw(pts)


def rounded_rect_contour(
    cx: float,
    cy: float,
    width: float,
    depth: float,
    radius: float,
    segments_per_corner: int = 10,
) -> List[Point2D]:
    if width <= 0 or depth <= 0:
        raise ValueError(f"Dimensions must be > 0, got {width}x{depth}")
    r = max(0.0, min(radius, width / 2.0 - 0.01, depth / 2.0 - 0.01))
    if r < 1e-4:
        hw, hd = width / 2.0, depth / 2.0
        return ensure_ccw([
            snap2d((cx - hw, cy - hd)),
            snap2d((cx + hw, cy - hd)),
            snap2d((cx + hw, cy + hd)),
            snap2d((cx - hw, cy + hd)),
        ])
    hw, hd = width / 2.0 - r, depth / 2.0 - r
    corners = [
        (cx + hw, cy + hd, 0.0, math.pi / 2.0),
        (cx - hw, cy + hd, math.pi / 2.0, math.pi),
        (cx - hw, cy - hd, math.pi, 1.5 * math.pi),
        (cx + hw, cy - hd, 1.5 * math.pi, 2.0 * math.pi),
    ]
    pts = []
    for ccx, ccy, a0, a1 in corners:
        for i in range(segments_per_corner + 1):
            theta = a0 + (a1 - a0) * i / segments_per_corner
            pt = snap2d((ccx + r * math.cos(theta), ccy + r * math.sin(theta)))
            if not pts or pts[-1] != pt:
                pts.append(pt)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    return ensure_ccw(pts)


def slot_contour(
    cx: float,
    cy: float,
    length: float,
    width: float,
    angle_deg: float = 0.0,
    segments: int = 32,
) -> List[Point2D]:
    """Stadium / obround slot contour (total length x width)."""
    r = width / 2.0
    straight = max(0.0, length - width)
    if straight < 1e-4:
        return circle_contour(cx, cy, r, segments=segments)
    half_s = straight / 2.0
    half_seg = max(8, segments // 2)
    local_pts = []
    for i in range(half_seg + 1):
        theta = -math.pi / 2.0 + math.pi * i / half_seg
        local_pts.append((half_s + r * math.cos(theta), r * math.sin(theta)))
    for i in range(half_seg + 1):
        theta = math.pi / 2.0 + math.pi * i / half_seg
        local_pts.append((-half_s + r * math.cos(theta), r * math.sin(theta)))
    ang = math.radians(angle_deg)
    ca, sa = math.cos(ang), math.sin(ang)
    pts = []
    for lx, ly in local_pts:
        rx = cx + lx * ca - ly * sa
        ry = cy + lx * sa + ly * ca
        pt = snap2d((rx, ry))
        if not pts or pts[-1] != pt:
            pts.append(pt)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts.pop()
    return ensure_ccw(pts)


# ============================================================================
# 2. Polygon-with-Holes Ear-Clipping Triangulator (Manifold Bridge Algorithm)
# ============================================================================

def _cross2d(o: Point2D, a: Point2D, b: Point2D) -> float:
    return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])


def _point_in_triangle_2d(p: Point2D, a: Point2D, b: Point2D, c: Point2D) -> bool:
    if p == a or p == b or p == c:
        return False
    c1 = _cross2d(a, b, p)
    c2 = _cross2d(b, c, p)
    c3 = _cross2d(c, a, p)
    eps = -1e-9
    return (c1 >= eps and c2 >= eps and c3 >= eps)


def _segments_intersect(a: Point2D, b: Point2D, c: Point2D, d: Point2D) -> bool:
    if a == c or a == d or b == c or b == d:
        return False
    d1 = _cross2d(c, d, a)
    d2 = _cross2d(c, d, b)
    d3 = _cross2d(a, b, c)
    d4 = _cross2d(a, b, d)
    if ((d1 > 1e-9 and d2 < -1e-9) or (d1 < -1e-9 and d2 > 1e-9)) and (
        (d3 > 1e-9 and d4 < -1e-9) or (d3 < -1e-9 and d4 > 1e-9)
    ):
        return True
    return False


def _merge_hole_into_outer(outer: List[Point2D], hole_cw: List[Point2D]) -> List[Point2D]:
    """Connects a CW hole contour into a CCW outer contour via a mutually visible bridge."""
    m_idx = max(range(len(hole_cw)), key=lambda i: (hole_cw[i][0], hole_cw[i][1]))
    mx, my = hole_cw[m_idx]

    best_idx = 0
    best_dist = float("inf")
    n = len(outer)

    for i in range(n):
        if outer.count(outer[i]) > 1:
            continue
        ox, oy = outer[i]
        if ox < mx - 1e-6:
            continue
        dist = math.hypot(ox - mx, oy - my)
        if dist >= best_dist:
            continue
        intersects = False
        for j in range(n):
            a, b = outer[j], outer[(j + 1) % n]
            if _segments_intersect((mx, my), (ox, oy), a, b):
                intersects = True
                break
        if not intersects:
            nh = len(hole_cw)
            for j in range(nh):
                a, b = hole_cw[j], hole_cw[(j + 1) % nh]
                if _segments_intersect((mx, my), (ox, oy), a, b):
                    intersects = True
                    break
        if not intersects:
            best_dist = dist
            best_idx = i

    merged = []
    for i in range(best_idx + 1):
        merged.append(outer[i])
    nh = len(hole_cw)
    for i in range(nh + 1):
        merged.append(hole_cw[(m_idx + i) % nh])
    for i in range(best_idx, n):
        merged.append(outer[i])
    return merged


def triangulate_polygon_with_holes(
    outer: List[Point2D], holes: Optional[List[List[Point2D]]] = None
) -> List[Tuple[Point2D, Point2D, Point2D]]:
    """
    Triangulates a 2D polygon with arbitrary inner holes into CCW 2D triangles.
    Preserves exact boundary vertices so adjacent vertical walls share 100% manifold edges.
    """
    poly = ensure_ccw(outer)
    if holes:
        cw_holes = [ensure_cw(h) for h in holes if len(h) >= 3]
        cw_holes.sort(key=lambda h: max(pt[0] for pt in h), reverse=True)
        for h in cw_holes:
            poly = _merge_hole_into_outer(poly, h)

    pts = list(poly)
    tris: List[Tuple[Point2D, Point2D, Point2D]] = []
    max_iters = len(pts) * len(pts) + 200
    iters = 0

    while len(pts) > 3 and iters < max_iters:
        iters += 1
        n = len(pts)
        ear_found = False

        for pass_num in (0, 1):
            for i in range(n):
                prev_pt = pts[(i - 1) % n]
                curr_pt = pts[i]
                next_pt = pts[(i + 1) % n]

                cross = _cross2d(prev_pt, curr_pt, next_pt)
                tol = 1e-9 if pass_num == 0 else -1e-7
                if cross <= tol:
                    continue

                contains_other = False
                for j in range(n):
                    p = pts[j]
                    if p == prev_pt or p == curr_pt or p == next_pt:
                        continue
                    if _point_in_triangle_2d(p, prev_pt, curr_pt, next_pt):
                        contains_other = True
                        break

                if not contains_other:
                    if abs(cross) > 1e-10:
                        tris.append((prev_pt, curr_pt, next_pt))
                    pts.pop(i)
                    ear_found = True
                    break
            if ear_found:
                break

        if not ear_found:
            prev_pt, curr_pt, next_pt = pts[0], pts[1], pts[2]
            if abs(_cross2d(prev_pt, curr_pt, next_pt)) > 1e-10:
                tris.append((prev_pt, curr_pt, next_pt))
            pts.pop(1)

    if len(pts) == 3:
        if abs(_cross2d(pts[0], pts[1], pts[2])) > 1e-10:
            tris.append((pts[0], pts[1], pts[2]))

    return tris


# ============================================================================
# 3. 3D Mesh Builder & Manifold Verification (with Live Studio Checkpoints)
# ============================================================================

class ManifoldMeshBuilder:
    def __init__(self) -> None:
        self.triangles: List[Triangle3D] = []
        self.checkpoints: List[Dict[str, object]] = []

    def mark_checkpoint(self, label: str) -> None:
        """Records a construction stage checkpoint for live progressive visualization."""
        self.checkpoints.append({
            "label": label,
            "triangle_count": len(self.triangles),
        })

    def add_triangle(self, p1: Point3D, p2: Point3D, p3: Point3D) -> None:
        a, b, c = snap3d(p1), snap3d(p2), snap3d(p3)
        if a == b or b == c or c == a:
            return
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx = uy * vz - uz * vy
        ny = uz * vx - ux * vz
        nz = ux * vy - uy * vx
        if (nx * nx + ny * ny + nz * nz) < 1e-16:
            return
        self.triangles.append((a, b, c))

    def add_quad(self, p1: Point3D, p2: Point3D, p3: Point3D, p4: Point3D) -> None:
        self.add_triangle(p1, p2, p3)
        self.add_triangle(p1, p3, p4)

    def add_horizontal_face(
        self,
        outer: List[Point2D],
        holes: Optional[List[List[Point2D]]],
        z: float,
        facing_up: bool = True,
    ) -> None:
        tris_2d = triangulate_polygon_with_holes(outer, holes)
        for a, b, c in tris_2d:
            p1 = (a[0], a[1], z)
            p2 = (b[0], b[1], z)
            p3 = (c[0], c[1], z)
            if facing_up:
                self.add_triangle(p1, p2, p3)
            else:
                self.add_triangle(p1, p3, p2)

    def add_lofted_contour_wall(
        self,
        contour_bottom: List[Point2D],
        z_bottom: float,
        contour_top: List[Point2D],
        z_top: float,
        is_outer_wall: bool = True,
    ) -> None:
        cb = ensure_ccw(contour_bottom)
        ct = ensure_ccw(contour_top)
        if len(cb) != len(ct):
            raise ValueError(f"Loft vertex count mismatch: {len(cb)} vs {len(ct)}")
        n = len(cb)
        for i in range(n):
            b0 = (cb[i][0], cb[i][1], z_bottom)
            b1 = (cb[(i + 1) % n][0], cb[(i + 1) % n][1], z_bottom)
            t0 = (ct[i][0], ct[i][1], z_top)
            t1 = (ct[(i + 1) % n][0], ct[(i + 1) % n][1], z_top)
            if is_outer_wall:
                self.add_triangle(b0, b1, t1)
                self.add_triangle(b0, t1, t0)
            else:
                self.add_triangle(b0, t1, b1)
                self.add_triangle(b0, t0, t1)

    def add_extruded_wall(
        self,
        contour: List[Point2D],
        z_bottom: float,
        z_top: float,
        is_outer_wall: bool = True,
    ) -> None:
        self.add_lofted_contour_wall(contour, z_bottom, contour, z_top, is_outer_wall=is_outer_wall)

    def verify_topology(self) -> Dict[str, object]:
        """Checks watertightness, edge incidence, volume, surface area, and bounding box."""
        directed_edges: Dict[Tuple[Point3D, Point3D], int] = {}
        min_x = min_y = min_z = float("inf")
        max_x = max_y = max_z = float("-inf")
        total_area = 0.0
        signed_volume = 0.0
        overhang_area = 0.0

        for a, b, c in self.triangles:
            for pt in (a, b, c):
                min_x = min(min_x, pt[0])
                max_x = max(max_x, pt[0])
                min_y = min(min_y, pt[1])
                max_y = max(max_y, pt[1])
                min_z = min(min_z, pt[2])
                max_z = max(max_z, pt[2])

            for e in ((a, b), (b, c), (c, a)):
                directed_edges[e] = directed_edges.get(e, 0) + 1

            ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
            vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
            nx = uy * vz - uz * vy
            ny = uz * vx - ux * vz
            nz = ux * vy - uy * vx
            norm_len = math.sqrt(nx * nx + ny * ny + nz * nz)
            tri_area = 0.5 * norm_len
            total_area += tri_area

            if norm_len > 1e-12:
                nz_unit = nz / norm_len
                avg_z = (a[2] + b[2] + c[2]) / 3.0
                if nz_unit < -0.708 and avg_z > min_z + 0.05:
                    overhang_area += tri_area

            signed_volume += (
                a[0] * (b[1] * c[2] - b[2] * c[1])
                - a[1] * (b[0] * c[2] - b[2] * c[0])
                + a[2] * (b[0] * c[1] - b[1] * c[0])
            ) / 6.0

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

        is_watertight = (open_edges == 0 and non_manifold_edges == 0 and len(self.triangles) > 0)
        dims = {
            "width_x": round(max_x - min_x, 4) if self.triangles else 0.0,
            "depth_y": round(max_y - min_y, 4) if self.triangles else 0.0,
            "height_z": round(max_z - min_z, 4) if self.triangles else 0.0,
            "min": [round(min_x, 4), round(min_y, 4), round(min_z, 4)] if self.triangles else [0, 0, 0],
            "max": [round(max_x, 4), round(max_y, 4), round(max_z, 4)] if self.triangles else [0, 0, 0],
        }
        return {
            "is_watertight_manifold": is_watertight,
            "triangle_count": len(self.triangles),
            "open_boundary_edges": open_edges,
            "non_manifold_edges": non_manifold_edges,
            "bounding_box_mm": dims,
            "volume_mm3": round(abs(signed_volume), 2),
            "volume_cm3": round(abs(signed_volume) / 1000.0, 3),
            "surface_area_mm2": round(total_area, 2),
            "overhang_area_mm2": round(overhang_area, 2),
            "overhang_ratio_pct": round(100.0 * overhang_area / max(total_area, 1e-6), 2),
            "checkpoints": self.checkpoints,
            "estimated_mass_grams": {
                "PLA_100pct_infill": round((abs(signed_volume) / 1000.0) * 1.24, 2),
                "PLA_25pct_gyroid_est": round((abs(signed_volume) / 1000.0) * 1.24 * 0.42, 2),
                "PETG_100pct_infill": round((abs(signed_volume) / 1000.0) * 1.27, 2),
                "ABS_ASA_100pct_infill": round((abs(signed_volume) / 1000.0) * 1.05, 2),
                "Aluminum_6061_CNC": round((abs(signed_volume) / 1000.0) * 2.70, 2),
            },
        }

    def export_binary_stl(self, filepath: str, header_text: str = "3D-Model-Studio Parametric CAD") -> None:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        hdr = header_text.encode("ascii", errors="ignore")[:80].ljust(80, b"\x00")
        with open(filepath, "wb") as f:
            f.write(hdr)
            f.write(struct.pack("<I", len(self.triangles)))
            for a, b, c in self.triangles:
                ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
                vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
                nx = uy * vz - uz * vy
                ny = uz * vx - ux * vz
                nz = ux * vy - uy * vx
                length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
                nx, ny, nz = nx / length, ny / length, nz / length
                f.write(
                    struct.pack(
                        "<12fH",
                        nx, ny, nz,
                        a[0], a[1], a[2],
                        b[0], b[1], b[2],
                        c[0], c[1], c[2],
                        0,
                    )
                )

    def export_obj(self, filepath: str) -> None:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        vert_map: Dict[Point3D, int] = {}
        verts: List[Point3D] = []
        faces: List[Tuple[int, int, int]] = []
        for a, b, c in self.triangles:
            idxs = []
            for pt in (a, b, c):
                if pt not in vert_map:
                    vert_map[pt] = len(verts) + 1
                    verts.append(pt)
                idxs.append(vert_map[pt])
            faces.append((idxs[0], idxs[1], idxs[2]))
        with open(filepath, "w", encoding="utf-8") as f:
            f.write("# Generated by 3D Model & Parametric CAD Studio\n")
            for vx, vy, vz in verts:
                f.write(f"v {vx:.5f} {vy:.5f} {vz:.5f}\n")
            for i1, i2, i3 in faces:
                f.write(f"f {i1} {i2} {i3}\n")


def auto_plate_parts(
    named_meshes: List[Tuple[str, "ManifoldMeshBuilder"]],
    min_gap_mm: float = 12.0,
    max_row_width_mm: float = 180.0,
) -> "ManifoldMeshBuilder":
    """
    Packs multiple ManifoldMeshBuilder parts onto a build plate (Z=0) with a guaranteed
    minimum XY bounding-box clearance `min_gap_mm` (default 12.0 mm) between every part
    so parts NEVER touch, collide, or fuse together on the printer!
    """
    plated = ManifoldMeshBuilder()
    cursor_x = 0.0
    cursor_y = 0.0
    row_max_depth = 0.0

    placed_items: List[Tuple[str, List[Triangle3D]]] = []

    for label, part in named_meshes:
        if not part.triangles:
            continue
        min_x = min(min(a[0], b[0], c[0]) for a, b, c in part.triangles)
        max_x = max(max(a[0], b[0], c[0]) for a, b, c in part.triangles)
        min_y = min(min(a[1], b[1], c[1]) for a, b, c in part.triangles)
        max_y = max(max(a[1], b[1], c[1]) for a, b, c in part.triangles)
        min_z = min(min(a[2], b[2], c[2]) for a, b, c in part.triangles)

        part_w = max_x - min_x
        part_d = max_y - min_y

        if cursor_x > 0 and (cursor_x + part_w > max_row_width_mm):
            cursor_x = 0.0
            cursor_y += row_max_depth + min_gap_mm
            row_max_depth = 0.0

        dx = cursor_x - min_x
        dy = cursor_y - min_y
        dz = -min_z

        shifted_tris: List[Triangle3D] = []
        for a, b, c in part.triangles:
            shifted_tris.append((
                snap3d((a[0] + dx, a[1] + dy, a[2] + dz)),
                snap3d((b[0] + dx, b[1] + dy, b[2] + dz)),
                snap3d((c[0] + dx, c[1] + dy, c[2] + dz)),
            ))
        placed_items.append((label, shifted_tris))
        cursor_x += part_w + min_gap_mm
        row_max_depth = max(row_max_depth, part_d)

    # Re-center the entire plate around (0, 0) in XY
    all_pts = [pt for _, tris in placed_items for tri in tris for pt in tri]
    if all_pts:
        plate_cx = 0.5 * (min(p[0] for p in all_pts) + max(p[0] for p in all_pts))
        plate_cy = 0.5 * (min(p[1] for p in all_pts) + max(p[1] for p in all_pts))
        for label, tris in placed_items:
            for a, b, c in tris:
                plated.add_triangle(
                    (a[0] - plate_cx, a[1] - plate_cy, a[2]),
                    (b[0] - plate_cx, b[1] - plate_cy, b[2]),
                    (c[0] - plate_cx, c[1] - plate_cy, c[2]),
                )
            plated.mark_checkpoint(label)

    return plated


# ============================================================================
# 4. Parametric Functional Part Generators (11 Industrial Templates)
# ============================================================================

def build_parametric_enclosure(params: Dict[str, object]) -> Tuple[ManifoldMeshBuilder, str]:
    w = float(params.get("outer_width", 100.0))
    d = float(params.get("outer_depth", 70.0))
    h = float(params.get("outer_height", 35.0))
    wall = max(1.6, float(params.get("wall_thickness", 2.4)))
    floor_t = max(1.6, float(params.get("floor_thickness", 2.4)))
    r_outer = max(2.0, float(params.get("corner_radius", 5.0)))
    base_chamfer = min(float(params.get("base_chamfer", 1.0)), wall * 0.6, floor_t * 0.6)
    boss_hole_d = float(params.get("boss_hole_diameter", 3.2))
    boss_outer_d = max(boss_hole_d + 4.0, float(params.get("boss_outer_diameter", 7.6)))
    lip_height = float(params.get("lip_height", 2.4))
    lip_thickness = min(wall * 0.5, float(params.get("lip_thickness", 1.2)))
    seg_corner = int(params.get("segments_per_corner", 10))

    mesh = ManifoldMeshBuilder()
    z0 = 0.0
    z_chamfer = base_chamfer
    z_floor = floor_t
    z_wall_top = h - lip_height if lip_height > 0 else h
    z_lip_top = h

    outer_base = rounded_rect_contour(
        0, 0, w - 2 * base_chamfer, d - 2 * base_chamfer, max(0.5, r_outer - base_chamfer), seg_corner
    )
    outer_main = rounded_rect_contour(0, 0, w, d, r_outer, seg_corner)
    r_inner = max(1.0, r_outer - wall)
    inner_cavity = rounded_rect_contour(0, 0, w - 2 * wall, d - 2 * wall, r_inner, seg_corner)

    boss_inset = wall + boss_outer_d / 2.0 + 0.8
    bx = w / 2.0 - boss_inset
    by = d / 2.0 - boss_inset
    boss_centers = [(-bx, -by), (bx, -by), (bx, by), (-bx, by)]
    boss_outers = [circle_contour(cx, cy, boss_outer_d / 2.0, segments=28) for (cx, cy) in boss_centers]
    boss_holes = [circle_contour(cx, cy, boss_hole_d / 2.0, segments=28) for (cx, cy) in boss_centers]

    # Stage 1: Base & 45-deg Chamfer
    mesh.add_horizontal_face(outer_base, holes=None, z=z0, facing_up=False)
    if base_chamfer > 1e-4:
        mesh.add_lofted_contour_wall(outer_base, z0, outer_main, z_chamfer, is_outer_wall=True)
    mesh.mark_checkpoint("Stage 1: Base Plate & 45° Chamfer")

    # Stage 2: Outer Structural Shell & Inner Floor
    if base_chamfer > 1e-4:
        mesh.add_extruded_wall(outer_main, z_chamfer, z_wall_top, is_outer_wall=True)
    else:
        mesh.add_extruded_wall(outer_main, z0, z_wall_top, is_outer_wall=True)
    mesh.add_horizontal_face(inner_cavity, holes=boss_outers, z=z_floor, facing_up=True)
    for bh in boss_holes:
        mesh.add_horizontal_face(bh, holes=None, z=z_floor, facing_up=True)
    mesh.add_extruded_wall(inner_cavity, z_floor, z_wall_top, is_outer_wall=False)
    mesh.mark_checkpoint("Stage 2: Perimeter Walls & Cavity")

    # Stage 3: Internal Corner Screw Bosses
    for bo, bh in zip(boss_outers, boss_holes):
        mesh.add_extruded_wall(bo, z_floor, z_wall_top, is_outer_wall=True)
        mesh.add_extruded_wall(bh, z_floor, z_wall_top, is_outer_wall=False)
        mesh.add_horizontal_face(bo, holes=[bh], z=z_wall_top, facing_up=True)
    mesh.mark_checkpoint("Stage 3: 4× Corner M-Screw Bosses")

    # Stage 4: Top Interlocking Rabbet Lip
    if lip_height > 1e-4:
        lip_outer = rounded_rect_contour(
            0, 0, w - 2 * (wall - lip_thickness), d - 2 * (wall - lip_thickness),
            max(1.0, r_outer - (wall - lip_thickness)), seg_corner
        )
        mesh.add_horizontal_face(outer_main, holes=[lip_outer], z=z_wall_top, facing_up=True)
        mesh.add_extruded_wall(lip_outer, z_wall_top, z_lip_top, is_outer_wall=True)
        mesh.add_extruded_wall(inner_cavity, z_wall_top, z_lip_top, is_outer_wall=False)
        mesh.add_horizontal_face(lip_outer, holes=[inner_cavity], z=z_lip_top, facing_up=True)
    else:
        mesh.add_horizontal_face(outer_main, holes=[inner_cavity], z=z_wall_top, facing_up=True)
    mesh.mark_checkpoint("Stage 4: Top Rabbet Lid Lip & Manifold Seal")

    scad_code = f"""// Parametric Sturdy Enclosure — Generated by 3D Model Studio
$fn = 64;
outer_width = {w};
outer_depth = {d};
outer_height = {h};
wall_thickness = {wall};
floor_thickness = {floor_t};
corner_radius = {r_outer};
boss_outer_d = {boss_outer_d};
boss_hole_d = {boss_hole_d};
lip_height = {lip_height};
lip_thickness = {lip_thickness};

module rounded_box(w, d, h, r) {{
    linear_extrude(height = h)
    offset(r = r)
    square([w - 2*r, d - 2*r], center = true);
}}

difference() {{
    rounded_box(outer_width, outer_depth, outer_height, corner_radius);
    translate([0, 0, floor_thickness])
        rounded_box(outer_width - 2*wall_thickness, outer_depth - 2*wall_thickness, outer_height, max(1, corner_radius - wall_thickness));
}}
for (sx = [-1, 1], sy = [-1, 1]) {{
    translate([sx * ({bx:.3f}), sy * ({by:.3f}), floor_thickness])
    difference() {{
        cylinder(d = boss_outer_d, h = outer_height - lip_height - floor_thickness);
        translate([0, 0, -0.1]) cylinder(d = boss_hole_d, h = outer_height);
    }}
}}
"""
    return mesh, scad_code


def build_reinforced_l_bracket(params: Dict[str, object]) -> Tuple[ManifoldMeshBuilder, str]:
    leg_a = float(params.get("flange_a_length", 60.0))
    leg_b = float(params.get("flange_b_length", 60.0))
    width = float(params.get("width", 40.0))
    t = max(3.0, float(params.get("thickness", 5.0)))
    r_fillet = max(2.0, float(params.get("inner_fillet_radius", 6.0)))
    gusset_h = float(params.get("gusset_thickness", 8.0))
    gusset_len = min(leg_a - t - 4.0, leg_b - t - 4.0, float(params.get("gusset_length", 32.0)))
    hole_d = float(params.get("hole_diameter", 4.5))

    mesh = ManifoldMeshBuilder()
    fillet_pts = []
    segs = 14
    cx, cy = t + r_fillet, t + r_fillet
    for i in range(segs + 1):
        theta = -math.pi / 2.0 - (math.pi / 2.0) * i / segs
        fillet_pts.append(snap2d((cx + r_fillet * math.cos(theta), cy + r_fillet * math.sin(theta))))

    gusset_profile = ensure_ccw([
        snap2d((0.0, 0.0)),
        snap2d((leg_a, 0.0)),
        snap2d((leg_a, t)),
        snap2d((t + gusset_len, t)),
        snap2d((t, t + gusset_len)),
        snap2d((t, leg_b)),
        snap2d((0.0, leg_b)),
    ])

    z0 = 0.0
    z1 = max(2.0, (width - gusset_h) / 2.0)
    z2 = width - z1
    z3 = width

    use_gusset = (gusset_h > 0.1 and gusset_len > r_fillet + 2.0 and z1 > 0.1)
    l_profile = ensure_ccw(
        [
            snap2d((0.0, 0.0)),
            snap2d((leg_a, 0.0)),
            snap2d((leg_a, t)),
        ]
        + ([snap2d((t + gusset_len, t))] if use_gusset else [])
        + fillet_pts
        + ([snap2d((t, t + gusset_len))] if use_gusset else [])
        + [
            snap2d((t, leg_b)),
            snap2d((0.0, leg_b)),
        ]
    )

    if use_gusset:
        web_only = ensure_ccw(
            [snap2d((t, t + gusset_len))]
            + list(reversed(fillet_pts))
            + [snap2d((t + gusset_len, t))]
        )
        mesh.add_horizontal_face(l_profile, holes=None, z=z0, facing_up=False)
        mesh.add_extruded_wall(l_profile, z0, z1, is_outer_wall=True)
        mesh.mark_checkpoint("Stage 1: Lower L-Flange Section & Root Fillet")

        mesh.add_horizontal_face(web_only, holes=None, z=z1, facing_up=False)
        mesh.add_extruded_wall(gusset_profile, z1, z2, is_outer_wall=True)
        mesh. add_horizontal_face(web_only, holes=None, z=z2, facing_up=True)
        mesh.mark_checkpoint("Stage 2: Central Triangular Gusset Reinforcement")

        mesh.add_extruded_wall(l_profile, z2, z3, is_outer_wall=True)
        mesh.add_horizontal_face(l_profile, holes=None, z=z3, facing_up=True)
        mesh.mark_checkpoint("Stage 3: Upper L-Flange Section & Manifold Cap")
    else:
        mesh.add_horizontal_face(l_profile, holes=None, z=z0, facing_up=False)
        mesh.add_extruded_wall(l_profile, z0, z3, is_outer_wall=True)
        mesh.add_horizontal_face(l_profile, holes=None, z=z3, facing_up=True)
        mesh.mark_checkpoint("Stage 1: Complete Filleted L-Bracket")

    scad_code = f"// Heavy-Duty Reinforced L-Bracket ({leg_a}x{leg_b}x{width}mm, {t}mm thick)\n"
    return mesh, scad_code


def build_flanged_spacer_or_mount(params: Dict[str, object]) -> Tuple[ManifoldMeshBuilder, str]:
    flange_d = float(params.get("flange_diameter", 50.0))
    flange_t = float(params.get("flange_thickness", 5.0))
    boss_d = float(params.get("boss_diameter", 24.0))
    total_h = float(params.get("total_height", 25.0))
    bore_d = float(params.get("bore_diameter", 10.2))
    bolt_circle_d = float(params.get("bolt_circle_diameter", 38.0))
    bolt_count = int(params.get("bolt_count", 4))
    bolt_hole_d = float(params.get("bolt_hole_diameter", 3.4))
    base_chamfer = min(1.0, float(params.get("base_chamfer", 0.8)))

    mesh = ManifoldMeshBuilder()
    outer_base = circle_contour(0, 0, flange_d / 2.0 - base_chamfer, segments=64)
    outer_flange = circle_contour(0, 0, flange_d / 2.0, segments=64)
    outer_boss = circle_contour(0, 0, boss_d / 2.0, segments=64)
    inner_bore = circle_contour(0, 0, bore_d / 2.0, segments=48)

    bolt_holes = []
    if bolt_count > 0 and bolt_circle_d > boss_d + bolt_hole_d + 1.0:
        for i in range(bolt_count):
            ang = 2.0 * math.pi * i / bolt_count
            bx = (bolt_circle_d / 2.0) * math.cos(ang)
            by = (bolt_circle_d / 2.0) * math.sin(ang)
            bolt_holes.append(circle_contour(bx, by, bolt_hole_d / 2.0, segments=28))

    all_base_holes = [inner_bore] + bolt_holes

    mesh.add_horizontal_face(outer_base, holes=all_base_holes, z=0.0, facing_up=False)
    if base_chamfer > 1e-4:
        mesh.add_lofted_contour_wall(outer_base, 0.0, outer_flange, base_chamfer, is_outer_wall=True)
        mesh.add_extruded_wall(outer_flange, base_chamfer, flange_t, is_outer_wall=True)
    else:
        mesh.add_extruded_wall(outer_flange, 0.0, flange_t, is_outer_wall=True)
    for bh in bolt_holes:
        mesh.add_extruded_wall(bh, 0.0, flange_t, is_outer_wall=False)
    mesh.mark_checkpoint("Stage 1: Base Flange & Bolt Circle Holes")

    if total_h > flange_t + 1e-4:
        mesh.add_horizontal_face(outer_flange, holes=[outer_boss] + bolt_holes, z=flange_t, facing_up=True)
        mesh.add_extruded_wall(outer_boss, flange_t, total_h, is_outer_wall=True)
        mesh.add_horizontal_face(outer_boss, holes=[inner_bore], z=total_h, facing_up=True)
    else:
        mesh.add_horizontal_face(outer_flange, holes=all_base_holes, z=flange_t, facing_up=True)

    mesh.add_extruded_wall(inner_bore, 0.0, max(flange_t, total_h), is_outer_wall=False)
    mesh.mark_checkpoint("Stage 2: Central Boss & Precision Through-Bore")

    scad_code = f"// Precision Flanged Mount (Flange Ø{flange_d}mm, Boss Ø{boss_d}mm, Bore Ø{bore_d}mm)\n"
    return mesh, scad_code


def build_grid_organizer_tray(params: Dict[str, object]) -> Tuple[ManifoldMeshBuilder, str]:
    w = float(params.get("outer_width", 120.0))
    d = float(params.get("outer_depth", 80.0))
    h = float(params.get("outer_height", 30.0))
    rows = max(1, int(params.get("rows", 2)))
    cols = max(1, int(params.get("cols", 3)))
    wall = max(1.6, float(params.get("wall_thickness", 2.4)))
    div_t = max(1.2, float(params.get("divider_thickness", 2.0)))
    floor_t = max(1.6, float(params.get("floor_thickness", 2.4)))
    r_outer = max(2.0, float(params.get("corner_radius", 5.0)))
    r_cell = max(1.5, float(params.get("cell_corner_radius", 3.0)))
    base_chamfer = min(1.0, float(params.get("base_chamfer", 0.8)))

    mesh = ManifoldMeshBuilder()
    outer_base = rounded_rect_contour(0, 0, w - 2 * base_chamfer, d - 2 * base_chamfer, max(0.5, r_outer - base_chamfer))
    outer_main = rounded_rect_contour(0, 0, w, d, r_outer)

    avail_w = w - 2 * wall - (cols - 1) * div_t
    avail_d = d - 2 * wall - (rows - 1) * div_t
    cell_w = avail_w / cols
    cell_d = avail_d / rows

    cells = []
    start_x = -w / 2.0 + wall + cell_w / 2.0
    start_y = -d / 2.0 + wall + cell_d / 2.0
    for r_idx in range(rows):
        for c_idx in range(cols):
            cx = start_x + c_idx * (cell_w + div_t)
            cy = start_y + r_idx * (cell_d + div_t)
            cells.append(rounded_rect_contour(cx, cy, cell_w, cell_d, min(r_cell, cell_w * 0.3, cell_d * 0.3), 8))

    mesh.add_horizontal_face(outer_base, holes=None, z=0.0, facing_up=False)
    if base_chamfer > 1e-4:
        mesh.add_lofted_contour_wall(outer_base, 0.0, outer_main, base_chamfer, is_outer_wall=True)
        mesh.add_extruded_wall(outer_main, base_chamfer, h, is_outer_wall=True)
    else:
        mesh.add_extruded_wall(outer_main, 0.0, h, is_outer_wall=True)
    mesh.mark_checkpoint("Stage 1: Outer Tray Shell & Base Chamfer")

    for cell in cells:
        mesh.add_horizontal_face(cell, holes=None, z=floor_t, facing_up=True)
        mesh.add_extruded_wall(cell, floor_t, h, is_outer_wall=False)
    mesh.add_horizontal_face(outer_main, holes=cells, z=h, facing_up=True)
    mesh.mark_checkpoint(f"Stage 2: {rows}×{cols} Filleted Compartment Grid")

    scad_code = f"// Parametric Grid Organizer Tray ({rows}x{cols}, {w}x{d}x{h}mm)\n"
    return mesh, scad_code


def build_custom_plate_or_extrusion(params: Dict[str, object]) -> Tuple[ManifoldMeshBuilder, str]:
    w = float(params.get("width", 80.0))
    d = float(params.get("depth", 50.0))
    h = float(params.get("thickness", 4.0))
    r_outer = float(params.get("corner_radius", 4.0))
    base_chamfer = min(float(params.get("base_chamfer", 0.6)), h * 0.3)
    features = params.get("holes", [])

    mesh = ManifoldMeshBuilder()
    outer_base = rounded_rect_contour(0, 0, w - 2 * base_chamfer, d - 2 * base_chamfer, max(0.2, r_outer - base_chamfer))
    outer_main = rounded_rect_contour(0, 0, w, d, r_outer)

    hole_contours = []
    if isinstance(features, list):
        for feat in features:
            if not isinstance(feat, dict):
                continue
            ftype = str(feat.get("type", "circle")).lower()
            fx = float(feat.get("x", 0.0))
            fy = float(feat.get("y", 0.0))
            if ftype == "slot":
                flen = float(feat.get("length", 12.0))
                fwid = float(feat.get("width", 4.5))
                fang = float(feat.get("angle_deg", 0.0))
                hole_contours.append(slot_contour(fx, fy, flen, fwid, fang))
            elif ftype == "hex":
                flats = float(feat.get("across_flats", 5.7))
                hole_contours.append(hex_across_flats_contour(fx, fy, flats))
            elif ftype == "rect":
                rw = float(feat.get("width", 10.0))
                rd = float(feat.get("depth", 10.0))
                rr = float(feat.get("radius", 1.5))
                hole_contours.append(rounded_rect_contour(fx, fy, rw, rd, rr))
            else:
                fd = float(feat.get("diameter", 3.4))
                hole_contours.append(circle_contour(fx, fy, fd / 2.0, segments=32))

    mesh.add_horizontal_face(outer_base, holes=hole_contours, z=0.0, facing_up=False)
    if base_chamfer > 1e-4:
        mesh.add_lofted_contour_wall(outer_base, 0.0, outer_main, base_chamfer, is_outer_wall=True)
        mesh.add_extruded_wall(outer_main, base_chamfer, h, is_outer_wall=True)
    else:
        mesh.add_extruded_wall(outer_main, 0.0, h, is_outer_wall=True)
    for hc in hole_contours:
        mesh.add_extruded_wall(hc, 0.0, h, is_outer_wall=False)
    mesh.add_horizontal_face(outer_main, holes=hole_contours, z=h, facing_up=True)
    mesh.mark_checkpoint("Stage 1: Precision Plate & Feature Cutouts")

    scad_code = f"// Custom Parametric Mounting Plate ({w}x{d}x{h}mm)\n"
    return mesh, scad_code


def build_enclosure_lid(params: Dict[str, object]) -> Tuple[ManifoldMeshBuilder, str]:
    w = float(params.get("outer_width", 100.0))
    d = float(params.get("outer_depth", 70.0))
    lid_t = max(2.0, float(params.get("lid_thickness", 3.0)))
    wall = max(1.6, float(params.get("wall_thickness", 2.4)))
    r_outer = max(2.0, float(params.get("corner_radius", 5.0)))
    clearance = float(params.get("fit_clearance", 0.20))
    lip_h = float(params.get("lip_height", 2.0))
    boss_outer_d = float(params.get("boss_outer_diameter", 7.6))
    screw_clearance_d = float(params.get("screw_clearance_diameter", 3.4))
    base_chamfer = min(0.8, float(params.get("base_chamfer", 0.6)))

    mesh = ManifoldMeshBuilder()
    outer_base = rounded_rect_contour(0, 0, w - 2 * base_chamfer, d - 2 * base_chamfer, max(0.5, r_outer - base_chamfer))
    outer_main = rounded_rect_contour(0, 0, w, d, r_outer)

    boss_inset = wall + boss_outer_d / 2.0 + 0.8
    bx = w / 2.0 - boss_inset
    by = d / 2.0 - boss_inset
    hole_centers = [(-bx, -by), (bx, -by), (bx, by), (-bx, by)]
    screw_holes = [circle_contour(cx, cy, screw_clearance_d / 2.0, segments=28) for (cx, cy) in hole_centers]

    rim_outer_w = w - 2 * (wall + clearance)
    rim_outer_d = d - 2 * (wall + clearance)
    rim_t = 1.6
    rim_outer = rounded_rect_contour(0, 0, rim_outer_w, rim_outer_d, max(1.0, r_outer - wall - clearance))
    rim_inner = rounded_rect_contour(0, 0, rim_outer_w - 2 * rim_t, rim_outer_d - 2 * rim_t, max(0.8, r_outer - wall - clearance - rim_t))

    mesh.add_horizontal_face(outer_base, holes=screw_holes, z=0.0, facing_up=False)
    if base_chamfer > 1e-4:
        mesh.add_lofted_contour_wall(outer_base, 0.0, outer_main, base_chamfer, is_outer_wall=True)
        mesh.add_extruded_wall(outer_main, base_chamfer, lid_t, is_outer_wall=True)
    else:
        mesh.add_extruded_wall(outer_main, 0.0, lid_t, is_outer_wall=True)
    for sh in screw_holes:
        mesh.add_extruded_wall(sh, 0.0, lid_t, is_outer_wall=False)
    mesh.mark_checkpoint("Stage 1: Lid Plate & Screw Clearance Bores")

    if lip_h > 1e-4 and rim_outer_w - 2 * rim_t > 2 * bx + boss_outer_d:
        mesh.add_horizontal_face(outer_main, holes=[rim_outer], z=lid_t, facing_up=True)
        mesh.add_horizontal_face(rim_inner, holes=screw_holes, z=lid_t, facing_up=True)
        mesh.add_extruded_wall(rim_outer, lid_t, lid_t + lip_h, is_outer_wall=True)
        mesh.add_extruded_wall(rim_inner, lid_t, lid_t + lip_h, is_outer_wall=False)
        mesh.add_horizontal_face(rim_outer, holes=[rim_inner], z=lid_t + lip_h, facing_up=True)
    else:
        mesh.add_horizontal_face(outer_main, holes=screw_holes, z=lid_t, facing_up=True)
    mesh.mark_checkpoint("Stage 2: Calibrated Alignment Lip")

    scad_code = f"// Parametric Enclosure Lid ({w}x{d}x{lid_t}mm) with {clearance}mm fit clearance\n"
    return mesh, scad_code


def build_spur_gear(params: Dict[str, object]) -> Tuple[ManifoldMeshBuilder, str]:
    mod = float(params.get("module_mm", 2.0))
    teeth = max(8, int(params.get("teeth", 24)))
    thickness = float(params.get("thickness", 8.0))
    bore_d = float(params.get("bore_diameter", 8.2))

    pitch_r = 0.5 * mod * teeth
    outer_r = pitch_r + mod
    root_r = max(bore_d / 2.0 + 1.5, pitch_r - 1.25 * mod)

    gear_pts: List[Point2D] = []
    pitch_angle = 2.0 * math.pi / teeth
    half_tooth = pitch_angle / 4.0
    tip_half = half_tooth * 0.62
    root_half = half_tooth * 1.28

    for i in range(teeth):
        center_ang = i * pitch_angle
        angles_radii = [
            (center_ang - pitch_angle * 0.5, root_r),
            (center_ang - root_half, root_r),
            (center_ang - half_tooth, pitch_r),
            (center_ang - tip_half, outer_r),
            (center_ang + tip_half, outer_r),
            (center_ang + half_tooth, pitch_r),
            (center_ang + root_half, root_r),
        ]
        for ang, rad in angles_radii:
            pt = snap2d((rad * math.cos(ang), rad * math.sin(ang)))
            if not gear_pts or gear_pts[-1] != pt:
                gear_pts.append(pt)

    gear_contour = ensure_ccw(gear_pts)
    bore_contour = circle_contour(0, 0, bore_d / 2.0, segments=48)

    mesh = ManifoldMeshBuilder()
    mesh.add_horizontal_face(gear_contour, holes=[bore_contour], z=0.0, facing_up=False)
    mesh.add_extruded_wall(gear_contour, 0.0, thickness, is_outer_wall=True)
    mesh.add_extruded_wall(bore_contour, 0.0, thickness, is_outer_wall=False)
    mesh.add_horizontal_face(gear_contour, holes=[bore_contour], z=thickness, facing_up=True)
    mesh.mark_checkpoint(f"Stage 1: {teeth}-Tooth Module {mod}mm Spur Gear & Bore")

    scad_code = f"// Metric Spur Gear: Module={mod}mm, Teeth={teeth}, PitchD={2*pitch_r:.2f}mm\n"
    return mesh, scad_code


def build_saddle_clamp(params: Dict[str, object]) -> Tuple[ManifoldMeshBuilder, str]:
    """
    Heavy-duty Omega (Ω) pipe / tube / cable saddle clamp printed on its side (Z = clamp width)
    for maximum hoop tensile strength along continuous filament perimeters!
    """
    pipe_d = float(params.get("pipe_diameter", 25.0))
    wall = max(2.4, float(params.get("arch_thickness", 4.0)))
    ear_len = max(10.0, float(params.get("ear_length", 16.0)))
    ear_t = max(3.0, float(params.get("ear_thickness", 5.0)))
    width = float(params.get("clamp_width", 20.0))

    r_in = pipe_d / 2.0
    r_out = r_in + wall
    total_half_x = r_out + ear_len

    # Construct 2D Omega profile in XY plane:
    # Bottom flat ears at y = 0, arch center at (0, r_in)
    pts: List[Point2D] = []
    # Right ear bottom -> right ear outer -> right ear top
    pts.append(snap2d((r_in, 0.0)))
    pts.append(snap2d((total_half_x, 0.0)))
    pts.append(snap2d((total_half_x, ear_t)))

    # Outer arch from angle = asin(ear_t / r_out) around to pi - asin(ear_t / r_out)
    ang_start = math.asin(min(0.95, ear_t / r_out))
    segs = 36
    for i in range(segs + 1):
        theta = ang_start + (math.pi - 2.0 * ang_start) * i / segs
        pts.append(snap2d((r_out * math.cos(theta), r_in + r_out * math.sin(theta))))

    # Left ear top -> left ear outer -> left ear bottom
    pts.append(snap2d((-total_half_x, ear_t)))
    pts.append(snap2d((-total_half_x, 0.0)))
    pts.append(snap2d((-r_in, 0.0)))

    # Inner arch from pi back to 0 (centered at (0, r_in))
    for i in range(segs + 1):
        theta = math.pi - math.pi * i / segs
        pts.append(snap2d((r_in * math.cos(theta), r_in + r_in * math.sin(theta))))

    # Clean duplicate consecutive points
    clean_pts: List[Point2D] = []
    for p in pts:
        if not clean_pts or clean_pts[-1] != p:
            clean_pts.append(p)
    if len(clean_pts) > 1 and clean_pts[0] == clean_pts[-1]:
        clean_pts.pop()

    omega_contour = ensure_ccw(clean_pts)
    mesh = ManifoldMeshBuilder()
    mesh.add_horizontal_face(omega_contour, holes=None, z=0.0, facing_up=False)
    mesh.add_extruded_wall(omega_contour, 0.0, width, is_outer_wall=True)
    mesh.add_horizontal_face(omega_contour, holes=None, z=width, facing_up=True)
    mesh.mark_checkpoint(f"Stage 1: Heavy-Duty Ω Saddle Clamp (Ø{pipe_d}mm)")

    scad_code = f"// Heavy-Duty Pipe/Cable Saddle Clamp (Pipe Ø{pipe_d}mm, Width {width}mm)\n"
    return mesh, scad_code


def build_bearing_pillow_block(params: Dict[str, object]) -> Tuple[ManifoldMeshBuilder, str]:
    """
    Self-standing Bearing / Shaft Pillow Block Mount (default calibrated for 608ZZ bearing Ø22.05mm).
    """
    base_w = float(params.get("base_width", 68.0))
    base_t = float(params.get("base_thickness", 7.0))
    block_h = float(params.get("total_height", 34.0))
    depth = float(params.get("depth", 16.0))
    bore_d = float(params.get("bearing_bore_diameter", 22.1))
    center_h = float(params.get("shaft_center_height", 18.0))

    r_bore = bore_d / 2.0
    r_tower = max(r_bore + 4.5, (block_h - center_h))
    hw = base_w / 2.0

    # Outer profile in XY plane (X = width, Y = height, extruded along Z = depth)
    # Tangency from base shoulder to circular tower top centered at (0, center_h)
    pts: List[Point2D] = [
        snap2d((-hw, 0.0)),
        snap2d((hw, 0.0)),
        snap2d((hw, base_t)),
        snap2d((r_tower + 4.0, base_t)),
    ]
    segs = 32
    for i in range(segs + 1):
        theta = math.pi * i / segs
        pts.append(snap2d((r_tower * math.cos(theta), center_h + r_tower * math.sin(theta))))
    pts.extend([
        snap2d((-r_tower - 4.0, base_t)),
        snap2d((-hw, base_t)),
    ])

    outer_contour = ensure_ccw(pts)
    bore_hole = circle_contour(0.0, center_h, r_bore, segments=48)

    mesh = ManifoldMeshBuilder()
    mesh.add_horizontal_face(outer_contour, holes=[bore_hole], z=0.0, facing_up=False)
    mesh.add_extruded_wall(outer_contour, 0.0, depth, is_outer_wall=True)
    mesh.add_extruded_wall(bore_hole, 0.0, depth, is_outer_wall=False)
    mesh.add_horizontal_face(outer_contour, holes=[bore_hole], z=depth, facing_up=True)
    mesh.mark_checkpoint(f"Stage 1: Pillow Block Housing & Ø{bore_d}mm Bearing Bore")

    scad_code = f"// Bearing Pillow Block (Bore Ø{bore_d}mm, Base {base_w}x{depth}mm)\n"
    return mesh, scad_code


def build_pcb_standoff_frame(params: Dict[str, object]) -> Tuple[ManifoldMeshBuilder, str]:
    """
    Parametric PCB Carrier / Standoff Frame with 4 corner standoffs, recessed lightweight pocket,
    and precision M2.5 / M3 mounting bores (default Raspberry Pi / standard sensor board 58x49mm hole pattern).
    """
    hole_dx = float(params.get("hole_spacing_x", 58.0))
    hole_dy = float(params.get("hole_spacing_y", 49.0))
    boss_od = float(params.get("standoff_outer_diameter", 8.0))
    hole_d = float(params.get("screw_hole_diameter", 2.7))  # M2.5/M3 self-tap
    base_h = float(params.get("frame_thickness", 3.2))
    standoff_h = float(params.get("standoff_height", 6.0))
    total_h = base_h + standoff_h

    w = hole_dx + boss_od + 4.0
    d = hole_dy + boss_od + 4.0
    r_corner = boss_od / 2.0 + 2.0

    outer_main = rounded_rect_contour(0, 0, w, d, r_corner, 10)
    # Central weight-reduction cutout inside the frame
    cutout_w = max(8.0, hole_dx - boss_od - 4.0)
    cutout_d = max(8.0, hole_dy - boss_od - 4.0)
    center_cutout = rounded_rect_contour(0, 0, cutout_w, cutout_d, 3.0, 8)

    centers = [
        (-hole_dx / 2.0, -hole_dy / 2.0),
        (hole_dx / 2.0, -hole_dy / 2.0),
        (hole_dx / 2.0, hole_dy / 2.0),
        (-hole_dx / 2.0, hole_dy / 2.0),
    ]
    screw_holes = [circle_contour(cx, cy, hole_d / 2.0, 24) for (cx, cy) in centers]
    boss_outers = [circle_contour(cx, cy, boss_od / 2.0, 28) for (cx, cy) in centers]

    base_holes = [center_cutout] + screw_holes

    mesh = ManifoldMeshBuilder()
    mesh.add_horizontal_face(outer_main, holes=base_holes, z=0.0, facing_up=False)
    mesh.add_extruded_wall(outer_main, 0.0, base_h, is_outer_wall=True)
    mesh.add_extruded_wall(center_cutout, 0.0, base_h, is_outer_wall=False)
    mesh.mark_checkpoint("Stage 1: Stiffened PCB Frame Base")

    # Top of frame at base_h (with 4 standoff bosses rising to total_h)
    mesh.add_horizontal_face(outer_main, holes=[center_cutout] + boss_outers, z=base_h, facing_up=True)
    for bo, sh in zip(boss_outers, screw_holes):
        mesh.add_extruded_wall(bo, base_h, total_h, is_outer_wall=True)
        mesh.add_extruded_wall(sh, 0.0, total_h, is_outer_wall=False)
        mesh.add_horizontal_face(bo, holes=[sh], z=total_h, facing_up=True)
    mesh.mark_checkpoint("Stage 2: 4× Integrated Corner Standoff Pillars")

    scad_code = f"// PCB Standoff Carrier Frame ({hole_dx}x{hole_dy}mm hole spacing)\n"
    return mesh, scad_code


def build_dovetail_rail_mount(params: Dict[str, object]) -> Tuple[ManifoldMeshBuilder, str]:
    """
    60-degree self-supporting Female Dovetail Quick-Release Rail Receiver (extruded along Z = length).
    """
    outer_w = float(params.get("outer_width", 44.0))
    outer_h = float(params.get("total_thickness", 12.0))
    length = float(params.get("rail_length", 60.0))
    slot_bottom_w = float(params.get("dovetail_base_width", 24.0))
    slot_depth = float(params.get("dovetail_depth", 6.0))
    clearance = float(params.get("fit_clearance", 0.20))

    # 60-degree dovetail overhang: top opening is narrower than slot_bottom_w
    taper_dx = slot_depth / math.tan(math.radians(60.0))
    bw = (slot_bottom_w + 2 * clearance) / 2.0
    tw = bw - taper_dx
    hw = outer_w / 2.0
    y_slot_floor = outer_h - slot_depth

    profile = ensure_ccw([
        snap2d((-hw, 0.0)),
        snap2d((hw, 0.0)),
        snap2d((hw, outer_h)),
        snap2d((tw, outer_h)),
        snap2d((bw, y_slot_floor)),
        snap2d((-bw, y_slot_floor)),
        snap2d((-tw, outer_h)),
        snap2d((-hw, outer_h)),
    ])

    mesh = ManifoldMeshBuilder()
    mesh.add_horizontal_face(profile, holes=None, z=0.0, facing_up=False)
    mesh.add_extruded_wall(profile, 0.0, length, is_outer_wall=True)
    mesh.add_horizontal_face(profile, holes=None, z=length, facing_up=True)
    mesh.mark_checkpoint("Stage 1: 60° Precision Dovetail Receiver Rail")

    scad_code = f"// 60-Degree Dovetail Quick-Release Rail ({outer_w}x{outer_h}x{length}mm)\n"
    return mesh, scad_code


GENERATORS = {
    "enclosure_box": build_parametric_enclosure,
    "enclosure_lid": build_enclosure_lid,
    "l_bracket": build_reinforced_l_bracket,
    "flanged_spacer": build_flanged_spacer_or_mount,
    "grid_organizer": build_grid_organizer_tray,
    "mounting_plate": build_custom_plate_or_extrusion,
    "spur_gear": build_spur_gear,
    "saddle_clamp": build_saddle_clamp,
    "bearing_pillow_block": build_bearing_pillow_block,
    "pcb_standoff_frame": build_pcb_standoff_frame,
    "dovetail_rail_mount": build_dovetail_rail_mount,
}


def generate_part(
    part_type: str,
    params: Dict[str, object],
    output_stl: str,
    output_scad: Optional[str] = None,
    output_obj: Optional[str] = None,
    live_viewer_html: Optional[str] = None,
    stream_stages_delay_sec: float = 0.0,
) -> Dict[str, object]:
    if part_type not in GENERATORS:
        raise ValueError(f"Unknown part_type '{part_type}'. Valid types: {list(GENERATORS.keys())}")
    mesh, scad_code = GENERATORS[part_type](params)
    mesh.export_binary_stl(output_stl)
    if output_scad:
        os.makedirs(os.path.dirname(os.path.abspath(output_scad)), exist_ok=True)
        with open(output_scad, "w", encoding="utf-8") as f:
            f.write(scad_code)
    if output_obj:
        mesh.export_obj(output_obj)
    report = mesh.verify_topology()
    report["part_type"] = part_type
    report["parameters"] = params
    report["output_stl"] = os.path.abspath(output_stl)
    if output_scad:
        report["output_scad"] = os.path.abspath(output_scad)
    if output_obj:
        report["output_obj"] = os.path.abspath(output_obj)

    # Automatic Live Studio Inspector Sync if live_viewer_html or AGY_LIVE_CAD_VIEWER is set
    viewer_target = live_viewer_html or os.environ.get("AGY_LIVE_CAD_VIEWER")
    if viewer_target:
        import generate_viewer
        generate_viewer.sync_live_viewer(
            mesh_filepath=output_stl,
            output_html=viewer_target,
            title=f"Live CAD Studio — {part_type}",
            checkpoints=mesh.checkpoints,
            stream_delay_sec=stream_stages_delay_sec,
        )
        report["live_viewer_html"] = os.path.abspath(viewer_target)

    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate exact parametric 3D CAD models (.stl, .obj, .scad).")
    parser.add_argument("--type", required=True, choices=list(GENERATORS.keys()), help="Parametric part template")
    parser.add_argument("--params", default="{}", help="JSON string of dimensional parameters")
    parser.add_argument("--out-stl", required=True, help="Output binary STL file path")
    parser.add_argument("--out-scad", default=None, help="Optional output OpenSCAD (.scad) file path")
    parser.add_argument("--out-obj", default=None, help="Optional output Wavefront (.obj) file path")
    parser.add_argument(
        "--live-viewer",
        default=None,
        help="Optional path to live_cad_studio.html artifact to stream real-time model updates into",
    )
    parser.add_argument(
        "--stream-delay",
        type=float,
        default=0.0,
        help="Optional delay in seconds between streaming construction stages to the live viewer",
    )
    args = parser.parse_args()

    params = json.loads(args.params)
    report = generate_part(
        args.type,
        params,
        args.out_stl,
        args.out_scad,
        args.out_obj,
        live_viewer_html=args.live_viewer,
        stream_stages_delay_sec=args.stream_delay,
    )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
