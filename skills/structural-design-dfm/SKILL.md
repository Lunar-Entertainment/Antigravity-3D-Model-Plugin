---
name: structural-design-dfm
description: >-
  Mechanical engineering, structural sturdiness optimization, tolerance calibration, and Design for
  Manufacturing (DFM / 3D printing / CNC) strategies. Use this skill when designing load-bearing
  parts, snap-fits, enclosures, interlocking joints, fastener bosses, or optimizing part durability.
---

# Structural Design & DFM Optimization Skill

Use this skill to ensure every 3D model is **mechanically sturdy, dimensionally accurate, and effortlessly manufacturable**. For full fastener and tolerance tables, read [engineering_tables.md](./references/engineering_tables.md).

## 1. Structural Sturdiness Strategies ("Right & Sturdy")

1. **Eliminate Sharp Internal Corners ($K_t$ Stress Reduction)**:
   - A sharp 90° internal corner concentrates bending stress by $2.5\times$ to $4.0\times$, causing parts to snap along the corner seam.
   - Always add a root fillet of radius $R \ge 0.6 \times t_{\text{wall}}$ (minimum `1.5 mm`, ideally `3.0–6.0 mm` on brackets).
2. **Use Gussets & Ribs Instead of Massive Solid Blocks**:
   - Thick solid blocks (`>10 mm`) warp due to internal thermal contraction and waste material.
   - Instead, use a sturdy nominal wall (`2.4–4.0 mm`) reinforced by triangular gussets or perpendicular ribs of thickness $t_{\text{rib}} = 0.65 \times t_{\text{wall}}$ and height $3\times$ to $4\times t_{\text{wall}}$.
   - Because bending stiffness scales with the **cube of height** ($I = \frac{b h^3}{12}$), doubling section height with a thin gusset rib increases stiffness by **$800\%$** using only ~$15\%$ extra material.
3. **Anisotropic Layer Orientation (FDM Critical Rule)**:
   - 3D printed parts are strongest along continuous filament perimeters ($XY$) and weakest in interlayer adhesion ($Z$).
   - **L-Brackets & Clips**: Always orient with the profile flat on the build plate (extruding width along $Z$) so perimeter loops run unbroken around the bend and through the gusset.
   - **Standoffs & Tall Pins**: Never print thin vertical pins `< Ø5 mm` standing in $Z$; they shear easily. Instead, use a reinforcement fillet at the base, a press-fit dowel/screw bore, or print horizontally with a flat bottom and teardrop top.

## 2. Precision Joinery & Multi-Part Assemblies

1. **Stepped Rabbet Lip (Enclosure Lids)**:
   - Never rely on flat butt-joints for lids. Use a stepped rabbet rim (`1.2–1.6 mm` thick, `2.0–3.0 mm` tall) with a **`0.16–0.20 mm` radial clearance** (`0.32–0.40 mm` total width/depth difference) between the male rim and female cavity.
2. **Fastener Boss Design**:
   - **Self-Tapping Plastic Boss**: Hole diameter $= 0.88 \times d_{\text{nominal}}$ (`Ø2.7 mm` for M3), outer boss diameter $= 2.4 \times d_{\text{nominal}}$.
   - **Heat-Set Brass Insert Boss**: Use tapered or stepped bore (`Ø4.0–4.2 mm` for M3, `Ø5.6 mm` for M4) with at least `2.0 mm` radial wall thickness around the insert so molten plastic doesn't bulge outward.
   - **Captive Hex Nut Trap**: Across-flats clearance $= S_{\text{ISO}} + 0.20\text{ mm}$ (`5.7 mm` for M3, `7.2 mm` for M4, `8.2 mm` for M5).
3. **Cantilever Snap-Fit Design**:
   - Keep beam length-to-thickness ratio $L / t \ge 5:1$ (ideally $7:1$ to $10:1$).
   - Taper the beam thickness from $t$ at the root to $0.6t$ at the hook tip to distribute strain evenly along the beam (allowing $60\%$ more safe deflection than a constant-thickness beam).
   - Add a generous root fillet ($R \ge t$) where the snap arm meets the base wall.

## 3. Printability & Zero-Support DFM Rules

- **Base Elephant's Foot Chamfer**: Add a `0.6–1.0 mm × 45°` chamfer on the bottom outer contour touching the build plate. This guarantees exact outer dimensions on the first layers and prevents sharp bottom burrs.
- **Overhangs**: Keep all unsupported overhangs $\le 45^\circ$ from vertical.
- **Horizontal Bores**: Convert horizontal holes $> \varnothing 6\text{ mm}$ into 90°/120° **teardrop profiles** so the top arch prints without sagging into the shaft clearance.
