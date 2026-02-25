#!/usr/bin/env python3
"""
RD-03D Filter Sweep — Find the right consecutive count.

Runs 5 filters in parallel on the same data stream:
  - OLD:  current logic (1 reading)
  - C3:   3 consecutive readings (~300ms)
  - C5:   5 consecutive readings (~500ms)
  - C8:   8 consecutive readings (~800ms)
  - C5+R2: 5 consecutive + reduced range 2.0m

Same data, different filters. Find which one has:
  ✓ ZERO triggers in empty room
  ✓ Still triggers when you walk in

HOW TO RUN:
    cd ~/current_state/tests
    uv run 06_test_radar_filter_sweep.py

TEST:
    1. Empty room 60-90s → note which filters trigger
    2. Walk in front → note which still detect you
    3. Ctrl+C → see scoreboard
"""

import time
import sys
from datetime import datetime

sys.path.insert(0, str(__file__).rsplit("/", 2)[0])
from lib.settings import load_settings

try:
    from RdLib.Rd import Rd
    from RdLib.config import config
    import numpy as np
except ImportError:
    print("RdLib not available. Install with: pip install RdLib --break-system-packages")
    sys.exit(1)

settings = load_settings()
MAX_RANGE = settings["hwFeatures"].get("radarMaxRangeMeters", 2.5)
TIMEOUT = settings["hwFeatures"].get("radarTargetTimeoutSec", 2.0)

config.set(Kalman=True)
config.set(distance_units="m")
config.set(Kalman_Q=np.diag([0.05, 0.05, 0.05, 0.05]))
config.set(Kalman_R=np.diag([50, 50]))

rd = Rd()


def ts():
    return datetime.now().strftime("%H:%M:%S")


class FilterState:
    """One instance of the detection logic with configurable params."""

    def __init__(self, name: str, consecutive_required: int, max_range: float):
        self.name = name
        self.consecutive_required = consecutive_required
        self.max_range = max_range
        self.last_valid_time = 0
        self.target_present = False
        self.consecutive_valid = 0
        self.trigger_count = 0
        self.stop_count = 0

    def update(self, dist: float, now: float) -> tuple[bool, bool]:
        in_range = 0 < dist <= self.max_range

        if in_range:
            self.consecutive_valid += 1
        else:
            self.consecutive_valid = 0

        if self.consecutive_valid >= self.consecutive_required:
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


def main():
    filters = [
        FilterState("OLD   ", consecutive_required=1, max_range=MAX_RANGE),
        FilterState("C3    ", consecutive_required=3, max_range=MAX_RANGE),
        FilterState("C5    ", consecutive_required=5, max_range=MAX_RANGE),
        FilterState("C8    ", consecutive_required=8, max_range=MAX_RANGE),
        FilterState("C5+R2 ", consecutive_required=5, max_range=2.0),
    ]

    print(f"\n{'='*60}")
    print(f"  Filter Sweep Test")
    print(f"  Range: {MAX_RANGE}m | Timeout: {TIMEOUT}s")
    print(f"  Filters: OLD(1), C3(3), C5(5), C8(8), C5+R2(5@2.0m)")
    print(f"{'='*60}")
    print(f"  [{ts()}] Waiting... (Ctrl+C to stop)\n")

    try:
        while True:
            data = rd.OutputDump()
            dist = data[2]
            now = time.time()

            for f in filters:
                started, stopped = f.update(dist, now)
                if started:
                    print(f"  [{ts()}] {f.name} ▶ STARTED  (dist: {dist:.2f}m)  [#{f.trigger_count}]")
                if stopped:
                    print(f"  [{ts()}] {f.name} ■ STOPPED")

            time.sleep(0.1)

    except KeyboardInterrupt:
        pass

    print(f"\n{'='*60}")
    print(f"  SCOREBOARD")
    print(f"{'='*60}")
    print(f"  {'Filter':<10} {'Triggers':>10} {'Stops':>10}")
    print(f"  {'-'*10} {'-'*10} {'-'*10}")
    for f in filters:
        print(f"  {f.name:<10} {f.trigger_count:>10} {f.stop_count:>10}")
    print(f"{'='*60}")
    print(f"  Goal: find the filter with 0 false triggers")
    print(f"  that still triggers when you walk in front.")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
