# 3D Model & Parametric CAD Studio (`3d-model-studio`)

An Antigravity plugin for **fast, exact-measurement, structurally sturdy, and print/CNC-ready parametric 3D modeling**.

## Included Customizations

### 1. MCP Server (`3d-model-studio-mcp`)
Configured via [`mcp_config.json`](./mcp_config.json) and powered by [`mcp/cad_studio_server.py`](./mcp/cad_studio_server.py) (zero external dependencies required):
- **`cad_calculate_engineering_fit`**: Computes exact metric fastener holes (`M1.6`–`M10` close/medium/free clearance, socket counterbores, 90° countersinks, hex nut traps, brass heat-set insert bosses, self-tap holes), mating fit clearances (`press`, `snug`, `sliding`, `loose`, `hinge`), material shrinkage factors, structural rib ratios, and cantilever snap-fit safe deflection limits.
- **`cad_init_live_studio`**: Initializes `<artifact_dir>/live_cad_studio.html` immediately with target `[width_x, depth_y, height_z]` mm caliper blueprint dimensions so the user can watch the 3D model construct live.
- **`cad_generate_parametric_part`**: Generates 100% watertight manifold 3D models (`.stl`, `.obj`, and editable `.scad` OpenSCAD code) from 11 precision parametric generators (`enclosure_box`, `enclosure_lid`, `l_bracket`, `flanged_spacer`, `grid_organizer`, `mounting_plate`, `spur_gear`, `saddle_clamp`, `bearing_pillow_block`, `pcb_standoff_frame`, `dovetail_rail_mount`) and streams construction checkpoints live to `live_cad_studio.html`.
- **`cad_verify_mesh`**: Universal Binary/ASCII `.stl` and `.obj` engineering auditor — verifies watertight manifold topology (`0` open/non-manifold edges), compares exact bounding box against target dimensions, and calculates volume, center of mass, filament/metal weight, and overhang percentage (`>45°`).
- **`cad_render_interactive_viewer`**: Generates and live-syncs the interactive 3D CAD Studio HTML widget (`<agent-embed>` and side-pane artifact compatible) with 450ms hot-swap model polling (`live_model_data.js`) and locked camera/settings state (`window.name` + `localStorage`).

### 2. Automatic `PostToolUse` Live Sync Hook ([`hooks.json`](./hooks.json) + [`scripts/live_sync_hook.py`](./scripts/live_sync_hook.py))
Automatically detects whenever any tool call creates or updates an `.stl` or `.obj` file and pushes the updated 3D mesh into `<artifactDirectoryPath>/live_model_data.js` and `<artifactDirectoryPath>/live_cad_studio.html` in real time—updating **only the 3D model** without resetting camera angles or inspector settings.

### 3. Always-On Engineering Rules ([`rules/AGENTS.md`](./rules/AGENTS.md))
Enforces parametric code architecture, minimum structural wall thicknesses (`>= 2.0–2.4 mm` for enclosures, `>= 3.2–5.0 mm` for brackets), stress-relief fillets, elephant's-foot base chamfers, calibrated mating tolerances, and mandatory topological/dimensional verification before delivery.

### 3. Skills (`skills/`)
- **[`parametric-cad-modeling`](./skills/parametric-cad-modeling/SKILL.md)**: Complete toolkit & API (`ManifoldMeshBuilder`, 2D contour generators, polygon-with-holes bridge ear-clipping triangulator, stratified solid builder) for both template parts and bespoke 3D geometries.
- **[`structural-design-dfm`](./skills/structural-design-dfm/SKILL.md)**: Mechanical engineering experience design skill with [reference tables](./skills/structural-design-dfm/references/engineering_tables.md) for fasteners, tolerances, snap-fits, gussets, and anisotropic print orientation.
- **[`custom-model-workflow`](./skills/custom-model-workflow/SKILL.md)**: Fast 5-stage workflow from custom request to verified model + interactive 3D preview.

### 4. Subagents (`agents/`)
- **[`cad-architect`](./agents/cad-architect.md)**: Specialized subagent for designing complex parametric assemblies.
- **[`structural-auditor`](./agents/structural-auditor.md)**: Specialized subagent for auditing mesh integrity, tolerances, and structural sturdiness.
