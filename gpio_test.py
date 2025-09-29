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
# GPIO.add_event_detect(PLAY_PAUSE_BTN_PIN, GPIO.FALLING, callback=button_pressed_callback, bouncetime=300)
# GPIO.add_event_detect(STOP_BTN_PIN, GPIO.FALLING, callback=button_pressed_callback, bouncetime=300)

try:
    # 1. Test the LED: Blink 5 times
    print("\n1. Testing LED on GPIO 27. It should blink 5 times.")
    for i in range(5):
        GPIO.output(LED_PIN, GPIO.HIGH)
        time.sleep(0.2)
        GPIO.output(LED_PIN, GPIO.LOW)
        time.sleep(0.2)
    print("-> LED test complete.")

    # 2. Test the buttons with polling
    print("\n2. Testing Buttons (polling mode). Press the buttons connected to GPIO 22 and GPIO 10.")
    print("   Waiting for button presses...")
    
    last_play_state = GPIO.HIGH
    last_stop_state = GPIO.HIGH
    
    while True:
        play_state = GPIO.input(PLAY_PAUSE_BTN_PIN)
        stop_state = GPIO.input(STOP_BTN_PIN)
        
        if play_state == GPIO.LOW and last_play_state == GPIO.HIGH:
            print(f"-> Button press detected on GPIO {PLAY_PAUSE_BTN_PIN}!")
        
        if stop_state == GPIO.LOW and last_stop_state == GPIO.HIGH:
            print(f"-> Button press detected on GPIO {STOP_BTN_PIN}!")
        
        last_play_state = play_state
        last_stop_state = stop_state
        time.sleep(0.05)  # Small delay to debounce

except KeyboardInterrupt:
    print("\nExiting test.")