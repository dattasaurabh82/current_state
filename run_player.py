import threading
import time
from pathlib import Path

import argparse

from loguru import logger
from lib.hardware_player import HardwarePlayer
from lib.player import AudioPlayer # We need this for the keep-alive player (Silent audio file occasional playback)

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

# def keep_audio_alive(stop_event: threading.Event):
#     """
#     Plays a silent WAV file on a continuous loop to prevent speakers from sleeping.
#     """
#     silent_file = Path("silent.wav")
#     if not silent_file.exists():
#         logger.error("'silent.wav' not found! Cannot run keep-alive thread.")
#         return

#     # Add a small delay to de-conflict with main player initialization
#     time.sleep(0.5)

#     silent_player = None
#     try:
#         logger.info("Starting audio keep-alive player.")
#         #FIX: Increase buffer and block sizes for stability ---
#         silent_player = AudioPlayer(
#             silent_file,
#             loop_by_default=True,
#             buffer_size=40,  # Increased from default 20
#             blocksize=4096   # Increased from default 2048
#         )
#         silent_player.play()
        
#         # This thread will now simply wait until the main app signals it to stop.
#         stop_event.wait()

#     except Exception as e:
#         logger.error(f"Error in keep-alive thread: {e}")
#     finally:
#         if silent_player:
#             silent_player.stop()
#         logger.warning("Audio keep-alive thread stopped.")


def keep_audio_alive(stop_event: threading.Event):
    """
    Plays a silent WAV file on a continuous loop to prevent speakers from sleeping.
    """
    silent_file = Path("silent.wav")
    if not silent_file.exists():
        logger.error("'silent.wav' not found! Cannot run keep-alive thread.")
        return

    # Add a small delay to de-conflict with main player initialization
    time.sleep(0.5)

    silent_player = None
    try:
        logger.info("Starting audio keep-alive player.")
        # --- FIX: Preload the entire silent file into RAM for stability ---
        silent_player = AudioPlayer(
            silent_file,
            loop_by_default=True,
            preload=True  # Use the new feature
        )
        silent_player.play()
        time.sleep(1)
        silent_player.stop()
        time.sleep(5)
        
        # This thread will now simply wait until the main app signals it to stop.
        stop_event.wait()

    except Exception as e:
        logger.error(f"Error in keep-alive thread: {e}")
    finally:
        if silent_player:
            silent_player.stop()
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
            target=keep_audio_alive, args=(stop_keep_alive,), daemon=True
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