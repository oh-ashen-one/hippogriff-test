#!/bin/bash
# Render the 120-frame hippogriff clip from the saved .hip.
# Requires a full (non-Apprentice) Houdini license: Apprentice caps
# resolution at 1280x720 AND makes husk reject all UsdLux light prims
# ("Light type not supported" -> black frames), so on the test machine
# this pipeline could only be validated up to USD export.
#
# Usage (on the licensed machine):
#   1. Open hippogriff_flight.hip in Houdini 22 GUI (it must cook the
#      vellum sim 1..120 once), then either:
#      a. In /stage, export the flattened stage per frame to
#         render/scene.$F4.usd (usd_rop 'usdexport' is already wired), or
#      b. Run this script against pre-exported USDs.
#   2. ./render_clip.sh
set -e
HB=/Applications/Houdini/Houdini22.0.451/Frameworks/Houdini.framework/Versions/22.0/Resources
cd "$(dirname "$0")/.."
mkdir -p render/frames

# If scene USDs are missing, export them from the hip with hython:
# $HB/bin/hython -c "hou.hipFile.load('$PWD/hippogriff_flight.hip'); \
#   n=hou.node('/stage/usdexport'); n.render(frame_range=(1,120))"

for f in $(seq 1 120); do
  usd=$(printf "render/scene.%04d.usd" "$f")
  out=$(printf "render/frames/hippogriff.%04d.exr" "$f")
  [ -f "$out" ] && continue
  "$HB/bin/husk" --renderer Karma "$usd" -o "$out" --frame "$f"
done

ffmpeg -y -framerate 24 -i render/frames/hippogriff.%04d.exr \
  -vf "scale=1920:1080:flags=lanczos" -c:v libx264 -pix_fmt yuv420p -crf 16 \
  hippogriff_flight_1080p.mp4
echo "clip: hippogriff_flight_1080p.mp4 (120 frames @ 24fps)"
