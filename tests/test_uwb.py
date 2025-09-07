# import RPi.GPIO as GPIO
# import time

# # --- Pin Configuration ---
# GPIO.setmode(GPIO.BCM) 
# SENSOR_PIN = 17 
# GPIO.setup(SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# print("Radar Sensor Test [Press CTRL+C to exit]")
# time.sleep(2) 
# print("Ready")

# try:
#     while True:
#         # Read the sensor's output and print its raw state (0 or 1)
#         pin_state = GPIO.input(SENSOR_PIN)
#         print(f"Sensor pin state: {pin_state}")
        
#         time.sleep(0.5)

# except KeyboardInterrupt:
#     print("Exiting...")

# finally:
#     GPIO.cleanup()

# ---------------------- #

# import RPi.GPIO as GPIO
# import time

# # --- Pin Configuration ---
# # Use BCM GPIO numbering
# GPIO.setmode(GPIO.BCM) 
# # The GPIO pin you connected the OUT pin to
# SENSOR_PIN = 17 

# # Set up the GPIO pin as an input
# # The pull-down resistor ensures the input is LOW when the sensor is not detecting
# GPIO.setup(SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# print("Radar Sensor Test [Press CTRL+C to exit]")
# time.sleep(2) # Give the sensor time to settle
# print("Ready")

# try:
#     while True:
#         # Read the sensor's output
#         if GPIO.input(SENSOR_PIN):
#             print("Motion Detected!")
#         else:
#             print("Clear.")
        
#         # Wait a moment before checking again
#         time.sleep(0.5)

# except KeyboardInterrupt:
#     print("Exiting...")

# finally:
#     # Clean up GPIO settings before exiting
#     GPIO.cleanup()  

# ---------------------- #

import RPi.GPIO as GPIO
import time
from datetime import timedelta

# --- Pin Configuration ---
SENSOR_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

# --- State Variables ---
is_person_present = False
start_time = None

print("Presence Logger Active [Press CTRL+C to exit]")
time.sleep(2) # Sensor settle time
print("Ready.")

try:
    while True:
        current_state = GPIO.input(SENSOR_PIN)
        
        # Check for a new presence event (transition from LOW to HIGH)
        if current_state and not is_person_present:
            start_time = time.time()
            is_person_present = True
            print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Person entered.")
            
        # Check for the end of a presence event (transition from HIGH to LOW)
        elif not current_state and is_person_present:
            if start_time is not None:
                end_time = time.time()
                duration_seconds = end_time - start_time
                # Format the duration for easy reading
                duration_formatted = str(timedelta(seconds=duration_seconds))
                print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Person left. Duration: {duration_formatted}")
            
            # Reset state
            is_person_present = False
            start_time = None

        time.sleep(0.1) # Check state 10 times per second

except KeyboardInterrupt:
    print("\nExiting...")

finally:
    GPIO.cleanup()