---
name: custom-model-workflow
description: >-
  Fast, structured end-to-end workflow for turning custom 3D model requests into verified, sturdy,
  exact-dimension CAD models with interactive 3D previews. Use this skill when the user asks to
  design a custom 3D object, solve a mounting/storage problem, or iterate on a 3D design.
---

# Custom 3D Model Design Workflow

Follow this 5-stage engineering workflow to deliver exact, sturdy, print-ready 3D models fast and effortlessly:

## Stage 1: Parametric Specification & Fit Calibration
1. Extract all user-specified measurements (`X`, `Y`, `Z`, hole diameters, wall thicknesses, mating object sizes).
2. For any unspecified secondary dimensions, select **sturdy engineering defaults** automatically rather than stalling:
   - Structural walls: `2.4 mm` (enclosures/trays) or `4.0–5.0 mm` (brackets/mounts).
   - Corner fillets: `3.0–5.0 mm` outer, `1.5–3.0 mm` inner.
   - Base build-plate chamfer: `0.8–1.0 mm × 45°`.
   - Mating clearance: `0.16–0.20 mm` radial for snug fit, `0.35 mm` radial for moving/hinge parts.
3. Call `cad_calculate_engineering_fit` whenever fasteners, snap-fits, or mating tolerances are involved.

## Stage 2: Initialize Live 3D Studio Inspector Artifact (Real-Time Stream)
- Before or during geometry generation, initialize `<artifact_dir>/live_cad_studio.html` with the target bounding box (`generate_viewer.py --init-blueprint X Y Z --out-html <artifact_dir>/live_cad_studio.html` or `cad_init_live_studio`) and register it as a `UserFacing: true` artifact.
- As the model is constructed, stream stage updates using `--live-viewer <artifact_dir>/live_cad_studio.html --stream-delay 0.35` (and let the `PostToolUse` hook automatically sync any `.stl`/`.obj` updates into `<artifact_dir>/live_model_data.js`).
- The viewer updates **only the 3D model geometry and HUD metrics** in real time while keeping the user's camera orientation (`yaw`, `pitch`, `zoom`, `pan`) and settings (`shader`, `Z-slicer`, `calipers`) 100% locked.

## Stage 3: Structural & DFM Strategy + Parametric Generation
- Choose the optimal print orientation so primary loads run along continuous XY perimeters.
- Generate both the binary `.stl` mesh and the editable parametric source (`.scad` and/or `.py`) using `cad_generate_parametric_part` or `cad_engine.py`.
- If the design is an assembly (e.g., an enclosure box + matching lid), generate **all mating parts** with calibrated clearances so they fit together immediately.

## Stage 4: Mandatory Automated Engineering Audit
- Run `cad_verify_mesh` (or `verify_model.py --target X Y Z`) on every generated `.stl` file.
- Confirm:
  - `is_watertight_manifold: true` (`0` open boundary edges, `0` non-manifold edges)
  - `within_tolerance: true` (exact bounding box matches target within `±0.05 mm`)
  - `structural_quality_score >= 85`

## Stage 5: Interactive 3D CAD Preview & Engineering Summary
- Ensure `<artifact_dir>/live_cad_studio.html` has been registered/updated with `ArtifactMetadata` (`UserFacing: true`) and embed it inline in your response:
  ```html
  <agent-embed src="file:///<artifact_dir>/live_cad_studio.html"></agent-embed>
  ```
- Present a concise **Parametric Specification & Verification Table** listing exact dimensions, clearances, wall thicknesses, filament weight estimate, and clickable `file://` links to the `.stl` and `.scad`/`.py` files.
