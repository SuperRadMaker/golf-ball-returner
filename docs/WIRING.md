# Wiring

```
 12 V adapter ── DC jack ── rocker switch ──┬──────────────► A4988 VMOT
                                            │   100 µF across VMOT / GND
                                            └──────────────► Nano VIN
 all grounds tied together: adapter −, A4988 GND (both), Nano GND, sensors

   Arduino Nano                      A4988 / DRV8825
   ───────────                       ───────────────
   5V  ────────────────────────────► VDD, MS1, MS2      (MS3 → GND)
   D4  ────────────────────────────► STEP               (RESET ↔ SLEEP jumper)
   D5  ────────────────────────────► DIR
   D6  ────────────────────────────► EN                 1A 1B 2A 2B ─► motor
   D2  ◄──── TCRT5000 DO       (module VCC → 5V, GND → GND)
   D3  ◄──── KW11 switch NO    (COM → GND)   pressed = sled home
   D8  ◄──── pause button      (other leg → GND)
   D9  ────► active buzzer +   (− → GND)
```

## Stepper coils

Usongshine 17HS4401S leads are usually black/green for one coil and red/blue
for the other. Confirm the pairs with a multimeter: about 1.5 Ω within a
coil, open circuit between coils.

| Motor lead | A4988 / DRV8825 pin |
|---|---|
| Black | 2B |
| Green | 2A |
| Red | 1A |
| Blue | 1B |

If the sector turns the wrong way, set `DIR_INVERT 1` in the firmware or swap
one coil's two leads. A wrong direction drives the sector into the rack and
the firmware reports a jam within 1.3 revolutions.

## Driver current

Set it with the motor unplugged and the 12 V supply on. Measure between the
trimmer and GND.

| Driver | Formula | Vref for 0.9 A |
|---|---|---|
| A4988, R100 sense resistors | Vref = I × 8 × 0.1 | 0.72 V |
| A4988, R050 sense resistors | Vref = I × 8 × 0.05 | 0.36 V |
| DRV8825 | Vref = I / 2 | 0.45 V |

The driver is disabled between kicks, so it stays cool. The toothless dwell
means nothing can back-drive the gear while it's off.

## Micro-stepping

Both drivers use 1/8 stepping with the first two mode pins HIGH and the third
LOW. On the A4988 those are MS1, MS2, MS3. On the DRV8825 they are M0, M1, M2.
The firmware assumes 200 × 8 × 3.5 = 5,600 micro-steps per sector revolution.

## Power budget

| Load | Current |
|---|---|
| Stepper while cocking, about 1.2 s per kick | about 0.9 A per coil |
| Nano + TCRT5000 + switch, idle | about 40 mA |

The Nano's onboard regulator handles 12 V on VIN at this current. A 12 V
battery pack, such as 8 × AA or a 3S Li-ion pack, also works for outdoor use.
