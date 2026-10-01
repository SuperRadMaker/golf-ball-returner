#!/usr/bin/env bash
# Interference check: intersects every relevant part pair at several points
# of the kick cycle. Overlaps under 0.5 mm^3 are surface contacts (parts that
# sit on each other) and are reported separately.
cd "$(dirname "$0")"
PAIRS="sled:base sled:guide sled:sector sled:lid sled:pinion sled:motor sled:spacer
crossbar:base crossbar:guide crossbar:lid crossbar:motor sector:base sector:guide
sector:pinion sector:motor pinion:base pinion:guide spacer:base motor:base guide:base
lid:guide lid:sector ball:base ball:sled ball:guide ball:ramp ramp:base"
ANGLES=${ANGLES:-0 60 110 150 200 240 262 300}
one() {
  a=$1; A=${2%%:*}; B=${2##*:}; f=$(mktemp --suffix=.stl)
  out=$(openscad -D 'part="isect"' -D "A=\"$A\"" -D "B=\"$B\"" -D "cycle_deg=$a" -o "$f" golf_returner.scad 2>&1)
  if ! echo "$out" | grep -q "top level object is empty"; then
    vol=$(python3 -c "import trimesh;print(round(abs(trimesh.load('$f').volume),3))" 2>/dev/null)
    if python3 -c "import sys; sys.exit(0 if float('${vol:-99}') < 0.5 else 1)"; then
      echo "contact a=$a $A x $B (${vol} mm3)"
    else echo "CLASH   a=$a $A x $B (${vol} mm3)"; fi
  fi
  rm -f "$f"
}
export -f one
for a in $ANGLES; do for p in $PAIRS; do echo "$a $p"; done; done |
  xargs -P "$(nproc)" -n 2 bash -c 'one "$0" "$1"' | sort
echo "check done"
