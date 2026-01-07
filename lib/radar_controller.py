# lib/radar_controller.py

"""
Radar controller for motion detection.
Supports RCWL-0516 (GPIO-based) and RD-03D (serial-based).
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

# Try to import RD-03D library
try:
    from RdLib.Rd import Rd
    from RdLib.config import config as rd_config
    import numpy as np
    RD03D_AVAILABLE = True
except ImportError:
    RD03D_AVAILABLE = False

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
        
        # RCWL-0516 state
        self._last_gpio_state = None
        self._motion_active = False  # Tracks current motion state for LED
        
        # RD-03D state
        self._rd = None
        self._max_range = settings["hwFeatures"].get("radarMaxRangeMeters", 2.5)
        self._timeout = settings["hwFeatures"].get("radarTargetTimeoutSec", 1.0)
        self._last_valid_time = 0
        self._last_distance = 0
        self._target_present = False
        
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
        
        # Model-specific setup
        if self.radar_model == "RCWL-0516":
            self._setup_rcwl0516()
        elif self.radar_model == "RD-03D":
            self._setup_rd03d()
    
    def _setup_enable_pin(self):
        """Setup GPIO for enable switch (always needed to check switch state)."""
        GPIO.setup(self.enable_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
    
    def _setup_rcwl0516(self):
        """Setup GPIO pin for RCWL-0516 radar sensor."""
        GPIO.setup(self.radar_pin, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        self._last_gpio_state = GPIO.input(self.radar_pin)
        self.enabled = True
        logger.info(f"RadarController initialized: {self.radar_model} on GPIO{self.radar_pin}")
    
    def _setup_rd03d(self):
        """Setup serial connection for RD-03D radar sensor."""
        if not RD03D_AVAILABLE:
            logger.error(
                "RD-03D requires RdLib library. "
                "Install with: pip install RdLib --break-system-packages"
            )
            self.enabled = False
            return
        
        try:
            # Initialize RD-03D
            self._rd = Rd()
            
            # Configure Kalman filter (tuned for human movement)
            rd_config.set(Kalman=True)
            rd_config.set(distance_units="m")
            rd_config.set(Kalman_Q=np.diag([0.05, 0.05, 0.05, 0.05]))
            rd_config.set(Kalman_R=np.diag([50, 50]))
            
            self.enabled = True
            logger.info(
                f"RadarController initialized: {self.radar_model} "
                f"(range: {self._max_range}m, timeout: {self._timeout}s)"
            )
        except Exception as e:
            logger.error(f"Failed to initialize RD-03D: {e}")
            self.enabled = False
    
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
        
        Works for both RCWL-0516 and RD-03D with same interface.
        """
        if not self.enabled or not IS_PI:
            return False, False
        
        if self.radar_model == "RCWL-0516":
            return self._check_rcwl0516()
        elif self.radar_model == "RD-03D":
            return self._check_rd03d()
        
        return False, False
    
    def _check_rcwl0516(self) -> tuple[bool, bool]:
        """
        Check RCWL-0516 motion state via GPIO.
        Returns: (motion_started, motion_stopped)
        """
        current_state = GPIO.input(self.radar_pin)
        
        motion_started = (current_state == GPIO.HIGH and self._last_gpio_state == GPIO.LOW)
        motion_stopped = (current_state == GPIO.LOW and self._last_gpio_state == GPIO.HIGH)
        
        # Update motion active state for LED
        if motion_started:
            self._motion_active = True
        elif motion_stopped:
            self._motion_active = False
        
        self._last_gpio_state = current_state
        return motion_started, motion_stopped
    
    def _check_rd03d(self) -> tuple[bool, bool]:
        """
        Check RD-03D motion state via serial.
        Returns: (motion_started, motion_stopped)
        
        Note: RD-03D is a Doppler radar - it detects MOVEMENT, not static presence.
        If someone stands still, readings become invalid/zero, which triggers timeout.
        This is expected behavior: no movement = motion stopped.
        """
        if not self._rd:
            return False, False
        
        try:
            data = self._rd.OutputDump()
            # OutputDump returns: (x, y, dist, angle, mode, raw_dist)
            dist = data[2]
            
            # Is there valid movement within range?
            valid_movement = (0 < dist <= self._max_range)
            
            if valid_movement:
                self._last_valid_time = time.time()
                self._last_distance = dist
            
            # Determine current state based on timeout
            time_since_valid = time.time() - self._last_valid_time
            currently_present = (time_since_valid < self._timeout) if self._last_valid_time > 0 else False
            
            # Detect edges
            motion_started = currently_present and not self._target_present
            motion_stopped = not currently_present and self._target_present
            
            # Update state
            if motion_started:
                self._motion_active = True
            elif motion_stopped:
                self._motion_active = False
            
            self._target_present = currently_present
            
            return motion_started, motion_stopped
            
        except Exception as e:
            logger.error(f"RD-03D read error: {e}")
            return False, False
    
    def is_motion_active(self) -> bool:
        """Get current motion active state (for LED display)."""
        return self._motion_active
    
    def get_current_state(self) -> bool:
        """Get raw current state (HIGH = motion active)."""
        if not self.enabled or not IS_PI:
            return False
        
        if self.radar_model == "RCWL-0516":
            return GPIO.input(self.radar_pin) == GPIO.HIGH
        elif self.radar_model == "RD-03D":
            return self._target_present
        
        return False
    
    def get_last_distance(self) -> float:
        """Get last valid distance reading (RD-03D only)."""
        return self._last_distance
