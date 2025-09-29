# run_player.py

import threading
import time
from pathlib import Path

from loguru import logger
from lib.hardware_player import HardwarePlayer
from lib.player import AudioPlayer # We need this for the keep-alive player

def setup_logger():
    """Configures a simple logger for the player service."""
    log_file_path = "player_service.log"
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
    logger.info(f"Player service logger initialized. Logging to console and '{log_file_path}'")

def keep_audio_alive(stop_event: threading.Event):
    """
    Plays a silent WAV file every 10 seconds to prevent speakers from sleeping.
    """
    silent_file = Path("silent.wav")
    if not silent_file.exists():
        logger.error("'silent.wav' not found! Cannot run keep-alive thread.")
        return

    logger.info("Starting audio keep-alive thread.")
    while not stop_event.is_set():
        try:
            player = AudioPlayer(silent_file, loop_by_default=False)
            player.play()
            player.wait() # Wait for the 1-second silent file to finish
        except Exception as e:
            logger.error(f"Error in keep-alive thread: {e}")
        
        # Wait for 10 seconds before playing again, but check the stop event frequently
        for _ in range(100): # Check every 0.1 seconds
            if stop_event.is_set():
                break
            time.sleep(0.1)
    
    logger.warning("Audio keep-alive thread stopped.")


def main():
    """
    Initializes and runs the hardware player and the keep-alive thread.
    """
    setup_logger()
    logger.info("--- Starting World Theme Music Player Service ---")
    
    stop_keep_alive = threading.Event()
    player = HardwarePlayer()

    try:
        # --- Start the Keep-Alive Thread ---
        keep_alive_thread = threading.Thread(
            target=keep_audio_alive, args=(stop_keep_alive,), daemon=True
        )
        keep_alive_thread.start()

        # --- Start the Main Hardware Player ---
        player.listen_for_input() # This blocks until 'q' is pressed
    
    finally:
        # --- This code is GUARANTEED to run on exit ---
        logger.info("Main listener stopped. Shutting down all processes...")
        
        # 1. Stop the keep-alive thread
        stop_keep_alive.set()
        if 'keep_alive_thread' in locals() and keep_alive_thread.is_alive():
            keep_alive_thread.join()
        
        # 2. Clean up the player and GPIO
        player.cleanup()
        
        logger.info("--- Player Service Shut Down ---")


if __name__ == "__main__":
    main()