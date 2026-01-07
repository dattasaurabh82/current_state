# lib/radar_controller.py

"""
Radar controller for motion detection.
Supports RCWL-0516 (GPIO-based) with placeholder for RD-03D (serial-based).
"""

import sys
import time
from loguru import logger
from lib.settings import load_settings

try:
    import RPi.GPIO as GPIO
    IS_PI = True
except (RuntimeError, ModuleNotFoundError):
    IS_PI = False

# Load settings
settings = load_settings()

# Valid radar models
VALID_MODELS = ["RCWL-0516", "RD-03D"]


class RadarController:
    def __init__(self):
        self.radar_model = settings["inputPins"]["radarModel"]
        self.radar_pin = settings["inputPins"]["radarPin"]
        self.enable_pin = settings["inputPins"]["radarEnablePin"]
        self.enabled = False
        self._last_state = None
        
        # Validate radar model
        if self.radar_model not in VALID_MODELS:
            logger.error(
                f"Invalid radarModel: '{self.radar_model}'. "
                f"Valid options are: {VALID_MODELS}. "
                f"Please update settings.json and restart."
            )
            sys.exit(1)
        
        # Check for RD-03D (not implemented)
        if self.radar_model == "RD-03D":
            logger.warning(
                "radarModel 'RD-03D' (serial) is not implemented yet. "
                "Radar detection will be disabled. "
                "Use 'RCWL-0516' for GPIO-based detection."
            )
            self.enabled = False
            return
        
        # RCWL-0516 setup
        if IS_PI:
            self._setup_gpio()
            self.enabled = True
            logger.info(f"RadarController initialized: {self.radar_model} on GPIO{self.radar_pin}")
        else:
            logger.warning("Not running on Pi. Radar detection disabled.")
            self.enabled = False
    
    def _setup_gpio(self):
        """Setup GPIO pins for radar and enable switch."""
        # Radar pin - input with pull-down (RCWL-0516 outputs HIGH on motion)
        GPIO.setup(self.radar_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
        # Enable switch - input with pull-up (switch closes to GND)
        GPIO.setup(self.enable_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
        
        # Initialize last state
        self._last_state = GPIO.input(self.radar_pin)
    
    def is_switch_enabled(self) -> bool:
        """
        Check if radar enable switch is ON.
        Switch connects to GND when ON, so LOW = enabled.
        """
        if not IS_PI:
            return False
        return GPIO.input(self.enable_pin) == GPIO.LOW
    
    def is_motion_detected(self) -> bool:
        """
        Check for motion (rising edge detection).
        Returns True only on the transition from LOW to HIGH.
        """
        if not self.enabled or not IS_PI:
            return False
        
        current_state = GPIO.input(self.radar_pin)
        
        # Detect rising edge (LOW -> HIGH)
        motion_detected = (current_state == GPIO.HIGH and self._last_state == GPIO.LOW)
        
        self._last_state = current_state
        return motion_detected
    
    def get_current_state(self) -> bool:
        """Get raw current state of radar pin (HIGH = motion active)."""
        if not self.enabled or not IS_PI:
            return False
        return GPIO.input(self.radar_pin) == GPIO.HIGH
