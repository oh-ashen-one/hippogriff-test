#!/bin/sh
# Build labelled review copies of the contender clips.
#
# The captions are burned into the pixels rather than relying on window titles, so
# each clip stays self-identifying when screen-recorded or shown side by side. This
# matters because the Houdini clip is a viewport screen capture, not a render, and
# the two are otherwise easy to confuse.
#
# Usage: sh make_labeled_reviews.sh <repo-root> <out-dir>
set -e

ROOT="${1:-.}"
OUT="${2:-./labeled}"
FONT="/System/Library/Fonts/Supplemental/Arial Bold.ttf"
[ -f "$FONT" ] || FONT="/System/Library/Fonts/Supplemental/Arial.ttf"
mkdir -p "$OUT"

label() {  # $1 in  $2 out  $3 text  $4 fontsize
  ffmpeg -y -v error -i "$1" \
    -vf "drawtext=fontfile='$FONT':text='$3':fontcolor=white:fontsize=$4:box=1:boxcolor=black@0.72:boxborderw=16:x=32:y=32" \
    -an -c:v libx264 -crf 16 -preset medium -pix_fmt yuv420p "$2"
  echo "wrote $2"
}

label "$ROOT/blender/hippogriff_flight.mp4"      "$OUT/1_blender_full_flight.mp4" \
      "1 | BLENDER - full flight - 1080p render - 120 frames" 40
label "$ROOT/blender/hippogriff_flight_solo.mp4" "$OUT/2_blender_solo.mp4" \
      "2 | BLENDER - solo pass - 1080p render - 67 frames" 40
label "$ROOT/houdini/flight_screenrec.mov"       "$OUT/3_houdini_viewport.mp4" \
      "3 | HOUDINI - viewport screenrec - NOT a render" 48
