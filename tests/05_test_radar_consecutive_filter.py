#!/usr/bin/env python3
"""
RD-03D Consecutive Filter Test — Validate false trigger fix.

Tests the theory: false triggers are 1-2 stray readings dipping below threshold,
while real humans produce sustained runs of valid readings.

HOW TO RUN:
    cd ~/current_state/tests
    uv run 05_test_radar_consecutive_filter.py

TEST PROCEDURE:
    1. Run with EMPTY ROOM for 60+ seconds. You should see ZERO triggers.
       (Old logic would have triggered 2-3 times in that window)
    2. Walk in front of radar. Should trigger within ~0.5s of arrival.
    3. Ctrl+C to see comparison stats.

WHAT IT SHOWS:
    Runs BOTH the old logic and new logic side by side on the same data stream.
    Every trigger prints which logic fired, so you can directly compare.
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

# --- Load settings (same as production) ---
settings = load_settings()
MAX_RANGE = settings["hwFeatures"].get("radarMaxRangeMeters", 2.5)
TIMEOUT = settings["hwFeatures"].get("radarTargetTimeoutSec", 2.0)

# --- The new filter parameter ---
CONSECUTIVE_REQUIRED = 3  # Need 3 valid readings in a row (~300ms at 100ms poll)

# --- Setup radar (same as production) ---
config.set(Kalman=True)
config.set(distance_units="m")
config.set(Kalman_Q=np.diag([0.05, 0.05, 0.05, 0.05]))
config.set(Kalman_R=np.diag([50, 50]))

rd = Rd()


def ts():
    return datetime.now().strftime("%H:%M:%S")


def main():
    # --- OLD logic state (current production) ---
    old_last_valid_time = 0
    old_target_present = False
    old_trigger_count = 0

    # --- NEW logic state (with consecutive filter) ---
    new_last_valid_time = 0
    new_target_present = False
    new_trigger_count = 0
    consecutive_valid = 0  # <-- the new bit

    print(f"\n{'='*60}")
    print(f"  Consecutive Filter Test")
    print(f"  OLD = current logic (any 1 reading triggers)")
    print(f"  NEW = require {CONSECUTIVE_REQUIRED} consecutive valid readings")
    print(f"  Range: {MAX_RANGE}m | Timeout: {TIMEOUT}s")
    print(f"{'='*60}")
    print(f"  [{ts()}] Waiting for motion... (Ctrl+C to stop)\n")

    try:
        while True:
            data = rd.OutputDump()
            dist = data[2]
            in_range = 0 < dist <= MAX_RANGE
            now = time.time()

            # ========== OLD LOGIC (current production) ==========
            if in_range:
                old_last_valid_time = now

            old_time_since = now - old_last_valid_time if old_last_valid_time > 0 else 999
            old_currently_present = (old_time_since < TIMEOUT) if old_last_valid_time > 0 else False

            old_started = old_currently_present and not old_target_present
            old_stopped = not old_currently_present and old_target_present
            old_target_present = old_currently_present

            if old_started:
                old_trigger_count += 1
                print(f"  [{ts()}] OLD ▶ STARTED  (dist: {dist:.2f}m)  [total: {old_trigger_count}]")
            if old_stopped:
                print(f"  [{ts()}] OLD ■ STOPPED")

            # ========== NEW LOGIC (consecutive filter) ==========
            if in_range:
                consecutive_valid += 1
            else:
                consecutive_valid = 0

            # Only count as valid after N consecutive readings
            if consecutive_valid >= CONSECUTIVE_REQUIRED:
                new_last_valid_time = now

            new_time_since = now - new_last_valid_time if new_last_valid_time > 0 else 999
            new_currently_present = (new_time_since < TIMEOUT) if new_last_valid_time > 0 else False

            new_started = new_currently_present and not new_target_present
            new_stopped = not new_currently_present and new_target_present
            new_target_present = new_currently_present

            if new_started:
                new_trigger_count += 1
                print(f"  [{ts()}] NEW ▶ STARTED  (dist: {dist:.2f}m)  [total: {new_trigger_count}]")
            if new_stopped:
                print(f"  [{ts()}] NEW ■ STOPPED")

            time.sleep(0.1)

    except KeyboardInterrupt:
        pass

    print(f"\n{'='*60}")
    print(f"  RESULTS")
    print(f"{'='*60}")
    print(f"  OLD triggers: {old_trigger_count}")
    print(f"  NEW triggers: {new_trigger_count}")
    if old_trigger_count > 0:
        reduction = (1 - new_trigger_count / old_trigger_count) * 100
        print(f"  Reduction:    {reduction:.0f}%")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
