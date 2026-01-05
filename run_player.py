import threading
import time
from pathlib import Path

import argparse

from loguru import logger
from lib.hardware_player import HardwarePlayer
from lib.player import AudioPlayer # We need this for the keep-alive player (Silent audio file occasional playback)

# Keep-alive interval in seconds (plays keep_audio_ch_active.wav when main audio is not playing)
KEEP_ALIVE_DELAY = 60

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


def keep_audio_alive(stop_event: threading.Event, hardware_player: HardwarePlayer):
    """
    Plays a silent WAV file at intervals to prevent speakers from sleeping.
    Only plays when main audio is not playing.
    """
    silent_file = Path("keep_audio_ch_active.wav")
    if not silent_file.exists():
        logger.error("'keep_audio_ch_active.wav' not found! Cannot run keep-alive thread.")
        return

    # Add a small delay to de-conflict with main player initialization
    time.sleep(0.5)
    logger.info(f"Starting audio keep-alive (interval: {KEEP_ALIVE_DELAY}s).")

    while not stop_event.is_set():
        try:
            # Only play if main audio is NOT playing
            if hardware_player.state != "PLAYING":
                silent_player = AudioPlayer(
                    silent_file,
                    loop_by_default=False,
                    preload=True
                )
                silent_player.play()
                # Wait for reader thread to finish (file ended), then let stream drain
                if silent_player._reader_thread:
                    silent_player._reader_thread.join()
                time.sleep(1.5)  # Let stream play the queued audio
                silent_player.stop()

            # Wait for delay (interruptable by stop_event)
            stop_event.wait(timeout=KEEP_ALIVE_DELAY)

        except Exception as e:
            logger.error(f"Error in keep-alive thread: {e}")
            break

    logger.warning("Audio keep-alive thread stopped.")


def main():
    """
    Initializes and runs the hardware player and the keep-alive thread.
    """
    parser = argparse.ArgumentParser(description="Run the hardware music player.")
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run in non-interactive daemon mode (no keyboard input)."
    )
    args = parser.parse_args()
    
    setup_logger()
    logger.info("--- Starting World Theme Music Player Service ---")
    
    stop_keep_alive = threading.Event()
    player = HardwarePlayer()

    try:
        # Start the Keep-Alive Thread
        keep_alive_thread = threading.Thread(
            target=keep_audio_alive, args=(stop_keep_alive, player), daemon=True
        )
        keep_alive_thread.start()

        # Start the Main Hardware Player
        # player.listen_for_input() # This blocks until 'q' is pressed
        
        # Start the Main Hardware Player, passing the daemon flag
        player.listen_for_input(daemon_mode=args.daemon)
    
    finally:
        logger.info("Main listener stopped. Shutting down all processes...")
        
        # 1. Stop the keep-alive thread
        stop_keep_alive.set()
        if 'keep_alive_thread' in locals() and keep_alive_thread.is_alive():
            keep_alive_thread.join(timeout=2.0)
        
        # 2. Clean up the main player and GPIO
        player.cleanup()
        
        logger.info("--- Player Service Shut Down ---")


if __name__ == "__main__":
    main()