# lib/hardware_player.py

import threading
from pathlib import Path
from typing import Optional
import os
import time

from loguru import logger

# Use evdev for headless keyboard input
import evdev
from evdev import ecodes, InputDevice

from lib.player import AudioPlayer


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
    Manages player state, audio playback, and input from keyboard/GPIO.
    """

    def __init__(self):
        self.state = "STOPPED"  # Can be STOPPED, PLAYING, PAUSED
        self.player: Optional[AudioPlayer] = None
        self.latest_song: Optional[Path] = find_latest_song()
        self.keyboard_device: Optional[InputDevice] = None
        self.lock = threading.Lock()

        logger.info("Hardware Player initialized. State: STOPPED")
        if self.latest_song:
            logger.info(f"Found latest song: {self.latest_song.name}")
        else:
            logger.warning("No song found in 'music_generated' directory.")

        self._find_keyboard_device()

    def _find_keyboard_device(self):
        """Finds the first available keyboard device and adds debugging."""
        logger.info("Searching for input devices...")
        try:
            devices = [InputDevice(path) for path in evdev.list_devices()]
            if not devices:
                logger.error("No input devices found! Check /dev/input/")
                return

            logger.info("--- Available Devices ---")
            for device in devices:
                logger.info(f"Path: {device.path}, Name: {device.name}")
            logger.info("-------------------------")

            for device in devices:
                if "keyboard" in device.name.lower():
                    self.keyboard_device = device
                    logger.success(
                        f"SUCCESS: Found keyboard: {self.keyboard_device.name} at {self.keyboard_device.path}"
                    )
                    return

            logger.error("No device with 'keyboard' in its name was found.")

        except Exception as e:
            logger.error(f"An error occurred while searching for devices: {e}")
            logger.error(
                "This is likely a permissions issue. Did you run 'sudo usermod -a -G input $USER' and reboot?"
            )

    def _update_led(self):
        """Placeholder for LED control logic."""
        if self.state == "PLAYING":
            logger.info("[LED] ON (Solid)")
        elif self.state == "PAUSED":
            logger.info("[LED] ON (Breathing)")
        elif self.state == "STOPPED":
            logger.info("[LED] OFF")

    def handle_toggle_play_pause(self):
        """Handles the Play/Pause logic."""
        with self.lock:
            logger.info(f"'Play/Pause' pressed. Current state: {self.state}")

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

    def handle_stop(self):
        """Handles the Stop logic."""
        with self.lock:
            logger.info(f"'Stop' pressed. Current state: {self.state}")
            if self.state in ["PLAYING", "PAUSED"]:
                if self.player:
                    logger.info("Stopping playback.")
                    self.player.stop()
                    self.player = None
                self.state = "STOPPED"

        self._update_led()
        self._print_status()

    def listen_for_input(self):
        """Starts the keyboard listener and waits for events."""
        if not self.keyboard_device:
            logger.error("Cannot listen for input: No keyboard device.")
            return

        logger.info("Starting keyboard listener...")
        self._print_status()

        try:
            self.keyboard_device.grab()
            for event in self.keyboard_device.read_loop():
                if event.type == ecodes.EV_KEY and event.value == 1:  # Key down events
                    if event.code == ecodes.KEY_P:
                        self.handle_toggle_play_pause()
                    elif event.code == ecodes.KEY_S:
                        self.handle_stop()
                    elif event.code == ecodes.KEY_Q:
                        logger.warning("'Q' pressed. Exiting listener.")
                        break
        except Exception as e:
            logger.error(f"Error with keyboard listener: {e}")
            logger.error(
                "This is likely a permissions issue if the script was able to find the device."
            )
        finally:
            self.cleanup()

    def _print_status(self):
        """Prints the current status to the console."""
        song_name = self.latest_song.name if self.latest_song else "None"
        print("\n" + "=" * 20 + " PLAYER STATUS " + "=" * 20)
        print(f"  State: {self.state}")
        print(f"  Song:  {song_name}")
        print("=" * 55)
        print("Controls: [P] Play/Pause | [S] Stop | [Q] Quit")

    def cleanup(self):
        """Stops all processes gracefully."""
        logger.warning("Cleaning up player...")
        if self.player:
            self.player.stop()
        if self.keyboard_device:
            self.keyboard_device.ungrab()
        logger.info("Cleanup complete. Exiting.")
