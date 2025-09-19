import json
import os
from datetime import datetime
import argparse
from pathlib import Path
from typing import Optional
import signal
from loguru import logger

from lib import (
    news_fetcher,
    llm_analyzer,
    music_generator,
    music_post_processor,
)
from lib.player import AudioPlayer

# Global player instance for the signal handler
player_instance: Optional[AudioPlayer] = None

def setup_logger():
    """Configures the logger for clean, colored output."""
    logger.remove()  # Remove default handler
    logger.add(
        lambda msg: print(msg, end=""),
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )

def handle_exit(sig, frame):
    """Gracefully handle Ctrl+C."""
    logger.warning("\nEXIT SIGNAL RECEIVED")
    music_generator.cancel_current_prediction()
    global player_instance
    if player_instance and player_instance.is_playing:
        logger.info("Stopping audio playback...")
        player_instance.stop()
    logger.info("Exiting.")
    exit(0)

def generate_new_song(args: argparse.Namespace) -> Optional[Path]:
    """Encapsulates the entire news-to-music generation pipeline."""
    logger.info("STARTING NEW SONG GENERATION PIPELINE")
    all_regional_data = None
    if args.local_file:
        logger.info(f"Loading news from local file: {args.local_file}")
        try:
            with open(args.local_file, "r", encoding="utf-8") as f:
                all_regional_data = json.load(f)
        except FileNotFoundError:
            logger.error(f"Local file not found at '{args.local_file}'")
            return None
    else:
        today_str = datetime.now().strftime("%Y-%m-%d")
        cache_filename = f"news_data_{today_str}.json"
        if os.path.exists(cache_filename) and not args.fetch:
            logger.info(f"Loading news from today's cache file: {cache_filename}")
            with open(cache_filename, "r", encoding="utf-8") as f:
                all_regional_data = json.load(f)
        elif args.fetch:
            logger.info("FETCHING LIVE NEWS DATA FROM API...")
            config = load_regions_config()
            if not config:
                return None
            all_regional_data = {}
            for name, data in config["regions"].items():
                if args.verbose:
                    logger.debug(f"  -> Fetching for Region: {name} (Language: {data['language'].upper()})")
                articles = news_fetcher.fetch_news_for_language(data["language"])
                all_regional_data[name] = {
                    "language": data["language"],
                    "articles": articles,
                }
            with open(cache_filename, "w", encoding="utf-8") as f:
                json.dump(all_regional_data, f, ensure_ascii=False, indent=4)
        else:
            logger.warning("No local file specified and no cache file found. Use --fetch True to get new data.")
            return None

    all_articles = [art for reg in all_regional_data.values() for art in reg.get("articles", [])]
    if not all_articles:
        logger.warning("No articles found to analyze.")
        return None

    music_prompt, _ = llm_analyzer.generate_music_prompt_from_news(all_articles)
    if not music_prompt:
        logger.error("Failed to generate music prompt.")
        return None

    if not args.generate:
        logger.info("Music generation skipped by command-line argument.")
        return None

    audio_file_path = music_generator.generate_and_download_music(music_prompt)
    if not audio_file_path:
        logger.error("Failed to generate music file.")
        return None

    if args.post_process:
        music_post_processor.process_and_replace(audio_file_path)

    logger.success("PIPELINE COMPLETE: New song is ready.")
    return audio_file_path

def display_menu(state: str, latest_song: Optional[Path], player: Optional[AudioPlayer]):
    """Displays a dynamic command menu based on the player state."""
    # This function is UI, so we keep using print()
    print("\n" + "=" * 40)
    loop_status = ""
    if player:
        loop_status = "ON" if player.loop else "OFF"

    if not latest_song:
        print("No music file available.")
        print("(N)ew Song | (Q)uit")
    elif state == "stopped":
        print(f"Ready to play: {latest_song.name}")
        print("(P)lay | (N)ew Song | (Q)uit")
    elif state == "playing":
        print(f"Now Playing: {latest_song.name} [Loop: {loop_status}]")
        print("(P)ause | (S)top | (L)oop Toggle | (N)ew Song | (Q)uit")
    elif state == "paused":
        print(f"Paused: {latest_song.name} [Loop: {loop_status}]")
        print("(P)resume | (S)top | (L)oop Toggle | (N)ew Song | (Q)uit")
    print("=" * 40)


def load_regions_config(filename="config.json"):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        logger.error(f"Config file '{filename}' not found.")
        return None


def find_latest_song(directory="music_generated") -> Optional[Path]:
    """Finds the most recently created .wav file in a directory."""
    music_dir = Path(directory)
    if not music_dir.exists():
        logger.error(f"Music directory '{directory}' not found.")
        return None
    
    wav_files = list(music_dir.glob("*.wav"))
    if not wav_files:
        logger.warning(f"No .wav files found in '{directory}'.")
        return None
        
    latest_file = max(wav_files, key=lambda p: p.stat().st_mtime)
    logger.info(f"Found latest song: {latest_file.name}")
    return latest_file


# Main Application
def main():
    global player_instance
    setup_logger() # Configure the logger at the start
    signal.signal(signal.SIGINT, handle_exit)
    
    parser = argparse.ArgumentParser(description="Generate and play the world's daily theme song.")
    parser.add_argument("--mode", choices=["auto", "interactive"], default="auto", help="Application mode.")
    parser.add_argument("--fetch", default=False, type=lambda x: x.lower() == "true", help="Force fetch new news data.")
    parser.add_argument("--local-file", type=str, default=None, help="Use a local news JSON file.")
    parser.add_argument("--verbose", default=False, type=lambda x: x.lower() == "true", help="Enable detailed logging.")
    parser.add_argument("--generate", default=True, type=lambda x: x.lower() == "true", help="Enable music generation.")
    parser.add_argument("--post-process", default=True, type=lambda x: x.lower() == "true", help="Enable post-processing.")
    parser.add_argument("--play", default=True, type=lambda x: x.lower() == "true", help="Enable auto-playback (in auto mode).")
    parser.add_argument("--play-latest", action='store_true', help="Skip generation and play the most recent song.")
    args = parser.parse_args()

    # State Variables
    latest_audio_file_path: Optional[Path] = None
    player_state = "stopped"

    if args.play_latest:
        args.mode = 'interactive'
        latest_audio_file_path = find_latest_song()
        if not latest_audio_file_path:
            logger.error("Could not find a song to play. Exiting.")
            return
    else:
        latest_audio_file_path = generate_new_song(args)

    if args.mode == "auto":
        if latest_audio_file_path and args.play:
            logger.info("AUTO MODE: Starting playback")
            player_instance = AudioPlayer(latest_audio_file_path, loop_by_default=True)
            player_instance.play()
            player_instance.wait()
            logger.info("AUTO MODE: Playback finished. Exiting.")
        elif not latest_audio_file_path:
            logger.error("AUTO MODE: Song generation failed. Exiting.")
        else:
            logger.info("AUTO MODE: Song generated successfully. Exiting without playback.")
        return

    elif args.mode == "interactive":
        while True:
            if player_state == "playing" and player_instance and not player_instance.is_playing:
                if not player_instance.loop:
                    logger.info(f"'{latest_audio_file_path.name}' finished playing.")
                    player_state = "stopped"
            
            display_menu(player_state, latest_audio_file_path, player_instance)
            command = input("Enter command > ").lower().strip()

            if command == "q":
                if player_instance:
                    player_instance.stop()
                logger.info("Exiting.")
                break
            elif command == "n":
                if player_instance:
                    player_instance.stop()
                player_state = "stopped"
                player_instance = None
                latest_audio_file_path = generate_new_song(args)
            elif command == "p":
                if not latest_audio_file_path:
                    logger.warning("No music file available. Generate one with (n).")
                    continue
                if player_state == "stopped":
                    player_instance = AudioPlayer(latest_audio_file_path)
                    player_instance.play()
                    player_state = "playing"
                elif player_state == "playing":
                    if player_instance:
                        player_instance.pause()
                    player_state = "paused"
                elif player_state == "paused":
                    if player_instance:
                        player_instance.resume()
                    player_state = "playing"
            elif command == "s":
                if player_state in ["playing", "paused"]:
                    if player_instance:
                        player_instance.stop()
                    player_state = "stopped"
                    player_instance = None
            elif command == "l":
                if player_instance and player_state in ["playing", "paused"]:
                    player_instance.toggle_loop()
                else:
                    logger.warning("Cannot toggle loop. No song is currently active.")
            else:
                logger.warning("Invalid command.")

if __name__ == "__main__":
    main()