# main.py

import time
from pathlib import Path
from colorama import Fore, Style, init
from loguru import logger

# Import our new class from the other file
from player import AudioPlayer

# --- Configuration --- #
AUDIO_FILE = Path("music_test/test_audio.wav")

def setup_logger():
    """Configures the logger for clean output."""
    init(autoreset=True)
    logger.remove()
    logger.add(
        lambda msg: print(msg, end=""),
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

def main():
    """
    Example of how to use the AudioPlayer class.
    """
    setup_logger()
    logger.info("Starting audio player demonstration...")

    try:
        # 1. Create an instance of the player.
        # We don't specify a device, so it uses the system default.
        player = AudioPlayer(AUDIO_FILE)

        # 2. Start playback (this is non-blocking).
        player.play()

        # 3. The main script can do other things while the audio plays.
        logger.info("Player started. The main script can now doing other work...")
        # while player.is_playing:
        #     print(f"{Fore.CYAN}    ...main thread is alive, music is playing...{Style.RESET_ALL}")
        #     time.sleep(2)

        # 4. Optionally, wait for the track to finish naturally.
        # If the loop above finishes, it means the song ended.
        logger.info("Playback has finished naturally.")

    except FileNotFoundError as e:
        logger.error(e)
    except KeyboardInterrupt:
        logger.warning("\nInterrupted by user. Stopping player.")
        # Ensure the player is stopped cleanly on Ctrl+C
        if 'player' in locals() and player.is_playing:
            player.stop()
    except Exception as e:
        logger.exception(f"An unexpected error occurred in main: {e}")

if __name__ == "__main__":
    main()