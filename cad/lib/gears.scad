// ---------------------------------------------------------------------------
// Minimal involute spur gear + rack library (no external dependencies).
// All angles in degrees. Gears are drawn in the 2D XY plane, centred at the
// origin, with tooth 0 pointing along +X.
// ---------------------------------------------------------------------------

// polar angle (deg) of an involute of base radius rb at radius r
function _inv_ang(rb, r) = let(a = acos(min(1, rb / r))) (tan(a) - a * PI / 180) * 180 / PI;

function _polar(r, a) = [r * cos(a), r * sin(a)];

// half-thickness angle (deg) of a tooth flank at radius r
// x = profile shift coefficient (positive = fatter teeth, avoids undercut)
function _flank(m, z, pa, backlash, r, x = 0) =
    let(rp = m * z / 2, rb = rp * cos(pa),
        psi = 90 / z + (2 * x * tan(pa) / z) * 180 / PI - (backlash / 2) / rp * 180 / PI)
    psi + _inv_ang(rb, rp) - _inv_ang(rb, max(r, rb));

// One tooth outline (closed polygon) centred on +X.
// tip_cut shortens the addendum (mm) - used as entry relief on a sector gear.
module gear_tooth2d(m, z, pa = 20, backlash = 0.15, tip_cut = 0, steps = 10, x = 0) {
    rp = m * z / 2;
    rb = rp * cos(pa);
    ra = rp + m * (1 + x) - tip_cut;
    rf = rp - m * (1.25 - x);
    r0 = max(rb, rf);
    flank_r = [for (i = [0 : steps]) r0 + (ra - r0) * i / steps];
    a_tip = _flank(m, z, pa, backlash, ra, x);
    tip = [for (i = [0 : 4]) _polar(ra, -a_tip + 2 * a_tip * i / 4)];
    right = [for (r = flank_r) _polar(r, -_flank(m, z, pa, backlash, r, x))];
    left  = [for (i = [steps : -1 : 0]) let(r = flank_r[i]) _polar(r, _flank(m, z, pa, backlash, r, x))];
    a_root = _flank(m, z, pa, backlash, r0, x);
    polygon(concat(
        [_polar(rf - 0.6, -a_root)],
        right, tip, left,
        [_polar(rf - 0.6, a_root)]));
}

// Full or partial (mutilated / sector) spur gear.
//   teeth   : list of tooth indices to keep (undef = all)
//   gap_r   : radius of the toothless arc (defaults to the root radius)
//   relief  : list of tooth indices that get a shortened tip (entry relief)
module spur_gear2d(m, z, pa = 20, backlash = 0.15, teeth = undef, gap_r = undef,
                   relief = [], relief_cut = 0.5, x = 0) {
    rp = m * z / 2;
    rf = rp - m * (1.25 - x);
    keep = teeth == undef ? [for (i = [0 : z - 1]) i] : teeth;
    pitch_a = 360 / z;
    union() {
        circle(r = teeth == undef ? rf : (gap_r == undef ? rf : gap_r), $fn = 4 * z);
        // root disk only under the kept teeth for a sector gear
        if (teeth != undef) {
            a0 = min(keep) * pitch_a - pitch_a / 2;
            a1 = max(keep) * pitch_a + pitch_a / 2;
            intersection() {
                circle(r = rf, $fn = 4 * z);
                polygon(concat([[0, 0]],
                    [for (i = [0 : 16]) _polar(rf * 2, a0 + (a1 - a0) * i / 16)]));
            }
        }
        for (i = keep)
            rotate(i * pitch_a)
                gear_tooth2d(m, z, pa, backlash,
                             tip_cut = len(search(i, relief)) > 0 ? relief_cut : 0, x = x);
    }
}

// Straight rack. Pitch line on y = 0, teeth point toward -Y, tooth centres
// at x = x0 + k*p for k in [0 : n-1]. Body extends from root up to y = body_h.
module rack2d(m, n, x0 = 0, pa = 20, backlash = 0.15, body_h = 5, body_x = undef) {
    p = PI * m;
    w = (p / 2 - backlash) / 2;         // half tooth width on pitch line
    tw = w - m * tan(pa);                // half width at tip  (y = -m)
    rw = w + 1.25 * m * tan(pa);         // half width at root (y = +1.25m)
    bx = body_x == undef ? [x0 - p / 2, x0 + (n - 0.5) * p] : body_x;
    union() {
        translate([bx[0], 1.25 * m - 0.01]) square([bx[1] - bx[0], body_h - 1.25 * m + 0.01]);
        for (k = [0 : n - 1]) translate([x0 + k * p, 0])
            polygon([[-tw, -m], [tw, -m], [rw, 1.25 * m], [-rw, 1.25 * m]]);
    }
}
