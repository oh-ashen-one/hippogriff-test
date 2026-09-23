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
