# lib/hardware_player.py

from pathlib import Path
from typing import Optional
from loguru import logger
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
    Manages player state and audio playback via simple text commands.
    """

    def __init__(self):
        self.state = "STOPPED"  # Can be STOPPED, PLAYING, PAUSED
        self.player: Optional[AudioPlayer] = None
        self.latest_song: Optional[Path] = find_latest_song()

        logger.info("Hardware Player initialized. State: STOPPED")
        if self.latest_song:
            logger.info(f"Found latest song: {self.latest_song.name}")
        else:
            logger.warning("No song found in 'music_generated' directory.")

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
        logger.info(f"'Play/Pause' command received. Current state: {self.state}")
        
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

    def handle_stop(self):
        """Handles the Stop logic."""
        logger.info(f"'Stop' command received. Current state: {self.state}")
        if self.state in ["PLAYING", "PAUSED"]:
            if self.player:
                logger.info("Stopping playback.")
                self.player.stop()
                self.player = None
            self.state = "STOPPED"
    
        self._update_led()

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
        logger.info("Cleanup complete.")