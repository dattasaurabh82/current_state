# gpio_test.py

import time
import RPi.GPIO as GPIO

# --- Pin Definitions ---
LED_PIN = 27
PLAY_PAUSE_BTN_PIN = 22
STOP_BTN_PIN = 10

# --- A simple callback function for button presses ---
def button_pressed_callback(channel):
    print(f"-> Button press detected on GPIO {channel}!")

print("--- GPIO Test Script ---")
print("Press Ctrl+C to exit.")

# Clean up any previous GPIO settings
GPIO.cleanup()
time.sleep(0.5)  # Small delay after cleanup

# Use BCM pin numbering
GPIO.setmode(GPIO.BCM)
# Disable warnings about channels being in use
GPIO.setwarnings(False)

# Setup pins
GPIO.setup(LED_PIN, GPIO.OUT)
GPIO.setup(PLAY_PAUSE_BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(STOP_BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Add event detection for buttons
GPIO.add_event_detect(PLAY_PAUSE_BTN_PIN, GPIO.FALLING, callback=button_pressed_callback, bouncetime=300)
GPIO.add_event_detect(STOP_BTN_PIN, GPIO.FALLING, callback=button_pressed_callback, bouncetime=300)