#!/bin/sh
# Assemble every version of the hippogriff work into one folder that can be served on
# localhost, so all the clips, stills and the GLB sit in one place with labels.
#
# Usage: sh make_localhost_gallery.sh <repo-root> <out-dir>
#   then:  python3 -m http.server 8765 --directory <out-dir>
#   and open http://127.0.0.1:8765/
#
# Note on branches: the Blender clips/stills and the recoloured GLB live on
# blender-contender; the Houdini clip, the screenrec and the Houdini stills live on
# houdini-contender. Check both out into one tree first, or copy the missing files in.
set -e

ROOT="${1:-.}"
OUT="${2:-./localhost}"
A="$OUT/all"
mkdir -p "$A"

# ---- videos ----
cp "$ROOT/blender/hippogriff_flight.mp4"       "$A/1_blender_full_flight.mp4"
cp "$ROOT/blender/hippogriff_flight_solo.mp4"  "$A/2_blender_solo.mp4"
cp "$ROOT/houdini/render_out/3_houdini_animation.mp4" "$A/3_houdini_animation.mp4"
# the Houdini capture is a .mov desktop recording; remux so browsers play it inline
ffmpeg -y -v error -i "$ROOT/houdini/flight_screenrec.mov" -c copy \
       "$A/4_houdini_viewport_screenrec.mp4"

# ---- stills ----
i=1
while [ $i -le 3 ]; do
  cp "$ROOT/blender/hero_$i.png" "$A/blender_hero_$i.png"
  cp "$ROOT/houdini/hero_$i.png" "$A/houdini_hero_$i.png"
  i=$((i + 1))
done
cp "$ROOT/houdini/render_out/3_houdini_stills_only.png" "$A/houdini_stills_sheet.png" 2>/dev/null || true

# ---- captioned variants (build them if the labelled folder is absent) ----
if [ -d "$ROOT/labeled" ]; then
  for f in 1_blender_full_flight 2_blender_solo 3_houdini_animation 3_houdini_viewport; do
    src="$ROOT/labeled/$f.mp4"
    [ -f "$src" ] && cp "$src" "$A/cap_$f.mp4"
  done
else
  echo "note: no labelled/ folder - captioned variants skipped"
  echo "      run blender/make_labeled_reviews.sh to generate them"
fi

# ---- pages + asset ----
cp "$ROOT/index.html"   "$OUT/index.html"
cp "$ROOT/compare.html" "$OUT/compare.html"
cp "$ROOT/viewer.html"  "$OUT/viewer.html" 2>/dev/null || true
cp "$ROOT/hippogriff_recolored_animated.glb" "$OUT/hippogriff_animated.glb" 2>/dev/null || true
cp "$ROOT/hippogriff_basecolor_4096.png"     "$OUT/hippogriff_basecolor_4096.png" 2>/dev/null || true

echo "gallery assembled in $OUT"
echo "serve with: python3 -m http.server 8765 --directory $OUT"
