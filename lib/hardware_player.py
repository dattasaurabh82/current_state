# lib/hardware_player.py

import threading
import time
from pathlib import Path
from typing import Optional
from loguru import logger
from lib.player import AudioPlayer
from lib.settings import load_settings
from lib.radar_controller import RadarController

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
RADAR_LED_PIN = settings["outputPins"]["radarStateLEDPin"]
PLAY_PAUSE_BTN_PIN = settings["inputPins"]["playPauseBtnPin"]
STOP_BTN_PIN = settings["inputPins"]["stopBtnPin"]

# Hardware Features (from settings.json)
BTN_DEBOUNCE_TIME = settings["hwFeatures"]["btnDebounceTimeMs"]
MAX_LED_BRIGHTNESS = settings["hwFeatures"]["maxLEDBrightness"]
PAUSE_BREATHING_FREQ = settings["hwFeatures"]["pauseBreathingFreq"]
MOTION_PLAYBACK_DURATION = settings["hwFeatures"]["motionTriggeredPlaybackDurationSec"]
COOLDOWN_AFTER_USER_ACTION = settings["hwFeatures"]["cooldownAfterUserActionSec"]


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
        
        # Radar-related state
        self.radar_controller: Optional[RadarController] = None
        self.radar_led_pwm = None
        self.initiated_by: Optional[str] = None  # 'user' | 'radar' | None
        self.radar_playback_active = False  # When True, ignore motion for triggering
        self.auto_stop_timer: Optional[threading.Timer] = None
        self.auto_stop_start_time: float = 0  # Track when timer started
        self.last_user_action_time: float = 0

        logger.info("Hardware Player initialized. State: STOPPED")
        if self.latest_song:
            logger.info(f"Found latest song: {self.latest_song.name}")
        else:
            logger.warning("No song found in 'music_generated' directory.")

        if IS_PI:
            self._setup_gpio()
            self._setup_radar()

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
            
            # Start the button polling thread
            polling_thread = threading.Thread(target=self._poll_buttons, daemon=True)
            polling_thread.start()
            
            logger.info("GPIO pins set up and polling started.")
        except Exception as e:
            logger.error(f"Failed to set up GPIO: {e}")
            global IS_PI
            IS_PI = False
    
    def _setup_radar(self):
        """Initialize radar controller and radar LED if switch is enabled."""
        try:
            self.radar_controller = RadarController()
            
            if self.radar_controller.is_switch_enabled() and self.radar_controller.enabled:
                # Setup radar LED (GPIO23)
                GPIO.setup(RADAR_LED_PIN, GPIO.OUT)
                self.radar_led_pwm = GPIO.PWM(RADAR_LED_PIN, 100)
                self.radar_led_pwm.start(0)
                
                # Start radar polling thread
                radar_thread = threading.Thread(target=self._poll_radar, daemon=True)
                radar_thread.start()
                
                logger.info(f"Radar enabled. Listening on GPIO{self.radar_controller.radar_pin}")
            elif self.radar_controller.is_switch_enabled() and not self.radar_controller.enabled:
                logger.info("Radar switch is ON but radar detection is disabled (model not supported).")
            else:
                logger.info("Radar switch is OFF. Radar detection disabled.")
        except Exception as e:
            logger.error(f"Failed to set up radar: {e}")
            self.radar_controller = None
            
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
    
    def _get_timer_remaining(self) -> int:
        """Get seconds remaining on auto-stop timer."""
        if not self.auto_stop_timer or self.auto_stop_start_time == 0:
            return 0
        elapsed = time.time() - self.auto_stop_start_time
        remaining = MOTION_PLAYBACK_DURATION - elapsed
        return max(0, int(remaining))
    
    def _get_cooldown_remaining(self) -> int:
        """Get seconds remaining on cooldown."""
        if self.last_user_action_time == 0:
            return 0
        elapsed = time.time() - self.last_user_action_time
        remaining = COOLDOWN_AFTER_USER_ACTION - elapsed
        return max(0, int(remaining))
    
    def _poll_radar(self):
        """Runs in a background thread to check for radar motion."""
        logger.info("Radar polling thread started.")
        
        while not self.stop_polling.is_set():
            # Check if radar switch is still enabled
            if not self.radar_controller or not self.radar_controller.is_switch_enabled():
                time.sleep(0.5)
                continue
            
            # Check for motion edges (for LED and potential trigger)
            motion_started, motion_stopped = self.radar_controller.check_motion_state()
            
            # Update radar LED based on actual motion state
            if motion_started:
                self._update_radar_led(True)
                logger.info("🏃🏻 Motion DETECTED!")
                
                # Check if we should trigger playback
                cooldown_remaining = self._get_cooldown_remaining()
                if cooldown_remaining > 0:
                    logger.info(f"   ↳ Ignoring trigger: Cooldown active ({cooldown_remaining}s remaining)")
                elif self.radar_playback_active:
                    timer_remaining = self._get_timer_remaining()
                    logger.info(f"   ↳ Ignoring trigger: Playback active (auto-stop in {timer_remaining}s)")
                else:
                    # Trigger playback
                    self.handle_radar_motion()
            
            if motion_stopped:
                self._update_radar_led(False)
                logger.info("Motion stopped.")
            
            time.sleep(0.05)  # 50ms polling
        
        logger.info("Radar polling thread stopped.")

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
    
    def _update_radar_led(self, on: bool):
        """Update radar LED state based on motion detection."""
        if self.radar_led_pwm:
            if on:
                self.radar_led_pwm.ChangeDutyCycle(MAX_LED_BRIGHTNESS)
            else:
                self.radar_led_pwm.ChangeDutyCycle(0)

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
    
    def _cancel_auto_stop_timer(self):
        """Cancel the auto-stop timer if running."""
        if self.auto_stop_timer:
            self.auto_stop_timer.cancel()
            self.auto_stop_timer = None
            self.auto_stop_start_time = 0
    
    def _start_auto_stop_timer(self):
        """Start the auto-stop timer."""
        self._cancel_auto_stop_timer()
        self.auto_stop_start_time = time.time()
        self.auto_stop_timer = threading.Timer(
            MOTION_PLAYBACK_DURATION, 
            self._auto_stop_callback
        )
        self.auto_stop_timer.daemon = True
        self.auto_stop_timer.start()
        logger.info(f"Auto-stop timer started: {MOTION_PLAYBACK_DURATION}s")
    
    def _auto_stop_callback(self):
        """Called when auto-stop timer expires."""
        with self.lock:
            logger.warning("⏱️ Auto-stop timer expired. Stopping playback.")
            if self.player:
                self.player.stop()
                self.player = None
            self.state = "STOPPED"
            self.initiated_by = None
            self.radar_playback_active = False
            self.auto_stop_start_time = 0
        self._update_led()
        self._print_status()

    def handle_toggle_play_pause(self):
        with self.lock:
            logger.info(f"'Play/Pause' triggered. Current state: {self.state}")
            
            # Record user action time for cooldown
            self.last_user_action_time = time.time()
            
            # User took control - cancel auto-stop and clear radar state
            self._cancel_auto_stop_timer()
            self.radar_playback_active = False
            self.initiated_by = 'user'
            
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
                    logger.info(f"Cooldown started: {COOLDOWN_AFTER_USER_ACTION}s")
            elif self.state == "PAUSED":
                if self.player:
                    self.player.resume()
                    self.state = "PLAYING"
        self._update_led()

    def handle_stop(self):
        with self.lock:
            logger.info(f"'Stop' triggered. Current state: {self.state}")
            
            # Record user action time for cooldown
            self.last_user_action_time = time.time()
            
            # User took control - cancel auto-stop and clear radar state
            self._cancel_auto_stop_timer()
            self.radar_playback_active = False
            self.initiated_by = None
            
            if self.state in ["PLAYING", "PAUSED"]:
                if self.player:
                    self.player.stop()
                    self.player = None
                self.state = "STOPPED"
                logger.info(f"Cooldown started: {COOLDOWN_AFTER_USER_ACTION}s")
        self._update_led()
    
    def handle_radar_motion(self):
        """Handle motion detected by radar - trigger playback."""
        with self.lock:
            if self.state == "STOPPED":
                self.latest_song = find_latest_song()
                if self.latest_song:
                    self.player = AudioPlayer(self.latest_song, loop_by_default=True)
                    self.player.play()
                    self.state = "PLAYING"
                    self.initiated_by = 'radar'
                    self.radar_playback_active = True
                    self._start_auto_stop_timer()
                    logger.success("Radar triggered playback started.")
                else:
                    logger.error("No song file found to play.")
            elif self.state == "PAUSED":
                if self.player:
                    self.player.resume()
                    self.state = "PLAYING"
                    self.initiated_by = 'radar'
                    self.radar_playback_active = True
                    self._start_auto_stop_timer()
                    logger.success("Radar triggered playback resumed.")
        
        self._update_led()
    
    def listen_for_input(self, daemon_mode=False):
        """
        Listens for keyboard input if not in daemon mode, otherwise just waits.
        """
        if daemon_mode:
            logger.info("Running in daemon mode. Listening for GPIO button presses...")
            if self.radar_controller and self.radar_controller.is_switch_enabled() and self.radar_controller.enabled:
                logger.info("Radar detection is active.")
            # In daemon mode, the GPIO polling is running in the background.
            # This loop just keeps the main script alive indefinitely.
            while True:
                time.sleep(1)
        else:
            logger.info("Running in interactive mode. Listening for keyboard commands and GPIO.")
            if self.radar_controller and self.radar_controller.is_switch_enabled() and self.radar_controller.enabled:
                logger.info("Radar detection is active.")
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
        radar_status = "ON" if (self.radar_controller and self.radar_controller.is_switch_enabled() and self.radar_controller.enabled) else "OFF"
        timer_info = ""
        if self.radar_playback_active:
            timer_info = f" | Timer: {self._get_timer_remaining()}s"
        print("\n" + "="*20 + " PLAYER STATUS " + "="*20)
        print(f"  State: {self.state}")
        print(f"  Song:  {song_name}")
        print(f"  Radar: {radar_status} | Initiated by: {self.initiated_by or 'N/A'}{timer_info}")
        print("="*55)
        print("Controls: [P] Play/Pause | [S] Stop | [Q] Quit")

    def cleanup(self):
        logger.warning("Cleaning up player...")
        self.stop_polling.set()
        self._cancel_auto_stop_timer()
        if self.player:
            self.player.stop()
        if IS_PI:
            self.stop_breathing.set()
            if self.breathing_thread and self.breathing_thread.is_alive():
                self.breathing_thread.join()
            if self.led_pwm:
                self.led_pwm.stop()
            if self.radar_led_pwm:
                self.radar_led_pwm.stop()
            GPIO.cleanup()
        logger.info("Cleanup complete.")
