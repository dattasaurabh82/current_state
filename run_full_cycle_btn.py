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
RADAR_ENABLE_PIN = settings["inputPins"]["radarEnablePin"]
DEBOUNCE = settings["hwFeatures"]["btnDebounceTimeMs"]
MAX_LED_BRIGHTNESS = settings["hwFeatures"]["maxLEDBrightness"]
PROGRESS_BREATHING_FREQ = settings["hwFeatures"]["ProcessProgressBreathingFreq"]
ERROR_BREATHING_FREQ = settings["hwFeatures"]["ProcessErrBreathingFreq"]

# Global state
led_pwm = None
led_enabled = False  # Whether we own the LED
stop_breathing = threading.Event()
breathing_thread = None


def setup_logger():
    """Configures a simple logger for the service."""
    log_file_path = PROJECT_DIR / "logs" / "full_cycle_btn.log"
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


def is_radar_enabled() -> bool:
    """Check if radar enable switch is ON (LOW = enabled)."""
    return GPIO.input(RADAR_ENABLE_PIN) == GPIO.LOW


def breathe_led(freq):
    """Breathing effect for LED at specified frequency."""
    global led_pwm
    if not led_pwm or not led_enabled:
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
    if not led_enabled:
        return
    stop_breathing.clear()
    breathing_thread = threading.Thread(target=breathe_led, args=(freq,), daemon=True)
    breathing_thread.start()


def stop_breathing_led():
    """Stop LED breathing and turn off LED."""
    global led_pwm
    stop_breathing.set()
    if breathing_thread and breathing_thread.is_alive():
        breathing_thread.join(timeout=1)
    if led_pwm and led_enabled:
        led_pwm.ChangeDutyCycle(0)


def error_blink(duration=3):
    """Fast breathing for error indication."""
    if not led_enabled:
        return
    start_breathing(ERROR_BREATHING_FREQ)
    time.sleep(duration)
    stop_breathing_led()


def handle_button_press():
    """Trigger the full news→music generation cycle."""
    global led_enabled
    
    # Check if radar is enabled - if so, skip entirely
    if is_radar_enabled():
        logger.warning(
            "⚠️ Radar is enabled. Cannot run full cycle while radar is active. "
            "Disable the radar switch (GPIO6) to use this button."
        )
        return
    
    logger.warning("Full cycle button pressed! Starting news→music pipeline...")
    
    # Start progress breathing (only if LED is available)
    if led_enabled:
        start_breathing(PROGRESS_BREATHING_FREQ)
    
    try:
        result = subprocess.run(
            ["/home/pi/.local/bin/uv", "run", "python", "main.py", "--fetch", "true", "--play", "false"],
            cwd=PROJECT_DIR
        )
        
        # Stop progress breathing
        if led_enabled:
            stop_breathing_led()
        
        if result.returncode == 0:
            logger.success("✅ Pipeline completed successfully!")
        else:
            logger.error(f"❌ Pipeline failed with exit code: {result.returncode}")
            error_blink(duration=3)
            
    except Exception as e:
        if led_enabled:
            stop_breathing_led()
        logger.error(f"Failed to start pipeline: {e}")
        error_blink(duration=3)
    finally:
        logger.info(f"Listening on GPIO{BTN_PIN}")


def main():
    global led_pwm, led_enabled
    
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
        
        # Setup radar enable pin to check switch state
        GPIO.setup(RADAR_ENABLE_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Setup LED only if radar is disabled
        if not is_radar_enabled():
            GPIO.setup(LED_PIN, GPIO.OUT)
            led_pwm = GPIO.PWM(LED_PIN, 100)
            led_pwm.start(0)
            led_enabled = True
            logger.info("Radar is OFF. LED feedback enabled.")
        else:
            led_enabled = False
            logger.info("Radar is ON. LED feedback disabled (owned by HardwarePlayer).")

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
        if led_pwm and led_enabled:
            led_pwm.stop()
        GPIO.cleanup()
        logger.info("--- Full Cycle Button Monitor Stopped ---")


if __name__ == "__main__":
    main()
