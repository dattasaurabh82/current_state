#!/usr/bin/env python3
"""
RD-03D Diagnostic Tool — See what the radar ACTUALLY reports.

Shows ALL fields from OutputDump so you can see what's noise vs real motion.
Uses settings from settings.json (same config as the main player).

HOW TO RUN:
    cd ~/current_state/tests
    uv run 04_test_radar_diagnostics.py

WHAT IT SHOWS:
    Every 100ms it prints one line with ALL radar fields:
    - mode     : What the radar thinks it sees (key field we're not using yet!)
    - dist     : Kalman-filtered distance
    - raw_dist : Raw unfiltered distance
    - x, y     : Cartesian coordinates
    - angle    : Target angle
    - verdict  : Whether our current logic would count this as "valid movement"

    After you Ctrl+C it prints a summary:
    - How many readings were "valid" vs total
    - Distance distribution (min/max/avg of valid readings)
    - Mode value distribution (this tells us what filter to add)

TEST PROCEDURE:
    1. Run with EMPTY ROOM — nobody in front of radar. Wait 30-60s.
       → If you see lots of "valid" readings, that's the false trigger source.
       → Check what mode values appear.
    2. Run and WALK IN FRONT — see the difference in mode/distance patterns.
    3. Run and STAND STILL in front — see how readings decay to noise.
"""

import time
import sys
from datetime import datetime
from collections import Counter

sys.path.insert(0, str(__file__).rsplit("/", 2)[0])
from lib.settings import load_settings

try:
    from RdLib.Rd import Rd
    from RdLib.config import config
    import numpy as np
except ImportError:
    print("RdLib not available. Install with: pip install RdLib --break-system-packages")
    sys.exit(1)

# --- Load settings (same as main player) ---
settings = load_settings()
MAX_RANGE = settings["hwFeatures"].get("radarMaxRangeMeters", 2.5)
TIMEOUT = settings["hwFeatures"].get("radarTargetTimeoutSec", 2.0)

# --- Setup radar with same Kalman config as production ---
config.set(Kalman=True)
config.set(distance_units="m")
config.set(Kalman_Q=np.diag([0.05, 0.05, 0.05, 0.05]))
config.set(Kalman_R=np.diag([50, 50]))

rd = Rd()

# --- Stats tracking ---
total_readings = 0
valid_readings = 0
valid_distances = []
mode_counts = Counter()
all_distances = []

# --- State (mirrors radar_controller.py logic) ---
last_valid_time = 0
target_present = False

POLL_INTERVAL = 0.1  # 100ms, same as production


def ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def main():
    global total_readings, valid_readings, last_valid_time, target_present

    print(f"\n{'='*72}")
    print(f"  RD-03D DIAGNOSTIC — What does the radar actually see?")
    print(f"{'='*72}")
    print(f"  Settings from settings.json:")
    print(f"    Max range : {MAX_RANGE}m")
    print(f"    Timeout   : {TIMEOUT}s")
    print(f"    Kalman    : ON  (Q=0.05, R=50)")
    print(f"{'='*72}")
    print()
    print(
        f"{'time':>12}  {'mode':>6}  {'dist':>6}  {'raw_d':>6}  "
        f"{'x':>6}  {'y':>6}  {'angle':>6}  {'in_range':>8}  {'state':>10}"
    )
    print(f"{'-'*12}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*6}  {'-'*8}  {'-'*10}")

    try:
        while True:
            data = rd.OutputDump()
            # OutputDump returns: (x, y, dist, angle, mode, raw_dist)
            x = data[0]
            y = data[1]
            dist = data[2]
            angle = data[3]
            mode = data[4]
            raw_dist = data[5] if len(data) > 5 else -1

            total_readings += 1
            mode_counts[mode] += 1
            all_distances.append(dist)

            # Same logic as radar_controller.py
            in_range = 0 < dist <= MAX_RANGE

            if in_range:
                valid_readings += 1
                valid_distances.append(dist)
                last_valid_time = time.time()

            # State machine (same as production)
            time_since = time.time() - last_valid_time if last_valid_time > 0 else 999
            now_present = time_since < TIMEOUT if last_valid_time > 0 else False

            # Detect edges for display
            state_str = ""
            if now_present and not target_present:
                state_str = "▶ STARTED"
            elif not now_present and target_present:
                state_str = "■ STOPPED"
            elif now_present:
                state_str = "  active"
            else:
                state_str = "  ·"

            target_present = now_present

            # Color hint: highlight suspicious readings (in range but high mode noise)
            flag = "  ✓" if in_range else "  ·"

            print(
                f"{ts():>12}  {mode:>6}  {dist:>6.2f}  {raw_dist:>6.2f}  "
                f"{x:>6.2f}  {y:>6.2f}  {angle:>6.1f}  {flag:>8}  {state_str:>10}"
            )

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        pass

    # --- Summary ---
    print(f"\n{'='*72}")
    print(f"  SUMMARY ({total_readings} readings)")
    print(f"{'='*72}")
    print(f"  'Valid' readings (0 < dist <= {MAX_RANGE}m): {valid_readings}/{total_readings} ({100*valid_readings/max(total_readings,1):.1f}%)")
    print()

    print(f"  Mode distribution (THIS IS THE KEY INFO):")
    for mode_val, count in sorted(mode_counts.items()):
        pct = 100 * count / max(total_readings, 1)
        bar = "█" * int(pct / 2)
        print(f"    mode={mode_val:>3} : {count:>5}x ({pct:5.1f}%) {bar}")
    print()

    if valid_distances:
        print(f"  Valid distance stats:")
        print(f"    min: {min(valid_distances):.2f}m")
        print(f"    max: {max(valid_distances):.2f}m")
        print(f"    avg: {sum(valid_distances)/len(valid_distances):.2f}m")

        # Distance histogram (simple text)
        print(f"\n  Distance histogram (valid readings):")
        buckets = [0] * 10
        for d in valid_distances:
            idx = min(int(d / MAX_RANGE * 10), 9)
            buckets[idx] += 1
        for i, count in enumerate(buckets):
            lo = i * MAX_RANGE / 10
            hi = (i + 1) * MAX_RANGE / 10
            bar = "█" * min(int(count / max(1, max(buckets)) * 40), 40)
            print(f"    {lo:4.1f}-{hi:4.1f}m : {count:>4}x {bar}")
    else:
        print(f"  No valid readings recorded.")

    print(f"\n{'='*72}")
    print(f"  → If valid% is high in an EMPTY room, filter on 'mode' or add")
    print(f"    consistency checks. See mode distribution above for clues.")
    print(f"{'='*72}\n")


if __name__ == "__main__":
    main()
