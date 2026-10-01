/*
 * Automatic Putting-Cup Ball Return - rubber-band snap kicker
 * -----------------------------------------------------------
 * Arduino Nano/Uno + A4988 or DRV8825 + 17HS4401S NEMA17 stepper.
 *
 * Mechanism: the stepper turns a 12T pinion -> 42T gear (3.5:1). The 42T gear
 * carries a 16T sector gear with only 5 teeth. Each full turn of the sector
 * pulls the sled (rack) back ~33 mm against the rubber bands, then the last
 * tooth slips off and the bands snap the paddle forward into the ball.
 * One trigger = exactly one revolution of the sector.
 *
 * Inputs (all active LOW, internal pull-ups):
 *   BALL_PIN  - TCRT5000 IR module "DO" (LOW = ball seen), or a microswitch
 *               to GND, or an IR break-beam receiver (set BALL_ACTIVE_LOW).
 *   HOME_PIN  - KW11 microswitch on the guide rail, NO contact to GND.
 *               Pressed when the sled is fully forward (at rest).
 *   PAUSE_PIN - optional push button to GND: toggles auto-return on/off.
 *
 * Driver micro-stepping: 1/8 (A4988: MS1=MS2=HIGH, MS3=LOW;
 *                             DRV8825: M0=M1=HIGH, M2=LOW). Same wiring.
 */

// ============================ configuration ================================
const uint8_t STEP_PIN  = 4;
const uint8_t DIR_PIN   = 5;
const uint8_t EN_PIN    = 6;     // driver ENABLE (active LOW)
const uint8_t BALL_PIN  = 2;
const uint8_t HOME_PIN  = 3;
const uint8_t PAUSE_PIN = 8;
const uint8_t BUZZ_PIN  = 9;     // optional passive/active buzzer
const uint8_t LED_PIN   = 13;

#define USE_HOME_SWITCH   1      // 0 = no switch, count steps only
#define BALL_ACTIVE_LOW   1      // 1 for TCRT5000 / microswitch to GND
#define DIR_INVERT        0      // flip if the sled does not pull back
#define HOME_ON_BOOT      1      // fire one test shot at power-up to sync

const uint16_t MOTOR_STEPS   = 200;      // 1.8 deg motor
const uint8_t  MICROSTEPS    = 8;
const float    GEAR_RATIO    = 42.0 / 12.0;
const uint32_t STEPS_PER_REV = (uint32_t)(MOTOR_STEPS * MICROSTEPS * GEAR_RATIO + 0.5); // 5600

// After the snap, keep turning this far so the toothless arc is centred
// under the rack (release happens at ~266 deg of the 360 deg cycle).
const uint32_t PARK_STEPS    = STEPS_PER_REV * 94UL / 360UL;

const float    SPEED_START   = 800;      // micro-steps / s
const float    SPEED_MAX     = 4800;     // = 180 rpm at the motor, 51 rpm sector
const float    ACCEL         = 12000;    // micro-steps / s^2
const uint32_t JAM_STEPS     = STEPS_PER_REV * 13UL / 10UL;

const uint16_t BALL_SETTLE_MS = 450;     // ball must sit still this long
const uint16_t COOLDOWN_MS    = 700;     // after a kick, before re-checking
const uint8_t  MAX_RETRIES    = 3;       // ball still there? kick again
// ===========================================================================

enum State { IDLE, COOLDOWN, WAIT_CLEAR, FAULT };
State state = IDLE;
bool  paused = false;
uint8_t retries = 0;
uint32_t tMark = 0, ballSince = 0;

inline bool ballPresent() {
  bool lvl = digitalRead(BALL_PIN);
  return BALL_ACTIVE_LOW ? !lvl : lvl;
}
inline bool sledHome() { return digitalRead(HOME_PIN) == LOW; }

void beep(uint16_t ms) {
  digitalWrite(BUZZ_PIN, HIGH); delay(ms); digitalWrite(BUZZ_PIN, LOW);
}

void driver(bool on) { digitalWrite(EN_PIN, on ? LOW : HIGH); }

inline void pulse(uint32_t periodUs) {
  digitalWrite(STEP_PIN, HIGH);
  delayMicroseconds(3);
  digitalWrite(STEP_PIN, LOW);
  if (periodUs > 3) delayMicroseconds(periodUs - 3);
}

// Run one kick cycle. Returns true if a snap was detected (or step-counted).
bool kickCycle() {
  digitalWrite(DIR_PIN, DIR_INVERT ? LOW : HIGH);
  driver(true);
  delay(5);

  float speed = SPEED_START;
  uint32_t steps = 0, stopAt = USE_HOME_SWITCH ? JAM_STEPS : STEPS_PER_REV;
  uint16_t awayCount = 0;
  bool released = !USE_HOME_SWITCH, snapped = !USE_HOME_SWITCH;

  while (steps < stopAt) {
    uint32_t remaining = stopAt - steps;
    // decelerate into the park position (no load there, but be gentle)
    float vDec = sqrt(2.0 * ACCEL * remaining) + SPEED_START;
    float v = min(speed, vDec);
    uint32_t period = (uint32_t)(1000000.0 / v);
    pulse(period);
    steps++;
    if (speed < SPEED_MAX) speed = min(SPEED_MAX, speed + ACCEL * period / 1e6);

#if USE_HOME_SWITCH
    if (!released) {
      // sled has to leave the switch for a while = it is being cocked
      awayCount = sledHome() ? 0 : awayCount + 1;
      if (awayCount > 150) released = true;
    } else if (!snapped && sledHome()) {
      snapped = true;                       // bands fired the sled home
      stopAt = steps + PARK_STEPS;          // finish into the dwell zone
    }
#endif
  }
  driver(false);
  return snapped;
}

void fault(const char *why) {
  Serial.print(F("FAULT: ")); Serial.println(why);
  driver(false);
  state = FAULT;
  for (uint8_t i = 0; i < 3; i++) { beep(80); delay(120); }
}

void setup() {
  pinMode(STEP_PIN, OUTPUT); pinMode(DIR_PIN, OUTPUT); pinMode(EN_PIN, OUTPUT);
  pinMode(LED_PIN, OUTPUT);  pinMode(BUZZ_PIN, OUTPUT);
  pinMode(BALL_PIN, INPUT_PULLUP);
  pinMode(HOME_PIN, INPUT_PULLUP);
  pinMode(PAUSE_PIN, INPUT_PULLUP);
  driver(false);
  Serial.begin(115200);
  Serial.print(F("Ball return ready. steps/rev=")); Serial.println(STEPS_PER_REV);
  delay(500);
#if HOME_ON_BOOT
  if (!kickCycle()) fault("no snap during homing - check DIR_INVERT / jam / home switch");
#endif
  beep(40);
}

void loop() {
  uint32_t now = millis();

  // pause / resume button
  static bool lastBtn = HIGH;
  bool btn = digitalRead(PAUSE_PIN);
  if (lastBtn == HIGH && btn == LOW) {
    paused = !paused;
    beep(paused ? 200 : 40);
    if (state == FAULT) state = IDLE;   // button also clears a fault
    delay(30);
  }
  lastBtn = btn;
  digitalWrite(LED_PIN, paused || state == FAULT ? (now / 250) % 2 : ballPresent());

  bool ball = ballPresent();
  if (!ball) ballSince = now;

  switch (state) {
    case IDLE:
      if (!paused && ball && now - ballSince >= BALL_SETTLE_MS) {
        Serial.println(F("kick"));
        if (!kickCycle()) { fault("jam: sled never snapped"); break; }
        retries++;
        state = COOLDOWN; tMark = millis();
      } else if (!ball) retries = 0;
      break;

    case COOLDOWN:
      if (now - tMark >= COOLDOWN_MS) {
        if (ball && retries >= MAX_RETRIES) { fault("ball not leaving"); state = WAIT_CLEAR; }
        else state = IDLE;
        ballSince = now;      // demand a fresh settle period
      }
      break;

    case WAIT_CLEAR:          // ball stuck: wait until someone removes it
      if (!ball) { retries = 0; state = IDLE; }
      break;

    case FAULT:               // press the button (or power-cycle) to retry
      break;
  }
}
