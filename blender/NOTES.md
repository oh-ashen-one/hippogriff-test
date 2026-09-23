# Hippogriff Flight Test — Blender contender NOTES

## Deliverables
- `hippogriff_flight.mp4` — 5 s clip, 120 frames @ 24 fps, 1920x1080, EEVEE render (not viewport)
- `hero_1.png`, `hero_2.png`, `hero_3.png` — hero stills, 1920x1080 rendered frames
- `hippogriff_flight.blend` — full editable project (rigged, animated, lit)
- `build_rig.py`, `fkcore.py`, `animate.py`, `rebake.py`, `build_env.py` — all code written for the task
- `frames/` — full PNG sequence the clip was encoded from

## What I did
- **Rig (by hand, no auto-rig services)**: analysed the mesh numerically (vertex-slice
  distributions + k-means clusters) to recover the anatomy from the folded pose — body axis
  Y, head at −Y, bat-style wings half-raised. Built a 30-bone armature in `build_rig.py`:
  spine/neck/head chain, 3-bone tail, per wing: upper arm, forearm, 3 finger bones through
  the membrane, plus tucked fore/hind legs with toes.
- **Skinning**: procedural closest-segment weights (numpy, 2-bone inverse-cubic blend with
  anatomical eligibility masks so wing bones only claim their side, tail/head/legs don't
  cross-claim). No manual paint time was affordable at 90 min.
- **Animation (`fkcore.py`, `animate.py`, `rebake.py`)**: my own FK solver baked per-frame
  into pose-bone keyframes via `matrix_basis` (fast, no per-bone depsgraph eval).
  - Wingbeat: 30-frame cycle, 13f power downstroke / 17f upstroke (asymmetric), elbow and
    wingtip phase-lagged, upstroke fold + sweep, finger fan spread on downstroke.
  - Body mass: root bob peaking just after downstroke end, counter-pitch oscillation,
    sagging during upstroke.
  - Choreography: cruise → dive with 28-30° bank and swept/tucked wings (f48-88) →
    pull-up recovery with boosted flap amplitude and neck counter-pitch (f88-110).
  - Camera: baked per-frame with 6-frame lag, slow orbit from front-left to rear-left,
    1-2-1 smoothing plus small handheld noise; TrackTo target leads the creature.
- **Gravity/momentum readability**: downstroke/upstroke timing asymmetry, body bob lagging
  the wingbeat, dive-and-recover with bank, wing sweep-back in the dive, motion-blurred
  downstroke tips (EEVEE motion blur, shutter 0.25).
- **Simulated secondary motion**: cloth-simulated tail streamer pinned at the tail tip,
  driven by gravity + a Wind force field (relative airflow), bone-parented to the tail.
- **Environment (all built, no downloads)**: Nishita-style sky (multiple-scattering sky
  texture, low sun), matched Sun lamp + cool traveling area fill, two procedural-noise
  cloud decks (below and cirrus above), AgX medium-high contrast.

## What broke
- **Blender 5.2 mathutils: `Quaternion * Quaternion` no longer composes rotations**
  (it zeroes the vector part — behaves like a component/dot operation). The whole first
  animation bake silently wrote identity quaternions for every bone whose pose multiplied
  two quats. Fix: compose with `@` (Hamilton product verified numerically).
- **pb.matrix setter stalls**: setting `pose_bone.matrix` on 30 bones re-evaluates the
  depsgraph per bone on a 61k-vert mesh — the first bake attempt hard-stalled Blender and I
  had to kill and relaunch my instance (saved file lost nothing). Fix: compute
  `matrix_basis` and set plain `location`/`rotation_quaternion` properties instead.
- **Double rig**: the stalled script actually completed server-side twice, leaving two
  armatures and 60 vertex groups; cleaned by hand (deleted orphan rig + `.001` groups).
- **Missing bone parents**: the armature was built as 30 root bones while the baked
  `matrix_basis` values assumed Blender's parented composition — evaluation rotated each
  bone around its rest joint but never propagated transforms down the chain (visible as
  wings that "refused to flap" despite correct fcurve data). Setting the real bone parents
  made the already-baked action evaluate correctly.
- **Folded-pose weight trap**: procedural nearest-segment weights bound the folded wing
  membrane (which lies against the neck/back in rest pose) to the head/neck/spine bones.
  Re-weighted in `reweight.py` with a wing-region rule (|x|>0.9 m, or high membrane
  z>1.85 m) that only same-side wing bones may claim.
- **Transform trap**: clearing the GLB root parent reset the mesh to 0.96 m; re-scaled to
  2.5 m after rigging (armature + mesh together).
- Cloth strips on mane and wing trailing edges rendered as white paper cards (no UVs,
  stiff) — cut them, kept the one that read well (tail streamer).

## With more time
- Geodesic/auto-weight cleanup pass around wing shoulders and leg roots (some membrane
  verts near the body follow the chest and softly crumple on hard downstrokes).
- Real feather cards with cloth on wing trailing edges, and a volume cloud layer with
  light shafts (cut for render budget).
- A second camera cut for the dive; the single-shot orbit is a compromise.
- Groom: the brief's thestral reads fine with its sculpted texture, but a mane/tail hair
  particle system would sell close-ups.
