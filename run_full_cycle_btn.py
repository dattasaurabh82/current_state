#!/usr/bin/env python3
"""
Monitors GPIO button to trigger full news→music generation cycle.
Runs as a standalone service alongside run_player.py.
"""

import subprocess
import time
from datetime import datetime
from pathlib import Path
from loguru import logger

import RPi.GPIO as GPIO
from lib.settings import load_settings

# Project directory (for subprocess cwd)
PROJECT_DIR = Path(__file__).parent

# Load settings
settings = load_settings()

# Configuration (from settings.json)
BTN_PIN = settings["inputPins"]["runFullCycleBtn_pin"]
DEBOUNCE = settings["hwFeatures"]["btnDebounceTimeMs"]


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


def handle_button_press():
    """Trigger the full news→music generation cycle."""
    logger.warning("🚀 Full cycle button pressed! Starting news→music pipeline...")
    try:
        subprocess.Popen(
            ["uv", "run", "python", "main.py", "--fetch", "true", "--play", "false"],
            cwd=PROJECT_DIR
        )
        logger.success("Pipeline subprocess started.")
    except Exception as e:
        logger.error(f"Failed to start pipeline: {e}")


def main():
    setup_logger()
    logger.info("--- Starting Full Cycle Button Monitor ---")
    logger.info(f"Listening on GPIO{BTN_PIN}")

    try:
        GPIO.setwarnings(False)
        GPIO.cleanup()
        time.sleep(0.1)

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

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
        GPIO.cleanup()
        logger.info("--- Full Cycle Button Monitor Stopped ---")


if __name__ == "__main__":
    main()
