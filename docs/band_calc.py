#!/usr/bin/env python3
"""
Rubber-band kicker sizing for the putting-cup ball return.

Model: each rubber band is looped over a frame pin and a sled pin (2 strands).
Rubber is treated as a neo-Hookean solid:  stress = G * (lam - 1/lam^2).
Defaults match a #32 office band (76 mm flat, 3.2 x 0.8 mm section), which
is what "50 mm circle relaxed / 75 mm flat" describes.

Calibrate G for YOUR bands: hang a known mass m from a single band looped over
a pencil, measure the loop length l (pencil to hook, i.e. half the loop).
Then  G = m*9.81 / (2*A*(lam - lam**-2))  with lam = (2*l + pi*d_pencil) / C0.
"""
import math

# ---- band ----------------------------------------------------------------
C0      = math.pi * 50.0          # relaxed circumference, mm (50 mm circle)
WIDTH   = 3.2                     # mm
THICK   = 0.8                     # mm
G       = 0.50                    # shear modulus, MPa (natural rubber 0.4-0.7)
A       = WIDTH * THICK           # mm^2 per strand

# ---- geometry (from golf_returner.scad) ------------------------------------
PIN_D        = 6.0
XBAR_PIN_X   = 134.0
FRAME_PINS   = {"front hole (x=26)": 26.0, "middle hole (x=34)": 34.0, "rear hole (x=42)": 42.0}
# stroke and lever arm come from the contact simulation (sector_sim.py)
GEAR_RATIO   = 42 / 12            # printed reduction
GEAR_EFF     = 0.85               # 2 PLA meshes + bushing
RAIL_FRIC_N  = 1.0                # guide friction during cocking (estimate)

# ---- ball / sled -----------------------------------------------------------
M_BALL  = 0.04593                 # kg
M_SLED  = 0.022                   # kg, sled + crossbar (PLA 30 % infill)
DECEL   = 0.55                    # m/s^2 rolling deceleration, ~stimp 10 green


def band_force(D):
    """Force (N) of one band looped between pins D mm apart (2 strands)."""
    lam = (2 * D + math.pi * PIN_D) / C0
    if lam <= 1.0:
        return 0.0
    return 2 * G * A * (lam - lam ** -2)


def energy(D0, stroke, n=400):
    """Energy (J) released by one band from D0+stroke back to D0."""
    dx = stroke / n
    return sum(band_force(D0 + (i + 0.5) * dx) * dx for i in range(n)) / 1000


def sim_curve():
    import numpy as np
    import sector_sim
    ang, d = sector_sim.simulate(da=0.5)
    arm = np.gradient(d, np.radians(ang))           # mm of sled travel per rad
    arm[d <= 0] = 0
    return d, arm


def main():
    import numpy as np
    d_curve, arm = sim_curve()
    STROKE = float(d_curve.max())
    print(f"simulated stroke {STROKE:.1f} mm, lever arm median "
          f"{np.median(arm[d_curve > 1]):.1f} mm, max {arm.max():.1f} mm")
    print(f"band: C0={C0:.0f} mm, section {WIDTH}x{THICK} mm, G={G} MPa\n")
    print(f"{'preload hole':20s} {'bands':>5s} {'F rest':>7s} {'F cocked':>8s} "
          f"{'energy':>7s} {'T sector':>9s} {'T motor':>8s} {'ball v':>7s} {'roll':>6s}")
    for name, x in FRAME_PINS.items():
        D0 = XBAR_PIN_X - x
        for nb in (2, 4, 6):
            f0 = nb * band_force(D0)
            f1 = nb * band_force(D0 + STROKE)
            e = nb * energy(D0, STROKE)
            # torque along the cycle = band force at that travel x lever arm
            f_d = np.array([nb * band_force(D0 + x) + RAIL_FRIC_N for x in d_curve])
            t_sec = float((f_d * arm).max()) / 1000             # N*m, peak
            t_mot = t_sec / GEAR_RATIO / GEAR_EFF
            # push-off: sled + ball accelerate together, sled is stopped,
            # ball leaves sliding then settles to rolling at 5/7 speed.
            v_launch = math.sqrt(2 * e * 0.85 / (M_BALL + M_SLED))  # 15 % rail/band losses
            v_roll = 5 / 7 * v_launch
            dist = v_roll ** 2 / (2 * DECEL)
            print(f"{name:20s} {nb:5d} {f0:6.1f}N {f1:7.1f}N {e*1000:5.0f}mJ "
                  f"{t_sec*100:6.1f}Ncm {t_mot*100:5.1f}Ncm {v_roll:5.2f}m/s {dist:5.1f}m")
        print()
    print("Motor reference torques (N*cm):")
    print("  SG90 9g servo, datasheet stall 1.8 kg*cm  = 17.6  (real ~12-15)")
    print("  FS90R continuous 9g servo, stall ~1.5 kg*cm = 14.7")
    print("  17HS4401S holding torque @1.7 A            = 40   (~20 usable @1 A, 200 rpm)")


if __name__ == "__main__":
    main()
