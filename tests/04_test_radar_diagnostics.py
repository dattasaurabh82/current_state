#!/usr/bin/env python3
"""
RD-03D Diagnostic Tool — See what the radar ACTUALLY reports + test filters.

Two modes (pass --filter to enable filter comparison):

  MODE 1 (default): Raw diagnostic
    uv run 04_test_radar_diagnostics.py
    Shows all radar fields every 100ms. Ctrl+C for summary.

  MODE 2: Filter comparison
    uv run 04_test_radar_diagnostics.py --filter
    Runs 4 filters side by side on same data stream:
      OLD    = current logic (1 reading triggers)
      C5     = 5 consecutive readings in range
      STABLE = 5 consecutive + distance std dev < 0.4m
      TIGHT  = 5 consecutive + std dev < 0.4m + range 2.0m
    Ctrl+C for scoreboard.

Uses settings from settings.json (same config as the main player).
"""

import time
import sys
import math
from datetime import datetime
from collections import Counter, deque

sys.path.insert(0, str(__file__).rsplit("/", 2)[0])
from lib.settings import load_settings

try:
    from RdLib.Rd import Rd
    from RdLib.config import config
    import numpy as np
except ImportError:
    print("RdLib not available. Install with: pip install RdLib --break-system-packages")
    sys.exit(1)

# --- Load settings (same as production) ---
settings = load_settings()
MAX_RANGE = settings["hwFeatures"].get("radarMaxRangeMeters", 2.5)
TIMEOUT = settings["hwFeatures"].get("radarTargetTimeoutSec", 2.0)

# --- Setup radar (same as production) ---
config.set(Kalman=True)
config.set(distance_units="m")
config.set(Kalman_Q=np.diag([0.05, 0.05, 0.05, 0.05]))
config.set(Kalman_R=np.diag([50, 50]))

rd = Rd()

POLL_INTERVAL = 0.1


def ts():
    return datetime.now().strftime("%H:%M:%S.%f")[:-3]


def ts_short():
    return datetime.now().strftime("%H:%M:%S")


def std_dev(values):
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


# =========================================================
# MODE 1: Raw diagnostic
# =========================================================

def run_diagnostic():
    total_readings = 0
    valid_readings = 0
    valid_distances = []
    mode_counts = Counter()

    # State (mirrors radar_controller.py logic)
    last_valid_time = 0
    target_present = False

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
            x, y, dist, angle, mode = data[0], data[1], data[2], data[3], data[4]
            raw_dist = data[5] if len(data) > 5 else -1

            total_readings += 1
            mode_counts[mode] += 1
            in_range = 0 < dist <= MAX_RANGE

            if in_range:
                valid_readings += 1
                valid_distances.append(dist)
                last_valid_time = time.time()

            time_since = time.time() - last_valid_time if last_valid_time > 0 else 999
            now_present = time_since < TIMEOUT if last_valid_time > 0 else False

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
    print(f"  Mode distribution:")
    for mode_val, count in sorted(mode_counts.items()):
        pct = 100 * count / max(total_readings, 1)
        bar = "█" * int(pct / 2)
        print(f"    mode={mode_val:>3} : {count:>5}x ({pct:5.1f}%) {bar}")
    print()
    if valid_distances:
        print(f"  Valid distance stats:")
        print(f"    min: {min(valid_distances):.2f}m  max: {max(valid_distances):.2f}m  avg: {sum(valid_distances)/len(valid_distances):.2f}m")
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
    print(f"{'='*72}\n")


# =========================================================
# MODE 2: Filter comparison
# =========================================================

class FilterState:
    def __init__(self, name, consecutive_req, max_range, max_std_dev=None):
        self.name = name
        self.consecutive_req = consecutive_req
        self.max_range = max_range
        self.max_std_dev = max_std_dev
        self.last_valid_time = 0
        self.target_present = False
        self.consecutive_valid = 0
        self.recent_dists = deque(maxlen=consecutive_req)
        self.trigger_count = 0
        self.stop_count = 0

    def update(self, dist, now):
        in_range = 0 < dist <= self.max_range

        if in_range:
            self.consecutive_valid += 1
            self.recent_dists.append(dist)
        else:
            self.consecutive_valid = 0
            self.recent_dists.clear()

        confirmed = False
        if self.consecutive_valid >= self.consecutive_req:
            if self.max_std_dev is None:
                confirmed = True
            elif len(self.recent_dists) >= self.consecutive_req:
                sd = std_dev(list(self.recent_dists))
                confirmed = sd <= self.max_std_dev

        if confirmed:
            self.last_valid_time = now

        time_since = now - self.last_valid_time if self.last_valid_time > 0 else 999
        currently_present = (time_since < TIMEOUT) if self.last_valid_time > 0 else False

        started = currently_present and not self.target_present
        stopped = not currently_present and self.target_present
        self.target_present = currently_present

        if started:
            self.trigger_count += 1
        if stopped:
            self.stop_count += 1

        return started, stopped


def run_filter():
    filters = [
        FilterState("OLD   ", 1, MAX_RANGE, max_std_dev=None),
        FilterState("C5    ", 5, MAX_RANGE, max_std_dev=None),
        FilterState("STABLE", 5, MAX_RANGE, max_std_dev=0.4),
        FilterState("TIGHT ", 5, 2.0,       max_std_dev=0.4),
    ]

    print(f"\n{'='*65}")
    print(f"  Filter Comparison")
    print(f"  OLD    = 1 reading, range {MAX_RANGE}m")
    print(f"  C5     = 5 consecutive, range {MAX_RANGE}m")
    print(f"  STABLE = 5 consecutive + std_dev < 0.4m, range {MAX_RANGE}m")
    print(f"  TIGHT  = 5 consecutive + std_dev < 0.4m, range 2.0m")
    print(f"  Timeout: {TIMEOUT}s")
    print(f"{'='*65}")
    print(f"  [{ts_short()}] Waiting... (Ctrl+C to stop)\n")

    try:
        while True:
            data = rd.OutputDump()
            dist = data[2]
            now = time.time()

            for f in filters:
                started, stopped = f.update(dist, now)
                if started:
                    print(f"  [{ts_short()}] {f.name} ▶ STARTED  (dist: {dist:.2f}m)  [#{f.trigger_count}]")
                if stopped:
                    print(f"  [{ts_short()}] {f.name} ■ STOPPED")

            time.sleep(POLL_INTERVAL)

    except KeyboardInterrupt:
        pass

    print(f"\n{'='*65}")
    print(f"  SCOREBOARD")
    print(f"{'='*65}")
    print(f"  {'Filter':<10} {'Triggers':>10} {'Stops':>10}")
    print(f"  {'-'*10} {'-'*10} {'-'*10}")
    for f in filters:
        print(f"  {f.name:<10} {f.trigger_count:>10} {f.stop_count:>10}")
    print(f"{'='*65}\n")


# =========================================================
# Main
# =========================================================

if __name__ == "__main__":
    if "--filter" in sys.argv:
        run_filter()
    else:
        run_diagnostic()
