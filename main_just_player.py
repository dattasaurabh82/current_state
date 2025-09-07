import time
from pathlib import Path
from colorama import Fore, Style, init
from loguru import logger

# Import our class from the other file
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

def play_test_audio():
    """Creates and starts an AudioPlayer instance."""
    try:
        logger.info("Creating audio player...")
        player = AudioPlayer(AUDIO_FILE)
        player.play()
        return player  # Return the created object
    except FileNotFoundError as e:
        logger.error(e)
        return None  # Return None if there was an error
    except Exception as e:
        logger.exception(f"An unexpected error occurred while starting playback: {e}")
        return None

def main():
    """
    Demonstrates how to use the AudioPlayer class.
    """
    setup_logger()
    logger.info("Starting audio player demonstration...")

    # 1. Capture the player object returned by the function.
    player = play_test_audio()

    # 2. Check if the player was created successfully before using it.
    if player:
        try:
            logger.info("Player started. Main thread is now free to do other work...")
            # 3. Now you can use the 'player' object here.
            while player.is_playing:
                # This loop just keeps the main script alive while music plays.
                time.sleep(1)
            logger.info("Playback finished naturally.")
        except KeyboardInterrupt:
            logger.warning("\nInterrupted by user. Stopping player.")
            player.stop()

if __name__ == "__main__":
    main()