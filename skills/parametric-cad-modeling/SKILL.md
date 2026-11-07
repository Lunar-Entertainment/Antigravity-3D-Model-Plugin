---
name: parametric-cad-modeling
description: >-
  Generate exact-dimension, 100% watertight manifold 3D models (.stl, .obj, .scad) and interactive
  3D CAD viewer widgets. Use this skill whenever the user asks to create, model, generate, or export
  a 3D part, enclosure, bracket, gear, mount, organizer, adapter, or custom geometric object.
---

# Parametric 3D CAD Modeling Skill

This skill provides a fast, zero-dependency, exact-measurement parametric 3D modeling pipeline that guarantees **100% watertight manifold meshes** (`0` open boundary edges, `0` non-manifold edges) with exact millimeter dimensions, structural fillets/chamfers, and interactive 3D visual inspection.

## 1. Available MCP Tools & Helper Scripts

Prefer calling the plugin's MCP tools (`3d-model-studio-mcp`) when active, or run the bundled CLI scripts directly:

1. **Engineering Fit & Fastener Calculator**:
   - MCP Tool: `cad_calculate_engineering_fit`
   - Calculates exact hole diameters, counterbores, hex nut traps, heat-set insert bosses, mating clearances (`press`, `snug`, `sliding`, `loose`, `hinge`), and snap-fit cantilever beam limits.
2. **Parametric Part Generator**:
   - MCP Tool: `cad_generate_parametric_part`
   - Script: [cad_engine.py](./scripts/cad_engine.py)
   - Built-in templates:
     - `enclosure_box`: Sturdy rounded electronics/project box with base chamfer, internal corner screw bosses, and stepped lid rabbet lip.
     - `enclosure_lid`: Matching precision lid with calibrated radial fit clearance (`0.20 mm` default), alignment rim, and corner screw clearance holes.
     - `l_bracket`: Heavy-duty reinforced structural L-bracket printed on its side for continuous fiber strength, with inner root fillet and central triangular gusset web.
     - `flanged_spacer`: Cylindrical flanged mount, bushing, or sensor/shaft spacer with bolt-circle mounting holes and precision center bore.
     - `grid_organizer`: Multi-compartment (`rows × cols`) storage tray with filleted interior pockets and chamfered base.
     - `mounting_plate`: Custom structural adapter/mounting plate supporting arbitrary arrays of circular holes, stadium slots (`type: "slot"`), hex traps (`type: "hex"`), and rounded rectangular cutouts (`type: "rect"`).
     - `spur_gear`: Metric module (`module_mm`, `teeth`, `thickness`, `bore_diameter`) involute-style spur gear.
     - `saddle_clamp`: Heavy-duty Omega ($\Omega$) pipe/tube/cable saddle clamp printed on its side for maximum hoop strength.
     - `bearing_pillow_block`: Self-standing shaft/bearing pillow block housing (default calibrated for `608ZZ` $\varnothing 22.1\text{ mm}$ bore).
     - `pcb_standoff_frame`: Stiffened open-frame PCB carrier with 4 integrated corner standoffs and M2.5/M3 screw bores.
     - `dovetail_rail_mount`: 60° self-supporting trapezoidal dovetail quick-release receiver rail with calibrated sliding clearance.
3. **Universal Mesh & Dimension Auditor**:
   - MCP Tool: `cad_verify_mesh`
   - Script: [verify_model.py](./scripts/verify_model.py)
   - Audits any `.stl` or `.obj` file for manifold watertightness, exact bounding box vs target dimensions, overhang percentage (`>45°`), volume, center of mass, and filament weight.
4. **Real-Time Live 3D CAD Studio Inspector & Hot-Swap Streamer**:
   - MCP Tools: `cad_init_live_studio` and `cad_render_interactive_viewer`
   - Script: [generate_viewer.py](./scripts/generate_viewer.py)
   - Generates a live-updating HTML 3D CAD Studio artifact (`<artifact_dir>/live_cad_studio.html`) paired with `<artifact_dir>/live_model_data.js`.
   - Polls `live_model_data.js` every 450ms to hot-swap **only the 3D model geometry, construction stage bar, and HUD metrics** in place while locking camera angles (`yaw`, `pitch`, `zoom`, `pan`) and user settings (`shader mode`, `Z-slicer`, `calipers`) in `window.name` and `localStorage`.

---

## 2. Standard Execution Workflow

### Path A: Fast Template Generation (Enclosures, Lids, Brackets, Flanges, Plates, Trays, Gears)
Run `cad_generate_parametric_part` (or `cad_engine.py`) with exact JSON parameters:

```bash
python3 /home/lunar/Documents/Projects/3d-model-plugin/skills/parametric-cad-modeling/scripts/cad_engine.py \
  --type enclosure_box \
  --params '{"outer_width": 110, "outer_depth": 75, "outer_height": 38, "wall_thickness": 2.4, "floor_thickness": 2.4, "corner_radius": 5.0, "boss_hole_diameter": 4.1}' \
  --out-stl ./enclosure_box.stl \
  --out-scad ./enclosure_box.scad
```

### Path B: Completely Custom Bespoke 3D Geometries
When the user requests a custom geometry beyond the standard templates, write a clean Python script importing `cad_engine`:

```python
import sys
sys.path.insert(0, "/home/lunar/Documents/Projects/3d-model-plugin/skills/parametric-cad-modeling/scripts")
import cad_engine

mesh = cad_engine.ManifoldMeshBuilder()
# 1. Define exact 2D contours using:
#    - cad_engine.rounded_rect_contour(cx, cy, width, depth, radius)
#    - cad_engine.circle_contour(cx, cy, r, segments=48)
#    - cad_engine.slot_contour(cx, cy, length, width, angle_deg=0)
#    - cad_engine.hex_across_flats_contour(cx, cy, across_flats)
#    - cad_engine.teardrop_contour(cx, cy, r)
# 2. Build stratified Z-layers and chamfers:
#    - mesh.add_horizontal_face(outer, holes=[...], z=z_level, facing_up=True/False)
#    - mesh.add_lofted_contour_wall(c_bot, z_bot, c_top, z_top, is_outer_wall=True/False)
#    - mesh.add_extruded_wall(contour, z_bot, z_top, is_outer_wall=True/False)
# 3. Verify and export:
report = mesh.verify_topology()
assert report["is_watertight_manifold"], f"Topology error: {report}"
mesh.export_binary_stl("./custom_part.stl")
```

> [!IMPORTANT]
> **Manifold Transition Rule for `ManifoldMeshBuilder`**:
> Whenever a horizontal step face at height `z` connects a lower cross-section to an upper cross-section, the outer boundary and hole contours of that horizontal face **must share the exact same 2D vertices** as the vertical/lofted walls meeting at `z`. Always assert `report["is_watertight_manifold"] == True`.

### Step 3: Verify & Render Interactive 3D Preview
Always run [verify_model.py](./scripts/verify_model.py) and [generate_viewer.py](./scripts/generate_viewer.py) (into the conversation's artifact directory) and embed the interactive viewer in your response using `<agent-embed src="file:///path/to/viewer.html"></agent-embed>`.
