#!/usr/bin/env bash
# Export every printable part to ../stl and preview images to ../images.
# Needs OpenSCAD (2021.01+). On a headless Linux box, xvfb-run is used for PNGs.
set -euo pipefail
cd "$(dirname "$0")"
SCAD=golf_returner.scad
PARTS="base ramp sled crossbar guide sector pinion spacer lid"
mkdir -p ../stl ../images
for p in ${1:-$PARTS}; do
  echo ">> $p"
  openscad -q -D "part=\"$p\"" -o "../stl/$p.stl" "$SCAD"
done
[ "${1:-}" != "" ] && exit 0
# one-file download of every part + print guide
rm -f ../golf_ball_return_stl.zip
zip -q -j -9 ../golf_ball_return_stl.zip ../stl/*.stl ../docs/PRINT_GUIDE.txt
RUN=""; command -v xvfb-run >/dev/null && [ -z "${DISPLAY:-}" ] && RUN="xvfb-run -a"
# png NAME WIDTHxHEIGHT openscad-args...
png() { $RUN openscad -q --imgsize="${2/x/,}" --colorscheme=Tomorrow --view=axes -o "../images/$1.png" "${@:3}" "$SCAD"; }
png assembly_ready   1600x1100 -D 'part="assembly"' -D 'cycle_deg=0'   --camera=-10,15,10,55,0,325,600
png assembly_cocked  1600x1100 -D 'part="assembly"' -D 'cycle_deg=262' --camera=-10,15,10,55,0,325,600
png profile          1800x700  -D 'part="section"'  -D 'cycle_deg=0'   --camera=17,0,25,90,0,0,420 --projection=ortho
png section_ready    1600x1100 -D 'part="section"'  -D 'cycle_deg=0'   --camera=90,0,30,90,0,0,330 --projection=ortho
png section_engaged  1600x1100 -D 'part="section"'  -D 'cycle_deg=180' --camera=90,0,30,90,0,0,330 --projection=ortho
png section_cocked   1600x1100 -D 'part="section"'  -D 'cycle_deg=262' --camera=90,0,30,90,0,0,330 --projection=ortho
png top_view         1800x900  -D 'part="assembly"' -D 'cycle_deg=0'   --camera=7,23,0,0,0,0,560 --projection=ortho
png gear_detail      1600x1100 -D 'part="section"'  -D 'cycle_deg=180' --camera=118,0,32,90,0,0,110 --projection=ortho
