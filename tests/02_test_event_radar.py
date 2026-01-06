#!/usr/bin/env python3
"""
Test RCWL-0516 Doppler Radar Sensor with RPi.GPIO (polling)
Sensor OUT pin connected to GPIO16
LED on GPIO23 indicates motion state (PWM controlled)
"""

import RPi.GPIO as GPIO
import time
from datetime import datetime

# Configuration
RADAR_PIN = 16  # BCM pin number
LED_PIN = 23    # BCM pin number
LED_BRIGHTNESS = 25  # Percentage (0-100)

def timestamp():
    """Return current time as formatted string."""
    return datetime.now().strftime("%H:%M:%S")

def main():
    # Clean up any previous state
    GPIO.setwarnings(False)
    GPIO.cleanup()
    
    led_pwm = None
    
    try:
        # Setup
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RADAR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(LED_PIN, GPIO.OUT)
        
        # Setup PWM on LED pin (100Hz frequency)
        led_pwm = GPIO.PWM(LED_PIN, 100)
        led_pwm.start(0)  # Start with LED off
        
        print(f"RCWL-0516 Radar Test (RPi.GPIO polling)")
        print(f"========================================")
        print(f"Radar: GPIO{RADAR_PIN}")
        print(f"LED:   GPIO{LED_PIN} (PWM @ {LED_BRIGHTNESS}%)")
        print(f"Press Ctrl+C to exit\n")
        print(f"[{timestamp()}] Waiting for motion...")
        
        last_state = GPIO.input(RADAR_PIN)
        
        while True:
            current_state = GPIO.input(RADAR_PIN)
            
            # Detect rising edge (LOW -> HIGH) = motion detected
            if current_state == GPIO.HIGH and last_state == GPIO.LOW:
                print(f"[{timestamp()}] 🏃🏻 Motion DETECTED!")
                led_pwm.ChangeDutyCycle(LED_BRIGHTNESS)
            
            # Detect falling edge (HIGH -> LOW) = motion stopped
            if current_state == GPIO.LOW and last_state == GPIO.HIGH:
                print(f"[{timestamp()}] Motion stopped.")
                led_pwm.ChangeDutyCycle(0)
            
            last_state = current_state
            time.sleep(0.05)  # 50ms polling
            
    except KeyboardInterrupt:
        print(f"\n[{timestamp()}] Exiting...")
    
    finally:
        if led_pwm:
            led_pwm.stop()
        GPIO.cleanup()
        print("GPIO cleaned up.")

if __name__ == "__main__":
    main()
