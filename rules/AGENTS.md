# 3D Model & Parametric CAD Studio — Core Engineering Rules

Whenever the user asks to design, generate, modify, optimize, or inspect a 3D model, CAD part, enclosure, bracket, mechanical assembly, or printable object, adhere to these engineering and design rules:

## 1. Exact Parametric Architecture & Output Folder Structure (Zero Magic Numbers)
- **Parametric First**: Never hardcode magic coordinates inside geometry operations. Declare all primary dimensions, wall thicknesses, fastener sizes, fillets, and fit clearances as named constants or a structured configuration dictionary at the top of every script/model (in millimeters `mm` unless explicitly specified otherwise).
- **Derived Dimensions**: Compute dependent positions mathematically from primary parameters (e.g., `inner_width = outer_width - 2 * wall_thickness`, `boss_offset = outer_width / 2 - corner_radius`).
- **Dual Deliverables**: Always produce both the **editable parametric source** (`.py` CAD script and/or `.scad` OpenSCAD script) AND the **compiled watertight mesh** (`.stl` / `.obj`) plus an **interactive 3D CAD viewer artifact** (`.html`) when presenting the model.
- **Dedicated `models/<model_name>/` Output Directory**: Never place newly generated or custom models inside `examples/`. Always save every generated model in its own dedicated subfolder under `models/<model_name>/` in the root of the project (`<workspace_root>/models/<model_name>/`). Keep `examples/` strictly for static built-in reference templates.
- **GitHub Auto-Sync on Plugin Changes**: Whenever any file in the plugin (`rules/`, `skills/`, `mcp/`, `agents/`, `scripts/`, `cpp_studio_app/`, `plugin.json`, `README.md`, or `.gitignore`) is modified, commit and push the changes to `origin main` (`https://github.com/Lunar-Entertainment/Antigravity-3D-Model-Plugin.git`). The `models/` directory is tracked via `models/.gitkeep` while `models/*` is git-ignored so user-generated 3D models stay local.

## 2. Structural Sturdiness & Mechanical Integrity ("Right & Sturdy")
Never output fragile, paper-thin, or sharp-cornered primitives for functional parts. Apply industrial mechanical design principles automatically:
- **Minimum Wall Thickness**:
  - Light cosmetic / non-load walls: `>= 1.2 mm` (3 perimeters at 0.4 mm nozzle).
  - Standard functional enclosures & organizers: `>= 2.0 mm` to `2.4 mm`.
  - Load-bearing brackets, mounts, clamps, & structural joints: `>= 3.2 mm` to `5.0 mm`.
- **Stress Concentration Mitigation**:
  - Apply **fillets** (`R >= 1.5 mm` to `4.0 mm`) on all internal 90° corners and boss roots to reduce stress concentration factor ($K_t$).
  - Apply **chamfers** (`0.6 mm` to `1.2 mm` at 45°) on bottom build-plate edges to eliminate "elephant's foot" dimensional error and ease part removal.
  - Add **triangular gussets or reinforcement ribs** whenever a wall or flange cantilevers at 90° under bending load. Rib thickness should be `0.6x` to `0.75x` the nominal wall thickness to prevent thermal sink marks while maximizing section modulus.
- **Bosses & Fastener Reinforcement**:
  - Screw bosses must have an outer diameter of at least `2.2x` to `2.5x` the screw nominal diameter (or `hole_diameter + 2 * 2.0 mm`) and connect to adjacent walls with web ribs if taller than `2x` their outer diameter.

## 3. Standard Clearances & Fit Tolerances (FDM / SLA / CNC Ready)
Apply calibrated real-world manufacturing clearances instead of zero-clearance boolean cuts:
- **Press / Interference Fit** (bearings, dowel pins, permanent join): `+0.00 mm` to `+0.05 mm` radial (`+0.05 mm` diameter).
- **Snug / Locational Transition Fit** (removable lids, friction caps, sliding rails): `+0.15 mm` to `+0.20 mm` per mating gap (`0.30–0.40 mm` total diametral clearance).
- **Loose / Running Fit** (hinges, rotating shafts, free-sliding drawers): `+0.30 mm` to `+0.45 mm` radial (`0.60–0.80 mm` total diametral clearance).
- **Standard Metric Fastener Holes (Medium Clearance / Heat-Set / Nut Trap)**:
  - `M2`: Clearance `Ø2.4 mm` | Counterbore `Ø4.4 x 2.2 mm` | Hex Nut Trap `4.2 mm` flats | Heat-Set Boss Hole `Ø3.2 mm`
  - `M2.5`: Clearance `Ø2.9 mm` | Counterbore `Ø5.4 x 2.7 mm` | Hex Nut Trap `5.2 mm` flats | Heat-Set Boss Hole `Ø4.0 mm`
  - `M3`: Clearance `Ø3.4 mm` | Counterbore `Ø6.2 x 3.2 mm` | Hex Nut Trap `5.7 mm` flats (`6.58 mm` corners) | Heat-Set Boss Hole `Ø4.0–4.2 mm`
  - `M4`: Clearance `Ø4.5 mm` | Counterbore `Ø8.0 x 4.2 mm` | Hex Nut Trap `7.2 mm` flats (`8.31 mm` corners) | Heat-Set Boss Hole `Ø5.6 mm`
  - `M5`: Clearance `Ø5.5 mm` | Counterbore `Ø9.5 x 5.2 mm` | Hex Nut Trap `8.2 mm` flats (`9.47 mm` corners) | Heat-Set Boss Hole `Ø6.4 mm`
  - `M6`: Clearance `Ø6.6 mm` | Counterbore `Ø11.0 x 6.2 mm` | Hex Nut Trap `10.2 mm` flats (`11.78 mm` corners) | Heat-Set Boss Hole `Ø8.0 mm`
  - Use the `cad_calculate_engineering_fit` MCP tool whenever exact fastener, snap-fit, or tolerance numbers are required.

## 4. Printability & Design for Manufacturing (DFM) Optimization
- **Overhang Control (45° Rule)**: Avoid unsupported overhangs exceeding 45° from vertical. Replace horizontal step overhangs with 45° transition chamfers.
- **Horizontal Holes**: For horizontal bores `> Ø6 mm`, use a **teardrop profile** (120°/90° pointed crown) or flat-top bridge so the upper arch prints cleanly without sagging into the bore tolerance.
- **Counterbores Upside-Down**: When a counterbored hole is printed with the counterbore at the bottom and smaller clearance hole above, add a `0.2–0.4 mm` sacrificial bridging layer or stepped two-stage bridge so it prints cleanly with zero supports.
- **Layer Orientation Strategy**: Orient parts so primary tensile and bending stresses run **parallel** to the build plate (along continuous filament paths) rather than pulling Z-layers apart (delamination axis).
- **Multi-Part Build-Plate Spacing (Anti-Collision)**: Never hardcode guesswork XY offsets when combining multiple parts onto a single build plate. Always use `cad_engine.auto_plate_parts(named_meshes, min_gap_mm=12.0)` to compute exact per-part bounding boxes and maintain at least `12.0 mm` XY clearance between adjacent parts so brims, skirts, or first-layer squish can never fuse parts together.

## 5. Mandatory Real-Time Live Studio Artifact & Verification Gate
Whenever the user asks to create, modify, or iterate on a 3D model, **always** provide a live-updating 3D Studio Inspector artifact (`<artifact_dir>/live_cad_studio.html`):
1. **Initialize Live Blueprint First**: At the start of modeling, initialize `<artifact_dir>/live_cad_studio.html` using `generate_viewer.py --init-blueprint X Y Z --out-html <artifact_dir>/live_cad_studio.html` (or `cad_init_live_studio`) and register it as a user-facing artifact (`write_file` with `ArtifactMetadata: {UserFacing: true, RequestFeedback: false}`).
2. **Stream Model Updates In-Place (Camera & Settings Locked)**:
   - Pass `--live-viewer <artifact_dir>/live_cad_studio.html --stream-delay 0.35` to `cad_engine.py` (or `live_viewer_html` to `cad_generate_parametric_part`).
   - In addition, the plugin's `PostToolUse` hook (`scripts/live_sync_hook.py`) automatically watches for any new or modified `.stl` / `.obj` file and pushes its triangles into `<artifact_dir>/live_model_data.js` + `<artifact_dir>/live_cad_studio.html`.
   - The viewer hot-swaps **only the 3D model and engineering metrics** every 450ms via `live_model_data.js` and locks camera angles (`yaw`, `pitch`, `zoom`, `pan`) and settings (`shader mode`, `Z-slicer`, `calipers`) in `window.name` + `localStorage` so the user's view is never reset.
3. **Automated Engineering Audit**:
   - Run `cad_verify_mesh` (MCP tool) or `verify_model.py` on the generated `.stl` / `.obj` file.
   - Verify that **Watertight / Manifold** status is `PASS` (`0` open boundary edges, `0` non-manifold edges, `0` degenerate faces), `part_collision_detected` is `false` (`min_inter_part_gap_mm >= 12.0 mm` for multi-part plates), and **Exact Bounding Box** (`X`, `Y`, `Z` in mm) matches the user's requested external dimensions within `±0.05 mm`.
4. **Embed Inline**: Include `<agent-embed src="file:///<artifact_dir>/live_cad_studio.html"></agent-embed>` in your response so the user can orbit, slice, and inspect the live model directly in chat or on mobile.
