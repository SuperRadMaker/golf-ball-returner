#!/usr/bin/env python3
"""
2D quasi-static simulation of the sector gear cocking the rack.

The rubber bands always pull the rack toward -X (forward); the front stop
holds it at d = 0. For each sector angle we find where the rack must sit so
it does not overlap the sector: pushed back by a tooth, following it, or
snapping home to the stop. Geometry is the same as cad/golf_returner.scad.
Outputs the stroke, the snap angle, the torque arm and a plot.
"""
import math
import numpy as np
from shapely.geometry import Polygon, Point
from shapely.affinity import rotate, translate
from shapely.ops import unary_union

M, Z, PA, BL = 1.5, 16, 20.0, 0.15
TEETH, GAP_R, RELIEF, RELIEF_CUT = [0, 1, 2, 3, 4], 9.5, [0], 0.45
AX = (115.0, 27.0)
RP = M * Z / 2
PITCH_Z = AX[1] + RP
RACK_P = math.pi * M
RACK_N = 10
RACK_SHIFT = 1.5        # rest phase of the rack: middle of the clean-entry window
RACK_X0 = AX[0] + RACK_P / 2 - (RACK_N - 1) * RACK_P + RACK_SHIFT
PARK_ROT = -(45 + 180 - 90)   # toothless arc centred on top


def inv_ang(rb, r):
    a = math.acos(min(1, rb / r))
    return math.degrees(math.tan(a) - a)


def flank(r):
    rb = RP * math.cos(math.radians(PA))
    psi = 90 / Z - math.degrees(BL / 2 / RP)
    return psi + inv_ang(rb, RP) - inv_ang(rb, max(r, rb))


def polar(r, a):
    return (r * math.cos(math.radians(a)), r * math.sin(math.radians(a)))


def tooth(tip_cut=0.0, steps=14):
    rb = RP * math.cos(math.radians(PA))
    ra, rf = RP + M - tip_cut, RP - 1.25 * M
    r0 = max(rb, rf)
    rs = [r0 + (ra - r0) * i / steps for i in range(steps + 1)]
    at = flank(ra)
    pts = [polar(rf - 0.6, -flank(r0))]
    pts += [polar(r, -flank(r)) for r in rs]
    pts += [polar(ra, -at + 2 * at * i / 4) for i in range(5)]
    pts += [polar(r, flank(r)) for r in reversed(rs)]
    pts += [polar(rf - 0.6, flank(r0))]
    return Polygon(pts)


def sector_shape():
    rf = RP - 1.25 * M
    pa = 360 / Z
    parts = [Point(0, 0).buffer(GAP_R, 128)]
    a0, a1 = min(TEETH) * pa - pa / 2, max(TEETH) * pa + pa / 2
    wedge = Polygon([(0, 0)] + [polar(2 * rf, a0 + (a1 - a0) * i / 32) for i in range(33)])
    parts.append(Point(0, 0).buffer(rf, 128).intersection(wedge))
    for i in TEETH:
        parts.append(rotate(tooth(RELIEF_CUT if i in RELIEF else 0), i * pa, origin=(0, 0)))
    return unary_union(parts)


def rack_shape():
    w = (RACK_P / 2 - BL) / 2
    tw, rw = w - M * math.tan(math.radians(PA)), w + 1.25 * M * math.tan(math.radians(PA))
    polys = [Polygon([(RACK_X0 - RACK_P / 2 - 30, PITCH_Z + 1.25 * M), (AX[0] + 40, PITCH_Z + 1.25 * M),
                      (AX[0] + 40, PITCH_Z + 4), (RACK_X0 - RACK_P / 2 - 30, PITCH_Z + 4)])]
    for k in range(RACK_N):
        x = RACK_X0 + k * RACK_P
        polys.append(Polygon([(x - tw, PITCH_Z - M), (x + tw, PITCH_Z - M),
                              (x + rw, PITCH_Z + 1.25 * M + 0.01), (x - rw, PITCH_Z + 1.25 * M + 0.01)]))
    return unary_union(polys)


def simulate(shift=RACK_SHIFT, da=0.25):
    global RACK_X0
    RACK_X0 = AX[0] + RACK_P / 2 - (RACK_N - 1) * RACK_P + shift
    sec0, rack0 = sector_shape(), rack_shape()
    tol = 1e-3
    d, out = 0.0, []
    angles = np.arange(0, 360.01, da)
    for a in angles:
        # cycle angle a -> CW rotation in the XZ plane ("top moves +X")
        sec = translate(rotate(sec0, PARK_ROT - a, origin=(0, 0)), *AX)
        hit = lambda dd: translate(rack0, dd, 0).intersection(sec).area > tol
        if hit(d):                          # tooth pushes the rack back
            while hit(d):                   # small steps: never hop a tooth
                d += 0.01
        else:                               # bands pull it forward
            step = 0.05
            while d > 0 and not hit(max(0.0, d - step)):
                d = max(0.0, d - step)
        out.append(d)
    return angles, np.array(out)


def main():
    angles, out = simulate()
    i_max = int(np.argmax(out))
    eng = angles[np.argmax(out > 0.01)]
    snap = angles[i_max + np.argmax(out[i_max:] < 0.5)]
    stroke = out.max()
    # effective torque arm = dd/dtheta (mm per rad)
    arm = np.gradient(out, np.radians(angles))
    print(f"engagement starts  : {eng:6.2f} deg")
    print(f"max stroke         : {stroke:6.2f} mm at {angles[i_max]:.2f} deg")
    print(f"snap (release)     : {snap:6.2f} deg")
    print(f"dwell (toothless)  : {360 - snap + eng:6.2f} deg of 360")
    print(f"torque arm, median : {np.median(arm[(out > 1) & (out < stroke - 1)]):.2f} mm (pitch radius {RP})")
    print(f"torque arm, max    : {arm[out > 0].max():.2f} mm")
    # phase window: sweep the rest position and flag tip-on-tip entries
    print("\nrest-phase tolerance (bumper thickness error):")
    for sh in np.arange(-2.0, 2.01, 0.5):
        a2, o2 = simulate(RACK_SHIFT + sh, 0.5)
        ok = np.diff(o2).max() < 0.25
        print(f"  {sh:+.1f} mm : stroke {o2.max():5.2f} mm  {'clean' if ok else 'TIP-ON-TIP lurch'}")
    # lookup table for the CAD assembly views
    tbl = ",\n    ".join(f"[{a:.0f}, {d:.3f}]" for a, d in zip(angles, out) if abs(a - round(a)) < 1e-9)
    with open(__file__.replace("docs/sector_sim.py", "cad/stroke_table.scad"), "w") as f:
        f.write("// generated by docs/sector_sim.py - sled travel (mm) vs sector angle (deg)\n")
        f.write(f"stroke_sim = {stroke:.2f};\nsnap_deg = {snap:.2f};\neng_deg_sim = {eng:.2f};\n")
        f.write("stroke_tbl = [\n    " + tbl + "];\n")
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 3.2))
        ax.plot(angles, out, lw=2)
        ax.axvline(eng, ls=":", c="g"); ax.axvline(snap, ls=":", c="r")
        ax.text(eng + 3, stroke * 0.85, "first tooth", color="g")
        ax.text(snap + 3, stroke * 0.85, "SNAP", color="r")
        ax.set_xlabel("sector angle from park position (deg)")
        ax.set_ylabel("sled pulled back (mm)")
        ax.set_xlim(0, 360); ax.grid(alpha=.3)
        fig.tight_layout()
        fig.savefig(__file__.replace("sector_sim.py", "../images/stroke_vs_angle.png"), dpi=130)
    except ImportError:
        pass


if __name__ == "__main__":
    main()
