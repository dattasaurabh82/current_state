# lib/hardware_player.py

import threading
from pathlib import Path
from typing import Optional

from loguru import logger
from pynput import keyboard

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
        
        # A lock to prevent race conditions from multiple key presses
        self.lock = threading.Lock()

        logger.info("Hardware Player initialized. State: STOPPED")
        if self.latest_song:
            logger.info(f"Found latest song: {self.latest_song.name}")
        else:
            logger.warning("No song found in 'music_generated' directory.")

    def _update_led(self):
        """Placeholder for LED control logic."""
        # We will implement this in the next step
        if self.state == "PLAYING":
            logger.info("[LED] ON (Solid)")
        elif self.state == "PAUSED":
            logger.info("[LED] ON (Breathing)")
        elif self.state == "STOPPED":
            logger.info("[LED] OFF")

    def handle_press(self):
        """The core state machine for a single button press."""
        with self.lock:
            logger.info(f"Button pressed. Current state: {self.state}")
            
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
                    logger.info("Stopping playback.")
                    self.player.stop()
                    self.player = None
                    self.state = "STOPPED"
        
        self._update_led()
        self._print_status()

    def _on_key_press(self, key):
        """Callback for pynput keyboard listener."""
        try:
            # Check for spacebar press
            if key == keyboard.Key.space:
                self.handle_press()
            # Check for 'q' key to quit
            elif key.char == 'q':
                logger.warning("'q' pressed. Exiting listener.")
                self.cleanup()
                return False  # Stop the listener
        except AttributeError:
            pass # Ignore other key presses

    def listen_for_input(self):
        """Starts the keyboard listener and waits for it to exit."""
        logger.info("Starting keyboard listener...")
        logger.info("Press [SPACE] to toggle play/pause/stop.")
        logger.info("Press [Q] to quit.")
        
        self._print_status()

        # The listener runs in its own thread
        listener = keyboard.Listener(on_press=self._on_key_press)
        listener.start()
        listener.join() # Wait for the listener to stop (on 'q' press)

    def _print_status(self):
        """Prints the current status to the console."""
        song_name = self.latest_song.name if self.latest_song else "None"
        print("\n" + "="*20 + " PLAYER STATUS " + "="*20)
        print(f"  State: {self.state}")
        print(f"  Song:  {song_name}")
        print("="*55)
        print("Controls: [SPACE] to toggle, [Q] to quit.")


    def cleanup(self):
        """Stops all processes gracefully."""
        logger.warning("Cleaning up player...")
        if self.player:
            self.player.stop()
        # GPIO cleanup will go here in the next step
        logger.info("Cleanup complete. Exiting.")