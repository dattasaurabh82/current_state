#!/usr/bin/env python3
"""
Test RCWL-0516 Doppler Radar Sensor with RPi.GPIO
Sensor OUT pin connected to GPIO16
"""

import RPi.GPIO as GPIO
import time
from datetime import datetime

# Configuration
RADAR_PIN = 16  # BCM pin number
DEBOUNCE_MS = 200  # Debounce time in milliseconds

def timestamp():
    """Return current time as formatted string."""
    return datetime.now().strftime("%H:%M:%S")

def on_motion_detected(channel):
    """Callback when motion is detected (rising edge)."""
    print(f"[{timestamp()}] 🚨 Motion DETECTED!")

def on_motion_stopped(channel):
    """Callback when motion stops (falling edge)."""
    print(f"[{timestamp()}] ✅ Motion stopped.")

def main():
    # Clean up any previous state first
    GPIO.setwarnings(False)
    GPIO.cleanup()
    
    try:
        # Setup
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RADAR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        # Remove any existing event detection before adding new one
        try:
            GPIO.remove_event_detect(RADAR_PIN)
        except:
            pass  # Ignore if no event was registered
        
        # Register event callback for rising edge
        GPIO.add_event_detect(
            RADAR_PIN, 
            GPIO.RISING, 
            callback=on_motion_detected, 
            bouncetime=DEBOUNCE_MS
        )
        
        print(f"RCWL-0516 Radar Test")
        print(f"====================")
        print(f"Listening on GPIO{RADAR_PIN}")
        print(f"Debounce: {DEBOUNCE_MS}ms")
        print(f"Press Ctrl+C to exit\n")
        print(f"[{timestamp()}] Waiting for motion...")
        
        last_state = GPIO.input(RADAR_PIN)
        
        while True:
            current_state = GPIO.input(RADAR_PIN)
            
            # Detect falling edge manually (HIGH -> LOW)
            if last_state == 1 and current_state == 0:
                on_motion_stopped(RADAR_PIN)
            
            last_state = current_state
            time.sleep(0.1)  # Small sleep to reduce CPU usage
            
    except KeyboardInterrupt:
        print(f"\n[{timestamp()}] Exiting...")
    
    finally:
        GPIO.cleanup()
        print("GPIO cleaned up.")

if __name__ == "__main__":
    main()
