# Hippogriff Flight Test — identical brief for both contenders

## Input
- Model: `/Users/midir/hippogriff-test/hippogriff.glb`
  (Tripo-generated thestral-style hippogriff: single mesh, 50,744 polygons, 1 material, 1 texture, NO rig)
- The mesh is ~1 unit tall as shipped. Scale it to something physically sensible (a large flying creature, ~2.5 m body) before animating.

## Goal
Make this hippogriff look as realistic and high-quality as you can while it is flying through the sky. Gravity must be physically readable in every frame.

## Required deliverables (in your workdir, committed to git)
1. A 5-second clip: 120 frames @ 24 fps, 1920x1080, one continuous cinematic shot of the hippogriff in flight. Rendered — not a viewport capture.
2. Three hero stills (1920x1080, rendered).
3. Your editable project file (.blend or .hip) plus any scripts you wrote.
4. `NOTES.md` — what you did, what broke, what you would do with more time.

## Gravity must be visible
- A full wingbeat cycle with wing flex under load (downstroke/upstroke asymmetry)
- Body bob and sag between wingbeats — the creature has mass
- One banking turn or dive-and-recover where momentum and weight read clearly
- Secondary motion: feathers, skin, or wing membrane reacting to air and gravity — simulated where your app supports it, not only keyframed

## Rules
- 90 minutes of wall-clock work, hard stop, then finalize and commit deliverables.
- No external asset packs, downloaded meshes, textures, or HDRIs. Build sky, clouds, lighting, and groom yourself. Sole exception: the provided GLB.
- Rig it yourself. No auto-rig web services.
- All compute and renders on the Studio.
- Verify deliverables exist on disk (sizes, frame counts, readable files) before declaring done.
- Commit AND push to the git repo when done.
