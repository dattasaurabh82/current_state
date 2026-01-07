#!/usr/bin/env python3
"""
Monitors GPIO button to trigger full news→music generation cycle.
Runs as a standalone service alongside run_player.py.
"""

import subprocess
import threading
import time
from pathlib import Path
from loguru import logger

import RPi.GPIO as GPIO
from lib.settings import load_settings

# Project directory (for subprocess cwd)
PROJECT_DIR = Path(__file__).parent

# Load settings
settings = load_settings()

# Configuration (from settings.json)
BTN_PIN = settings["inputPins"]["runFullCycleBtnPin"]
LED_PIN = settings["outputPins"]["radarStateLEDPin"]
DEBOUNCE = settings["hwFeatures"]["btnDebounceTimeMs"]
MAX_LED_BRIGHTNESS = settings["hwFeatures"]["maxLEDBrightness"]
PROGRESS_BREATHING_FREQ = settings["hwFeatures"]["ProcessProgressBreathingFreq"]
ERROR_BREATHING_FREQ = settings["hwFeatures"]["ProcessErrBreathingFreq"]

# Global state
led_pwm = None
stop_breathing = threading.Event()
breathing_thread = None


def setup_logger():
    """Configures a simple logger for the service."""
    log_file_path = "full_cycle_btn.log"
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    logger.add(
        log_file_path,
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        encoding="utf-8"
    )
    logger.info(f"Full cycle button logger initialized. Logging to '{log_file_path}'")


def breathe_led(freq):
    """Breathing effect for LED at specified frequency."""
    global led_pwm
    if not led_pwm:
        return
    while not stop_breathing.is_set():
        for duty_cycle in range(0, MAX_LED_BRIGHTNESS + 1, 5):
            if stop_breathing.is_set():
                break
            led_pwm.ChangeDutyCycle(duty_cycle)
            time.sleep(freq)
        for duty_cycle in range(MAX_LED_BRIGHTNESS, -1, -5):
            if stop_breathing.is_set():
                break
            led_pwm.ChangeDutyCycle(duty_cycle)
            time.sleep(freq)


def start_breathing(freq):
    """Start LED breathing in background thread."""
    global breathing_thread
    stop_breathing.clear()
    breathing_thread = threading.Thread(target=breathe_led, args=(freq,), daemon=True)
    breathing_thread.start()


def stop_breathing_led():
    """Stop LED breathing and turn off LED."""
    global led_pwm
    stop_breathing.set()
    if breathing_thread and breathing_thread.is_alive():
        breathing_thread.join(timeout=1)
    if led_pwm:
        led_pwm.ChangeDutyCycle(0)


def error_blink(duration=3):
    """Fast breathing for error indication."""
    start_breathing(ERROR_BREATHING_FREQ)
    time.sleep(duration)
    stop_breathing_led()


def handle_button_press():
    """Trigger the full news→music generation cycle."""
    logger.warning("Full cycle button pressed! Starting news→music pipeline...")
    
    # Start progress breathing
    start_breathing(PROGRESS_BREATHING_FREQ)
    
    try:
        result = subprocess.run(
            ["uv", "run", "python", "main.py", "--fetch", "true", "--play", "false"],
            cwd=PROJECT_DIR
        )
        
        # Stop progress breathing
        stop_breathing_led()
        
        if result.returncode == 0:
            logger.success("✅ Pipeline completed successfully!")
        else:
            logger.error(f"❌ Pipeline failed with exit code: {result.returncode}")
            error_blink(duration=3)
            
    except Exception as e:
        stop_breathing_led()
        logger.error(f"Failed to start pipeline: {e}")
        error_blink(duration=3)
    finally:
        logger.info(f"Listening on GPIO{BTN_PIN}")


def main():
    global led_pwm
    
    setup_logger()
    logger.info("--- Starting Full Cycle Button Monitor ---")
    logger.info(f"Listening on GPIO{BTN_PIN}")

    try:
        GPIO.setwarnings(False)
        GPIO.cleanup()
        time.sleep(0.1)

        GPIO.setmode(GPIO.BCM)
        
        # Setup button
        GPIO.setup(BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Setup LED with PWM
        GPIO.setup(LED_PIN, GPIO.OUT)
        led_pwm = GPIO.PWM(LED_PIN, 100)
        led_pwm.start(0)

        last_state = GPIO.HIGH

        while True:
            state = GPIO.input(BTN_PIN)

            # Detect falling edge (HIGH -> LOW)
            if state == GPIO.LOW and last_state == GPIO.HIGH:
                handle_button_press()

            last_state = state
            time.sleep(DEBOUNCE)

    except KeyboardInterrupt:
        logger.warning("Interrupted. Shutting down...")
    finally:
        stop_breathing_led()
        if led_pwm:
            led_pwm.stop()
        GPIO.cleanup()
        logger.info("--- Full Cycle Button Monitor Stopped ---")


if __name__ == "__main__":
    main()
