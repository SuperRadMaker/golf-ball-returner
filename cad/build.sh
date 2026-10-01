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
RUN=""; command -v xvfb-run >/dev/null && [ -z "${DISPLAY:-}" ] && RUN="xvfb-run -a"
png() { $RUN openscad -q --imgsize=1600,1100 --colorscheme=Tomorrow --view=axes -o "../images/$1.png" "${@:2}" "$SCAD"; }
png assembly_ready   -D 'part="assembly"' -D 'cycle_deg=0'   --camera=15,15,10,55,0,325,560
png assembly_cocked  -D 'part="assembly"' -D 'cycle_deg=262' --camera=15,15,10,55,0,325,560
png section_ready    -D 'part="section"'  -D 'cycle_deg=0'   --camera=90,0,30,90,0,0,330 --projection=ortho
png section_engaged  -D 'part="section"'  -D 'cycle_deg=180' --camera=90,0,30,90,0,0,330 --projection=ortho
png section_cocked   -D 'part="section"'  -D 'cycle_deg=262' --camera=90,0,30,90,0,0,330 --projection=ortho
png top_view         -D 'part="assembly"' -D 'cycle_deg=0'   --camera=7,23,0,0,0,0,560 --projection=ortho --imgsize=1800,900
png gear_detail      -D 'part="section"'  -D 'cycle_deg=180' --camera=118,0,32,90,0,0,110 --projection=ortho
