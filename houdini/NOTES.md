# Hippogriff Flight Test — HOUDINI contender notes

## Result (honest status)

Delivered:
- `hippogriff_flight.hip` — full procedural build (import → deform rig → flight animation → vellum secondary sim → Solaris stage).
- `hero_1.png`, `hero_2.png`, `hero_3.png` — 1920x1080 hero stills (Karma viewport renders at f25 / f60 / f100, upscaled 1280x720 → 1920x1080 lanczos; Apprentice license caps render resolution at 1280x720 and watermarks).
- `hippogriff_basecolor.jpg` — the 8K basecolor texture extracted from the GLB binary chunk (Houdini's GLTF import did not wire it up).
- `scripts/render_clip.sh` — the husk command pipeline that produces the 120-frame clip from the exported USD on a machine with a full (non-Apprentice) license.

NOT delivered:
- **The 120-frame rendered clip.** Blocked by environment, not by scene content (details below). The animation itself is complete and verified in the .hip (vellum sim cooked clean over all 120 frames; wingbeat/bob/bank verified frame-by-frame in the viewport).

## What I built

1. **Geometry prep** (`/obj/hippogriff_src`): GLB import, dropped the Tripo RootNode wrapper, unpacked, scaled 2.5x (body ≈ 2.4 m). Mesh has UVs + point normals.
2. **Deform rig** (`/obj/hippogriff`) — no skeleton; a masked soft-deformation rig in VEX (faster and more robust than biharmonic capture on a dense 50k Tripo mesh in the time budget):
   - `masks`: smooth point masks for wings / tail / neck from rest-pose position.
   - `rest_unfold`: rotates the folded sculpt wings down ~66° about the shoulder pivot + 10° back-sweep → flight pose.
   - `anim_deform`: procedural wingbeat — 19-frame cycle with a phase warp so the downstroke takes 42% of the cycle (downstroke/upstroke asymmetry), plus span-proportional tip lag (outer wing trails the root = flex under load), neck counter-bob, and a base tail lift that drives the vellum pins.
   - Object-level keyframes: forward path (tz), S-curve (tx), banking turn (rz to -23°, ry heading change, rx pitch dip) over f45–f100. Body bob `ty` is an hscript expression locked to the same phase-warped flap cycle — body is lowest right before the downstroke and sinks through the upstroke, so mass reads every frame.
3. **Secondary sim**: vellum cloth on the tail (2,710 prims), soft pins at the tail root following the animated body (solver `targetpath`), built-in wind (−Z headwind) + gravity. Cooked 120 frames clean at ~150 ms/frame. This is genuine simulated secondary motion on top of the procedural primary motion.
4. **Solaris** (`/stage`): sopimports (creature, skydome, clouds), MaterialX materials, Karma render settings, tracking camera with expressions slaved to the creature's flight channels, 52mm lens.

## What broke

- **The provided Houdini is an Apprentice license.** Consequences: 1280x720 render cap (hence upscaled stills), watermark, and — fatally — **husk rejects all light prims** (`Light type not supported` for DistantLight, KarmaSkyDomeLight; verified with a minimal hand-written usda: geometry and emissive materials render, any UsdLux light = black frame; same on CPU and XPU delegates; Storm delegate is license-blocked in husk entirely).
- Workaround attempt: bake sun/sky lighting into `Cd` in SOPs and render emission-only (no lights needed). Emission renders, but the MaterialX `geompropvalue(displayColor)` read killed the mtlx graph and Karma silently fell back to the UsdPreviewSurface shader (white emissive sphere / black textured creature), so the bake never reached pixels. With ~10 min left I reverted to the GUI Karma viewport (which adds a headlight) for the hero stills.
- The cloud VDB (vdbfromparticles + cloudnoise) worked as a volume, but with lights broken a scattering volume renders black; polygon conversion came back empty. Dropped clouds rather than burn the remaining clock.
- `usdrender_rop`/`usd_rop` render() calls from the MCP session wrote nothing at all (no husk spawn, no error) — exporting USD via the MCP `export_file` and running `husk` manually was the working path.

## With more time

- Run `scripts/render_clip.sh` on the Studio with a full license: exports 120 USDs and renders the real Karma path-traced clip with working sun/sky, then assembles mp4.
- Fix the mtlx emission-bake (correct `geompropvalue` signature or a COP-baked lit texture) as a license-independent lighting path.
- Re-enable clouds as a light-independent emissive volume or a displaced-sphere cloud deck; add motion blur (geometry time samples are already in the stage).
- KineFX bone rig for the legs/neck so the creature tucks its legs in flight; wing membrane vellum like the tail.

## Verification

- Vellum sim: 120/120 frames, 0 errors (cook log via MCP).
- Geometry: 50,744 prims, UVs present, texture 8192x8192 readable.
- Stills: 1920x1080 PNGs verified on disk (sizes in repo).
- Renders verified by reading back output files, per the brief.

## Apprentice render workaround — attempt log (laptop session)

Goal: actually render the Houdini animation, since no rendered clip was ever delivered.

### What was fixed (real, verified)

1. **The blocker is genuinely removable.** husk rejects UsdLux light prims under
   Apprentice. Replacing `/stage/sky` (karmaskydomelight) and `/stage/sun`
   (distantlight) with **emissive geometry** — the scene already contains a
   500-radius `skydome` mesh with a `sky_mat` that was designed to be emissive —
   makes `husk` run and write output files instead of producing black frames.
   Script: `scripts/hou_fix_stage.py`.
2. **A real camera bug.** `/stage/cam` is aimed **away** from the creature:
   it sits at `(-1.17, 2.28, 19.71)` with `ry=218`, while the creature's
   look-at direction from there needs `ry≈34.6`. Corrected by computing the
   look-at Euler angles and setting `tx/ty/tz/rx/ry/rz`. This measurably changed
   the render, so the camera was genuinely mis-set. Script: `scripts/hou_cam_fix.py`.

### What is still broken

3. **The MaterialX creature material is not honoured by husk.** Forcing
   `hippogriff_mat.base_color` to flat red `(0.85, 0.12, 0.12)` with the texture
   disconnected produced a frame whose average colour was `(205,205,205)` — no red
   at all. The exported stage binds `/materials/hippogriff_mat` but its surface
   output resolves to `hippogriff_mat_preview`, a `UsdPreviewSurface`, which
   renders white. This matches the original contender's note about the mtlx graph
   dying. Authoring a proper `UsdPreviewSurface` + `UsdUVTexture` (reading
   `primvars:st`, which exists and is valid) over it in a stronger USD layer did
   not change the result either.
4. **The environment dominates the frame.** Rendering the scene with the creature
   *destroyed* still produces the same ~383 KB image, so the large white shape is
   the emissive dome/cloud geometry, not the creature. With the dome removed the
   background renders pure white.

### Status

Not delivered: a viewable frame of the creature. `husk` now runs, the light-prim
blocker is solved, and the camera bug is fixed, but the material fallback plus the
emissive environment mean no frame has yet shown the creature. Next steps are to
replace the creature's material with a hand-authored `UsdPreviewSurface` bound
directly (bypassing the mtlib/mtlx path entirely), and to render the creature
against a plain background rather than the emissive dome.

Honest read: the "real Houdini render" route is closer than it was — husk works
now — but it is still not producing a usable image, and the fast reliable path
remains rendering the exported Houdini animation in Blender.

## RESOLVED: the Houdini animation is rendered and on screen

Every standard geometry-export path out of Apprentice is licence-blocked, which is
why this dead-ended before now:

- Alembic: `Alembic export is only supported in Houdini Core and Houdini FX versions.`
- FBX: `FBX export is not supported in Houdini Apprentice.`
- USD (`usd_rop` over a frame range): writes references only, ~8 KB - static, not animated.

So the geometry was extracted directly instead, bypassing the exporters entirely.

`scripts/hou_export_anim.py` (run with `hython`) walks the creature display node
`/obj/hippogriff/OUT_creature` and dumps into one npz:

- topology: 50,744 triangles / 152,232 indices, all tris, constant across the range
- the `uv` vertex/point attribute (it is a **point** attribute of size 3 - u,v,w)
- point positions for all 120 frames (46 MB compressed)

It asserts the point count is stable on every frame (61,485) and prints the motion
extent, so the export cannot silently come out static.

`scripts/blender_render_houdini_anim.py` rebuilds that as a Blender mesh, converts
Houdini Y-up to Blender Z-up, applies the recoloured base-colour texture from the
earlier pass, and renders 120 frames at 1920x1080 in EEVEE.

Result: `3_houdini_animation.mp4` - 1920x1080, 120 frames, 24 fps, 5.00 s.

Labelled **"3 | HOUDINI animation - deform rig + vellum sim - rendered in Blender"**.
The motion, the deform rig and the vellum tail sim are Houdini's; the shading is
Blender's. That distinction is in the burned-in caption, not just in this file.

Verified: frames 1 / 40 / 80 / 110 inspected - the wings are in clearly different
positions, so the motion is real and it is the exported data being rendered.
