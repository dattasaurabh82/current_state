import json
import os
from datetime import datetime
import argparse
from pathlib import Path
from typing import Optional

# Import all your project modules
import news_fetcher
import llm_analyzer
import music_generator
import music_post_processor
from player import AudioPlayer

# --- Core Action Functions ---
def generate_new_song(args: argparse.Namespace) -> Optional[Path]:
    """Encapsulates the entire news-to-music generation pipeline."""
    print("\n>>> STARTING NEW SONG GENERATION PIPELINE <<<")
    # 1. Load Data
    all_regional_data = None
    if args.local_file:
        print(f"Loading news from local file: {args.local_file}")
        try:
            with open(args.local_file, "r", encoding="utf-8") as f:
                all_regional_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: Local file not found at '{args.local_file}'")
            return None
    else:
        today_str = datetime.now().strftime("%Y-%m-%d")
        cache_filename = f"news_data_{today_str}.json"
        if os.path.exists(cache_filename) and not args.fetch:
            print(f"Loading news from today's cache file: {cache_filename}")
            with open(cache_filename, "r", encoding="utf-8") as f:
                all_regional_data = json.load(f)
        elif args.fetch:
            print(f"Fetching live data from API...")
            config = load_regions_config()
            if not config:
                return None
            all_regional_data = {}
            for name, data in config["regions"].items():
                if args.verbose:
                    print(
                        f"  -> Fetching for Region: {name} (Language: {data['language'].upper()})"
                    )
                articles = news_fetcher.fetch_news_for_language(data["language"])
                all_regional_data[name] = {
                    "language": data["language"],
                    "articles": articles,
                }
            with open(cache_filename, "w", encoding="utf-8") as f:
                json.dump(all_regional_data, f, ensure_ascii=False, indent=4)
        else:
            print(
                "No local file specified and no cache file found. Use --fetch True to get new data."
            )
            return None

    # 2. Analyze and Generate Prompt
    all_articles = [
        art for reg in all_regional_data.values() for art in reg.get("articles", [])
    ]
    if not all_articles:
        print("No articles found to analyze.")
        return None

    music_prompt, _ = llm_analyzer.generate_music_prompt_from_news(all_articles)
    if not music_prompt:
        print("Failed to generate music prompt.")
        return None

    # 3. Generate Music
    if not args.generate:
        print("\nMusic generation skipped by command-line argument.")
        return None  # Return None as no file was generated

    audio_file_path = music_generator.generate_and_download_music(music_prompt)
    if not audio_file_path:
        print("Failed to generate music file.")
        return None

    # 4. Post-Process Music
    if args.post_process:
        music_post_processor.process_and_replace(audio_file_path)

    print("\n>>> PIPELINE COMPLETE: New song is ready. <<<")
    return audio_file_path


def display_menu(state: str, latest_song: Optional[Path], player: Optional[AudioPlayer]):
    """Displays a dynamic command menu based on the player state."""
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
        print(f"Error: {filename} not found.")
        return None


# --- Main Application ---
def main():
    parser = argparse.ArgumentParser(
        description="Generate and play the world's daily theme song."
    )
    parser.add_argument(
        "--mode",
        choices=["auto", "interactive"],
        default="auto",
        help="Application mode.",
    )
    parser.add_argument(
        "--fetch",
        default=False,
        type=lambda x: x.lower() == "true",
        help="Force fetch new news data.",
    )
    parser.add_argument(
        "--local-file", type=str, default=None, help="Use a local news JSON file."
    )
    parser.add_argument(
        "--verbose",
        default=False,
        type=lambda x: x.lower() == "true",
        help="Enable detailed logging.",
    )
    parser.add_argument(
        "--generate",
        default=True,
        type=lambda x: x.lower() == "true",
        help="Enable music generation.",
    )
    parser.add_argument(
        "--post-process",
        default=True,
        type=lambda x: x.lower() == "true",
        help="Enable post-processing.",
    )
    parser.add_argument(
        "--play",
        default=True,
        type=lambda x: x.lower() == "true",
        help="Enable auto-playback (in auto mode).",
    )
    args = parser.parse_args()

    # State Variables
    latest_audio_file_path: Optional[Path] = None
    player_instance: Optional[AudioPlayer] = None
    player_state = "stopped"

    # --- Initial Song Generation ---
    latest_audio_file_path = generate_new_song(args)

    # --- Mode-Based Action ---
    if args.mode == "auto":
        if latest_audio_file_path and args.play:
            print("\n--- AUTO MODE: Starting playback ---")
            player_instance = AudioPlayer(latest_audio_file_path)
            player_instance.play()
            player_instance.wait()
            print("--- AUTO MODE: Playback finished. Exiting. ---")
        elif not latest_audio_file_path:
            print("--- AUTO MODE: Song generation failed. Exiting. ---")
        else:  # Song was generated but --play was False
            print(
                "--- AUTO MODE: Song generated successfully. Exiting without playback. ---"
            )
        return

    # --- Interactive Loop ---
    elif args.mode == "interactive":
        while True:
            if (
                player_state == "playing"
                and player_instance
                and not player_instance.is_playing
            ):
                # This check handles when a non-looping song finishes naturally
                if not player_instance.loop:
                    if latest_audio_file_path is not None:
                        print(f"\n'{latest_audio_file_path.name}' finished playing.")
                    else:
                        print("\nSong finished playing.")
                    player_state = "stopped"

            display_menu(player_state, latest_audio_file_path, player_instance)
            command = input("Enter command > ").lower().strip()

            if command == "q":
                if player_instance:
                    player_instance.stop()
                print("Exiting.")
                break
            elif command == "n":
                if player_instance:
                    player_instance.stop()
                player_state = "stopped"
                player_instance = None
                latest_audio_file_path = generate_new_song(args)
            elif command == "p":
                if not latest_audio_file_path:
                    print("No music file available. Generate one with (n).")
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
                    player_instance = None # Clear the instance after stopping
            elif command == "l":
                if player_instance and player_state in ["playing", "paused"]:
                    player_instance.toggle_loop()
                else:
                    print("Cannot toggle loop. No song is currently active.")
            else:
                print("Invalid command.")


if __name__ == "__main__":
    main()