#!/usr/bin/env python3
"""
Test RCWL-0516 Doppler Radar Sensor with RPi.GPIO (polling)
Sensor OUT pin connected to GPIO16
"""

import RPi.GPIO as GPIO
import time
from datetime import datetime

# Configuration
RADAR_PIN = 16  # BCM pin number

def timestamp():
    """Return current time as formatted string."""
    return datetime.now().strftime("%H:%M:%S")

def main():
    # Clean up any previous state
    GPIO.setwarnings(False)
    GPIO.cleanup()
    
    try:
        # Setup
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RADAR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        print(f"RCWL-0516 Radar Test (RPi.GPIO polling)")
        print(f"========================================")
        print(f"Listening on GPIO{RADAR_PIN}")
        print(f"Press Ctrl+C to exit\n")
        print(f"[{timestamp()}] Waiting for motion...")
        
        last_state = GPIO.input(RADAR_PIN)
        
        while True:
            current_state = GPIO.input(RADAR_PIN)
            
            # Detect rising edge (LOW -> HIGH) = motion detected
            if current_state == GPIO.HIGH and last_state == GPIO.LOW:
                print(f"[{timestamp()}] 🏃🏻 Motion DETECTED!")
            
            # Detect falling edge (HIGH -> LOW) = motion stopped
            if current_state == GPIO.LOW and last_state == GPIO.HIGH:
                print(f"[{timestamp()}] Motion stopped.")
            
            last_state = current_state
            time.sleep(0.05)  # 50ms polling
            
    except KeyboardInterrupt:
        print(f"\n[{timestamp()}] Exiting...")
    
    finally:
        GPIO.cleanup()
        print("GPIO cleaned up.")

if __name__ == "__main__":
    main()
