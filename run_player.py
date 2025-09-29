# run_player.py

from loguru import logger
from lib.hardware_player import HardwarePlayer

def setup_logger():
    """Configures a simple logger for the player service."""
    log_file_path = "player_service.log"
    logger.remove()  # Remove default handler
    # Console logger
    logger.add(
        lambda msg: print(msg, end=""),
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    # File logger for debugging the service
    logger.add(
        log_file_path,
        rotation="10 MB",
        retention="7 days",
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
        level="DEBUG",
        encoding="utf-8"
    )
    logger.info(f"Player service logger initialized. Logging to console and '{log_file_path}'")

def main():
    """
    Initializes and runs the hardware player, listening for user input.
    """
    setup_logger()
    logger.info("--- Starting World Theme Music Player Service ---")
    
    player = HardwarePlayer()
    
    # This function will block and listen for keyboard/GPIO input until quit.
    player.listen_for_input()
    
    logger.info("--- Player Service Shutting Down ---")

if __name__ == "__main__":
    main()