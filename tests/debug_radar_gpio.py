#!/usr/bin/env python3
"""
Debug script to check raw GPIO state for RCWL-0516.
Prints continuous readings to diagnose hardware issues.
"""

import RPi.GPIO as GPIO
import time
import sys
sys.path.insert(0, str(__file__).rsplit('/', 2)[0])
from lib.settings import load_settings

settings = load_settings()
RADAR_PIN = settings["inputPins"]["radarPin"]

print(f"RCWL-0516 Debug - Raw GPIO{RADAR_PIN} State")
print("=" * 40)
print("Expected: 0 = no motion, 1 = motion")
print("If always 0 or always 1: check wiring/power")
print("Press Ctrl+C to exit\n")

GPIO.setwarnings(False)
GPIO.cleanup()
time.sleep(0.1)

GPIO.setmode(GPIO.BCM)
GPIO.setup(RADAR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

try:
    count = 0
    while True:
        state = GPIO.input(RADAR_PIN)
        print(f"[{count:04d}] GPIO{RADAR_PIN} = {state}", end="\r")
        count += 1
        time.sleep(0.1)
except KeyboardInterrupt:
    print("\n\nExiting...")
finally:
    GPIO.cleanup()
    print("Done.")
