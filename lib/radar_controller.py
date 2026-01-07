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
        self._motion_active = False  # Tracks current motion state for LED
        
        # Validate radar model
        if self.radar_model not in VALID_MODELS:
            logger.error(
                f"Invalid radarModel: '{self.radar_model}'. "
                f"Valid options are: {VALID_MODELS}. "
                f"Please update settings.json and restart."
            )
            sys.exit(1)
        
        if not IS_PI:
            logger.warning("Not running on Pi. Radar detection disabled.")
            self.enabled = False
            return
        
        # Always setup enable pin so we can read switch state
        self._setup_enable_pin()
        
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
        self._setup_radar_pin()
        self.enabled = True
        logger.info(f"RadarController initialized: {self.radar_model} on GPIO{self.radar_pin}")
    
    def _setup_enable_pin(self):
        """Setup GPIO for enable switch (always needed to check switch state)."""
        GPIO.setup(self.enable_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    def _setup_radar_pin(self):
        """Setup GPIO pin for radar sensor."""
        # Radar pin - input with pull-down (RCWL-0516 outputs HIGH on motion)
        GPIO.setup(self.radar_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        
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
    
    def check_motion_state(self) -> tuple[bool, bool]:
        """
        Check motion state and detect edges.
        Returns: (motion_started, motion_stopped)
        - motion_started: True on rising edge (LOW -> HIGH)
        - motion_stopped: True on falling edge (HIGH -> LOW)
        """
        if not self.enabled or not IS_PI:
            return False, False
        
        current_state = GPIO.input(self.radar_pin)
        
        motion_started = (current_state == GPIO.HIGH and self._last_state == GPIO.LOW)
        motion_stopped = (current_state == GPIO.LOW and self._last_state == GPIO.HIGH)
        
        # Update motion active state
        if motion_started:
            self._motion_active = True
        elif motion_stopped:
            self._motion_active = False
        
        self._last_state = current_state
        return motion_started, motion_stopped
    
    def is_motion_active(self) -> bool:
        """Get current motion active state (for LED display)."""
        return self._motion_active
    
    def get_current_state(self) -> bool:
        """Get raw current state of radar pin (HIGH = motion active)."""
        if not self.enabled or not IS_PI:
            return False
        return GPIO.input(self.radar_pin) == GPIO.HIGH
