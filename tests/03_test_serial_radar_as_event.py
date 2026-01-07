#!/usr/bin/env python3
"""
Test RD-03D radar with event-based interface (like RCWL-0516).
Converts continuous distance readings into motion_started/motion_stopped events.
"""

import time
from datetime import datetime
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])  # Add project root to path
from lib.settings import load_settings

# Load settings
settings = load_settings()

try:
    from RdLib.Rd import Rd
    from RdLib.config import config
    import numpy as np
    RD_AVAILABLE = True
except ImportError:
    RD_AVAILABLE = False
    print("RdLib not available. Install with: pip install RdLib")

# --- CONFIGURATION ---
MAX_RANGE_METERS = 2.5  # Ignore readings beyond this (walls)
TARGET_TIMEOUT_SEC = 1.0  # Seconds without valid reading = target gone
LED_PIN = settings["outputPins"]["radarStateLEDPin"]

# Try to import GPIO for LED feedback
try:
    import RPi.GPIO as GPIO
    HAS_GPIO = True
except (ImportError, RuntimeError):
    HAS_GPIO = False
    print("GPIO not available. Running without LED feedback.")


def timestamp():
    """Return current time as formatted string."""
    return datetime.now().strftime("%H:%M:%S")


class RD03DEventWrapper:
    """
    Wraps RD-03D continuous readings into event-based interface.
    Mimics RCWL-0516 behavior: motion_started, motion_stopped events.
    """
    
    def __init__(self, max_range: float = 2.5, timeout: float = 1.0):
        self.max_range = max_range
        self.timeout = timeout
        
        # State tracking
        self._target_present = False
        self._last_valid_time = 0
        self._last_distance = 0
        
        # Initialize RD-03D
        self.rd = Rd()
        
        # Configure Kalman filter (from test script)
        config.set(Kalman=True)
        config.set(distance_units="m")
        config.set(Kalman_Q=np.diag([0.05, 0.05, 0.05, 0.05]))
        config.set(Kalman_R=np.diag([50, 50]))
        
        print(f"RD-03D initialized. Max range: {max_range}m, Timeout: {timeout}s")
    
    def check_motion_state(self) -> tuple[bool, bool, float]:
        """
        Check motion state and detect edges.
        
        Returns: (motion_started, motion_stopped, distance)
        - motion_started: True when target enters range
        - motion_stopped: True when target leaves range (or timeout or standing still)
        - distance: Current distance reading (0 if invalid/out of range)
        
        Note: RD-03D is a Doppler radar - it detects MOVEMENT, not static presence.
        If someone stands still, readings become invalid/zero, which triggers timeout.
        This is expected behavior: no movement = motion stopped.
        """
        try:
            data = self.rd.OutputDump()
            # OutputDump returns: (x, y, dist, angle, mode, raw_dist)
            dist = data[2]
            
            # Is there valid movement within range?
            # Doppler radar: dist > 0 means movement detected
            # dist == 0 or invalid means no movement (standing still or no target)
            valid_movement = (0 < dist <= self.max_range)
            
            if valid_movement:
                self._last_valid_time = time.time()
                self._last_distance = dist
            
            # Determine current state based on timeout
            # No valid movement for timeout period = motion stopped
            # (either target left, or target is standing still)
            time_since_valid = time.time() - self._last_valid_time
            currently_present = (time_since_valid < self.timeout) if self._last_valid_time > 0 else False
            
            # Detect edges
            motion_started = currently_present and not self._target_present
            motion_stopped = not currently_present and self._target_present
            
            # Update state
            self._target_present = currently_present
            
            return motion_started, motion_stopped, dist if valid_movement else 0
            
        except Exception as e:
            print(f"[{timestamp()}] Error reading sensor: {e}")
            return False, False, 0
    
    def is_target_present(self) -> bool:
        """Get current target presence state."""
        return self._target_present
    
    def get_last_distance(self) -> float:
        """Get last valid distance reading."""
        return self._last_distance


def main():
    if not RD_AVAILABLE:
        print("Cannot run test without RdLib.")
        return
    
    # Setup GPIO for LED if available
    led_pwm = None
    if HAS_GPIO:
        GPIO.setwarnings(False)
        GPIO.cleanup()
        time.sleep(0.1)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(LED_PIN, GPIO.OUT)
        led_pwm = GPIO.PWM(LED_PIN, 100)
        led_pwm.start(0)
    
    print(f"\nRD-03D Event-Based Test")
    print(f"=======================")
    print(f"Max Range: {MAX_RANGE_METERS}m")
    print(f"Timeout:   {TARGET_TIMEOUT_SEC}s")
    if HAS_GPIO:
        print(f"LED:       GPIO{LED_PIN}")
    print(f"Press Ctrl+C to exit\n")
    print(f"[{timestamp()}] Waiting for motion...")
    
    try:
        radar = RD03DEventWrapper(
            max_range=MAX_RANGE_METERS,
            timeout=TARGET_TIMEOUT_SEC
        )
        
        while True:
            motion_started, motion_stopped, distance = radar.check_motion_state()
            
            if motion_started:
                print(f"[{timestamp()}] 🏃🏻 Motion DETECTED! (distance: {distance:.2f}m)")
                if led_pwm:
                    led_pwm.ChangeDutyCycle(25)
            
            if motion_stopped:
                print(f"[{timestamp()}] Motion stopped.")
                if led_pwm:
                    led_pwm.ChangeDutyCycle(0)
            
            # Optional: Print continuous distance when target present
            # if radar.is_target_present() and distance > 0:
            #     print(f"[{timestamp()}] Distance: {distance:.2f}m")
            
            time.sleep(0.1)  # 100ms polling
            
    except KeyboardInterrupt:
        print(f"\n[{timestamp()}] Exiting...")
    
    finally:
        if led_pwm:
            led_pwm.stop()
        if HAS_GPIO:
            GPIO.cleanup()
        print("Cleanup complete.")


if __name__ == "__main__":
    main()
