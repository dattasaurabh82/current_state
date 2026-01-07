# lib/hardware_player.py

import threading
from pathlib import Path
from typing import Optional
from loguru import logger
import time
from lib.player import AudioPlayer
from lib.settings import load_settings

try:
    import RPi.GPIO as GPIO
    IS_PI = True
except (RuntimeError, ModuleNotFoundError):
    IS_PI = False
    logger.warning("RPi.GPIO library not found. GPIO functionality will be disabled.")

# Load settings
settings = load_settings()

# Pin Definitions (from settings.json)
LED_PIN = settings["outputPins"]["playerStateLEDPin"]
PLAY_PAUSE_BTN_PIN = settings["inputPins"]["playPauseBtnPin"]
STOP_BTN_PIN = settings["inputPins"]["stopBtnPin"]

# Hardware Features (from settings.json)
BTN_DEBOUNCE_TIME = settings["hwFeatures"]["btnDebounceTimeMs"]
MAX_LED_BRIGHTNESS = settings["hwFeatures"]["maxLEDBrightness"]
PAUSE_BREATHING_FREQ = settings["hwFeatures"]["pauseBreathingFreq"]


def find_latest_song(directory="music_generated") -> Optional[Path]:
    music_dir = Path(directory)
    if not music_dir.exists() or not music_dir.is_dir():
        return None
    wav_files = list(music_dir.glob("*.wav"))
    if not wav_files:
        return None
    return max(wav_files, key=lambda p: p.stat().st_mtime)


class HardwarePlayer:
    def __init__(self):
        self.state = "STOPPED"
        self.player: Optional[AudioPlayer] = None
        self.latest_song: Optional[Path] = find_latest_song()
        self.led_pwm = None
        self.breathing_thread: Optional[threading.Thread] = None
        self.stop_breathing = threading.Event()
        self.lock = threading.Lock()
        self.stop_polling = threading.Event()

        logger.info("Hardware Player initialized. State: STOPPED")
        if self.latest_song:
            logger.info(f"Found latest song: {self.latest_song.name}")
        else:
            logger.warning("No song found in 'music_generated' directory.")

        if IS_PI:
            self._setup_gpio()

    def _setup_gpio(self):
        try:
            # Clean up on start to prevent warnings
            GPIO.setwarnings(False)
            GPIO.cleanup()
            time.sleep(0.1)

            GPIO.setmode(GPIO.BCM)
            GPIO.setup(LED_PIN, GPIO.OUT)
            self.led_pwm = GPIO.PWM(LED_PIN, 100)
            self.led_pwm.start(0)

            GPIO.setup(PLAY_PAUSE_BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            GPIO.setup(STOP_BTN_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
            
            # Start the new polling thread instead of using event detection
            polling_thread = threading.Thread(target=self._poll_buttons, daemon=True)
            polling_thread.start()
            
            logger.info("GPIO pins set up and polling started.")
        except Exception as e:
            logger.error(f"Failed to set up GPIO: {e}")
            global IS_PI
            IS_PI = False
            
    def _poll_buttons(self):
        """Runs in a background thread to check for button presses."""
        last_play_state = GPIO.HIGH
        last_stop_state = GPIO.HIGH
        
        while not self.stop_polling.is_set():
            play_state = GPIO.input(PLAY_PAUSE_BTN_PIN)
            stop_state = GPIO.input(STOP_BTN_PIN)
            
            # Detect a falling edge (from HIGH to LOW)
            if play_state == GPIO.LOW and last_play_state == GPIO.HIGH:
                self.handle_toggle_play_pause()
            
            if stop_state == GPIO.LOW and last_stop_state == GPIO.HIGH:
                self.handle_stop()
            
            last_play_state = play_state
            last_stop_state = stop_state
            time.sleep(BTN_DEBOUNCE_TIME)

    def _update_led(self):
        if not IS_PI or not self.led_pwm:
            if self.state == "PLAYING": logger.info("[LED] ON (Solid)")
            elif self.state == "PAUSED": logger.info("[LED] ON (Breathing)")
            else: logger.info("[LED] OFF")
            return
        
        self.stop_breathing.set()
        if self.breathing_thread and self.breathing_thread.is_alive():
            self.breathing_thread.join()

        if self.state == "PLAYING":
            self.led_pwm.ChangeDutyCycle(MAX_LED_BRIGHTNESS)
        elif self.state == "STOPPED":
            self.led_pwm.ChangeDutyCycle(0)
        elif self.state == "PAUSED":
            self.stop_breathing.clear()
            self.breathing_thread = threading.Thread(target=self._breathe_led, daemon=True)
            self.breathing_thread.start()

    def _breathe_led(self):
        """Runs in a thread to create a breathing effect for the LED."""
        if not self.led_pwm:
            return
        pause_time = PAUSE_BREATHING_FREQ
        while not self.stop_breathing.is_set():
            for duty_cycle in range(0, MAX_LED_BRIGHTNESS + 1, 5):
                if self.stop_breathing.is_set(): break
                self.led_pwm.ChangeDutyCycle(duty_cycle)
                time.sleep(pause_time)
            for duty_cycle in range(MAX_LED_BRIGHTNESS, -1, -5):
                if self.stop_breathing.is_set(): break
                self.led_pwm.ChangeDutyCycle(duty_cycle)
                time.sleep(pause_time)

    def handle_toggle_play_pause(self):
        with self.lock:
            logger.info(f"'Play/Pause' triggered. Current state: {self.state}")
            if self.state == "STOPPED":
                self.latest_song = find_latest_song()
                if self.latest_song:
                    self.player = AudioPlayer(self.latest_song, loop_by_default=True)
                    self.player.play()
                    self.state = "PLAYING"
                else:
                    logger.error("No song file found to play.")
            elif self.state == "PLAYING":
                if self.player:
                    self.player.pause()
                    self.state = "PAUSED"
            elif self.state == "PAUSED":
                if self.player:
                    self.player.resume()
                    self.state = "PLAYING"
        self._update_led()
        self._print_status()

    def handle_stop(self):
        with self.lock:
            logger.info(f"'Stop' triggered. Current state: {self.state}")
            if self.state in ["PLAYING", "PAUSED"]:
                if self.player:
                    self.player.stop()
                    self.player = None
                self.state = "STOPPED"
        self._update_led()
        self._print_status()
    
    def listen_for_input(self, daemon_mode=False):
        """
        Listens for keyboard input if not in daemon mode, otherwise just waits.
        """
        if daemon_mode:
            logger.info("Running in daemon mode. Listening for GPIO button presses...")
            # In daemon mode, the GPIO polling is running in the background.
            # This loop just keeps the main script alive indefinitely.
            while True:
                time.sleep(1)
        else:
            logger.info("Running in interactive mode. Listening for keyboard commands and GPIO.")
            # This loop listens for keyboard commands in the foreground.
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
        
        # This cleanup will be called when the loop is broken (e.g., by 'q' or Ctrl+C)
        self.cleanup()

    def _print_status(self):
        song_name = self.latest_song.name if self.latest_song else "None"
        print("\n" + "="*20 + " PLAYER STATUS " + "="*20)
        print(f"  State: {self.state}")
        print(f"  Song:  {song_name}")
        print("="*55)
        print("Controls: [P] Play/Pause | [S] Stop | [Q] Quit")

    def cleanup(self):
        logger.warning("Cleaning up player...")
        self.stop_polling.set()
        if self.player:
            self.player.stop()
        if IS_PI:
            self.stop_breathing.set()
            if self.breathing_thread and self.breathing_thread.is_alive():
                self.breathing_thread.join()
            if self.led_pwm:
                self.led_pwm.stop()
            GPIO.cleanup()
        logger.info("Cleanup complete.")
