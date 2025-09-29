# lib/hardware_player.py

import threading
from pathlib import Path
from typing import Optional
from loguru import logger
import time
from lib.player import AudioPlayer

# Import the GPIO library and handle potential errors if not on a Pi
try:
    import RPi.GPIO as GPIO
    IS_PI = True
except (RuntimeError, ModuleNotFoundError):
    IS_PI = False
    logger.warning("RPi.GPIO library not found. GPIO functionality will be disabled.")

# --- Pin Definitions ---
LED_PIN = 27
PLAY_PAUSE_BTN_PIN = 22
STOP_BTN_PIN = 10


def find_latest_song(directory="music_generated") -> Optional[Path]:
    """Finds the most recently created .wav file in a directory."""
    music_dir = Path(directory)
    if not music_dir.exists() or not music_dir.is_dir():
        return None
    
    wav_files = list(music_dir.glob("*.wav"))
    if not wav_files:
        return None
        
    return max(wav_files, key=lambda p: p.stat().st_mtime)


class HardwarePlayer:
    """
    Manages player state and audio playback via keyboard and GPIO.
    """

    def __init__(self):
        self.state = "STOPPED"  # Can be STOPPED, PLAYING, PAUSED
        self.player: Optional[AudioPlayer] = None
        self.latest_song: Optional[Path] = find_latest_song()
        self.led_pwm = None
        self.breathing_thread: Optional[threading.Thread] = None
        self.stop_breathing = threading.Event()
        self.lock = threading.Lock() # To prevent race conditions

        logger.info("Hardware Player initialized. State: STOPPED")
        if self.latest_song:
            logger.info(f"Found latest song: {self.latest_song.name}")
        else:
            logger.warning("No song found in 'music_generated' directory.")

        if IS_PI:
            self._setup_gpio()

    def _setup_gpio(self):
        """Sets up the GPIO pins for buttons and LED."""
        try:
            GPIO.setmode(GPIO.BCM)
            # LED Pin
            GPIO.setup(LED_PIN, GPIO.OUT)
            self.led_pwm = GPIO.PWM(LED_PIN, 100)  # PWM at 100Hz
            self.led_pwm.start(0) # Start with LED off

            # Button Pins with internal pull-up resistors
            GPIO.setup(PLAY_PAUSE_BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(STOP_BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Add event detection (interrupts)
            GPIO.add_event_detect(PLAY_PAUSE_BTN_PIN, GPIO.FALLING, callback=self.handle_toggle_play_pause, bouncetime=300)
            GPIO.add_event_detect(STOP_BTN_PIN, GPIO.FALLING, callback=self.handle_stop, bouncetime=300)
            
            logger.info("GPIO pins set up successfully.")
        except Exception as e:
            logger.error(f"Failed to set up GPIO: {e}")
            global IS_PI
            IS_PI = False

    def _update_led(self):
        """Controls the LED based on the player's state."""
        if not IS_PI or not self.led_pwm:
            # Log the intended action if not on a Pi
            if self.state == "PLAYING": logger.info("[LED] ON (Solid)")
            elif self.state == "PAUSED": logger.info("[LED] ON (Breathing)")
            else: logger.info("[LED] OFF")
            return
        
        # Stop any existing breathing effect
        self.stop_breathing.set()
        if self.breathing_thread and self.breathing_thread.is_alive():
            self.breathing_thread.join()

        if self.state == "PLAYING":
            self.led_pwm.ChangeDutyCycle(100) # Full brightness
        elif self.state == "STOPPED":
            self.led_pwm.ChangeDutyCycle(0) # Off
        elif self.state == "PAUSED":
            self.stop_breathing.clear()
            self.breathing_thread = threading.Thread(target=self._breathe_led, daemon=True)
            self.breathing_thread.start()

    def _breathe_led(self):
        """Runs in a thread to create a breathing effect for the LED."""
        pause_time = 0.02
        while not self.stop_breathing.is_set():
            # Fade up
            for duty_cycle in range(0, 101, 5):
                if self.stop_breathing.is_set(): break
                self.led_pwm.ChangeDutyCycle(duty_cycle)
                time.sleep(pause_time)
            # Fade down
            for duty_cycle in range(100, -1, -5):
                if self.stop_breathing.is_set(): break
                self.led_pwm.ChangeDutyCycle(duty_cycle)
                time.sleep(pause_time)


    def handle_toggle_play_pause(self, channel=None):
        """Handles the Play/Pause logic for both keyboard and GPIO."""
        with self.lock:
            logger.info(f"'Play/Pause' triggered. Current state: {self.state}")
            
            if self.state == "STOPPED":
                self.latest_song = find_latest_song()
                if self.latest_song:
                    logger.info(f"Starting playback for {self.latest_song.name}")
                    self.player = AudioPlayer(self.latest_song, loop_by_default=True)
                    self.player.play()
                    self.state = "PLAYING"
                else:
                    logger.error("No song file found to play.")
            
            elif self.state == "PLAYING":
                if self.player:
                    logger.info("Pausing playback.")
                    self.player.pause()
                    self.state = "PAUSED"

            elif self.state == "PAUSED":
                if self.player:
                    logger.info("Resuming playback.")
                    self.player.resume()
                    self.state = "PLAYING"
        
        self._update_led()
        self._print_status()

    def handle_stop(self, channel=None):
        """Handles the Stop logic for both keyboard and GPIO."""
        with self.lock:
            logger.info(f"'Stop' triggered. Current state: {self.state}")
            if self.state in ["PLAYING", "PAUSED"]:
                if self.player:
                    logger.info("Stopping playback.")
                    self.player.stop()
                    self.player = None
                self.state = "STOPPED"
        
        self._update_led()
        self._print_status()

    def listen_for_input(self):
        """Starts a loop to listen for simple text commands."""
        logger.info("Starting text command listener...")
        
        while True:
            self._print_status()
            command = input("Enter command > ").lower().strip()

            if command == 'p':
                self.handle_toggle_play_pause()
            elif command == 's':
                self.handle_stop()
            elif command == 'q':
                logger.warning("'q' entered. Exiting.")
                break
            else:
                logger.warning(f"Unknown command: '{command}'")
        
        self.cleanup()

    def _print_status(self):
        """Prints the current status to the console."""
        song_name = self.latest_song.name if self.latest_song else "None"
        print("\n" + "="*20 + " PLAYER STATUS " + "="*20)
        print(f"  State: {self.state}")
        print(f"  Song:  {song_name}")
        print("="*55)
        print("Controls: [P] Play/Pause | [S] Stop | [Q] Quit")

    def cleanup(self):
        """Stops all processes gracefully."""
        logger.warning("Cleaning up player...")
        if self.player:
            self.player.stop()
        if IS_PI:
            self.stop_breathing.set()
            if self.breathing_thread and self.breathing_thread.is_alive():
                self.breathing_thread.join()
            self.led_pwm.stop()
            GPIO.cleanup()
        logger.info("Cleanup complete.")