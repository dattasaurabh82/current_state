#!/usr/bin/env python3
"""
Test RCWL-0516 Doppler Radar Sensor with lgpio
Sensor OUT pin connected to GPIO16
"""

import lgpio
import time
from datetime import datetime

# Configuration
RADAR_PIN = 16  # BCM pin number
CHIP = 0        # GPIO chip number (usually 0 for Pi 3)

def timestamp():
    """Return current time as formatted string."""
    return datetime.now().strftime("%H:%M:%S")

def main():
    h = None
    try:
        # Open GPIO chip
        h = lgpio.gpiochip_open(CHIP)
        
        # Claim pin as input
        lgpio.gpio_claim_input(h, RADAR_PIN)
        
        print(f"RCWL-0516 Radar Test (lgpio)")
        print(f"============================")
        print(f"Listening on GPIO{RADAR_PIN}")
        print(f"Press Ctrl+C to exit\n")
        print(f"[{timestamp()}] Waiting for motion...")
        
        last_state = lgpio.gpio_read(h, RADAR_PIN)
        
        while True:
            current_state = lgpio.gpio_read(h, RADAR_PIN)
            
            # Detect rising edge (LOW -> HIGH)
            if last_state == 0 and current_state == 1:
                print(f"[{timestamp()}] 🚨 Motion DETECTED!")
            
            # Detect falling edge (HIGH -> LOW)
            if last_state == 1 and current_state == 0:
                print(f"[{timestamp()}] ✅ Motion stopped.")
            
            last_state = current_state
            time.sleep(0.05)  # 50ms polling
            
    except KeyboardInterrupt:
        print(f"\n[{timestamp()}] Exiting...")
    
    finally:
        if h is not None:
            lgpio.gpiochip_close(h)
            print("GPIO closed.")

if __name__ == "__main__":
    main()
