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

# The Houdini "clip" above is a desktop screen recording in which the Houdini
# viewport is EMPTY for its entire 8 s - the only creature on screen is the Blender
# render playing in QuickTime, and the clip ends on black. So the hero stills are
# the whole of the Houdini visual output. This pane is what to compare with.
H="$ROOT/houdini"
ffmpeg -y -v error -i "$H/hero_1.png" -i "$H/hero_2.png" -i "$H/hero_3.png" \
  -f lavfi -i color=c=0x14171c:s=1920x1080 \
  -filter_complex "[0:v]scale=1920:1080[a];[1:v]scale=1920:1080[b];[2:v]scale=1920:1080[c];[3:v]scale=1920:1080[d];[a][b][c][d]xstack=inputs=4:layout=0_0|1920_0|0_1080|1920_1080[g];[g]drawtext=fontfile='$FONT':text='3 | HOUDINI - stills only - NO ANIMATION (Apprentice render, watermarked)':fontcolor=white:fontsize=56:box=1:boxcolor=black@0.80:boxborderw=22:x=44:y=44[out]" \
  -map "[out]" -frames:v 1 "$OUT/3_houdini_stills_only.png"
echo "wrote $OUT/3_houdini_stills_only.png"
