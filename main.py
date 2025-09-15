import json
import os
from datetime import datetime
import time
import argparse

import news_fetcher
import llm_analyzer
import music_generator
# from player import AudioPlayer

def load_regions_config(filename="config.json"):
    try:
        with open(filename, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch news, analyze sentiment, and generate a music prompt, generate music"
    )
    parser.add_argument("--fetch", default=True, type=lambda x: x.lower() == "true")
    parser.add_argument("--analyze", default=True, type=lambda x: x.lower() == "true")
    parser.add_argument("--verbose", default=False, type=lambda x: x.lower() == "true")
    parser.add_argument("--local-file", type=str, default=None)

    # Argument to control music generation
    parser.add_argument(
        "--generate",
        default=True,
        type=lambda x: x.lower() == "true",
        help="Set to 'True' to generate the music after analysis.",
    )
    args = parser.parse_args()

    # --- UPDATED DATA LOADING LOGIC ---
    all_regional_data = None

    # --- Priority 1: Use the local file if provided ---
    if args.local_file:
        print(f"Loading news from local file: {args.local_file}")
        try:
            with open(args.local_file, "r", encoding="utf-8") as f:
                all_regional_data = json.load(f)
        except FileNotFoundError:
            print(f"Error: Local file not found at '{args.local_file}'")
            exit()
    else:
        # --- Priority 2: Try to use today's cache file ---
        today_str = datetime.now().strftime("%Y-%m-%d")
        cache_filename = f"news_data_{today_str}.json"
        if os.path.exists(cache_filename):
            print(f"Loading news from today's cache file: {cache_filename}")
            with open(cache_filename, "r", encoding="utf-8") as f:
                all_regional_data = json.load(f)

        # --- Priority 3: Fetch live data if allowed ---
        elif args.fetch:
            print(f"No cache file found. Fetching live data from API...")
            config = load_regions_config()
            if not config:
                exit()

            all_regional_data = {}
            for region_name, region_data in config["regions"].items():
                language_code = region_data["language"]
                if args.verbose:
                    print(
                        f"  -> Fetching for Region: {region_name} (Language: {language_code.upper()})"
                    )
                articles = news_fetcher.fetch_news_for_language(language_code)
                all_regional_data[region_name] = {
                    "language": language_code,
                    "articles": articles,
                }

            with open(cache_filename, "w", encoding="utf-8") as f:
                json.dump(all_regional_data, f, ensure_ascii=False, indent=4)
            if args.verbose:
                print(f"Live data fetched and saved to {cache_filename}")

    # --- Analysis and Generation Logic ---
    if args.analyze:
        if all_regional_data:
            print("\n--- Analyzing World News with LLM ---")
            all_articles = []
            for region_data in all_regional_data.values():
                articles = region_data.get("articles", [])
                if articles and isinstance(articles, list):
                    all_articles.extend(articles)

            if not all_articles:
                print("No articles available to analyze.")
            else:
                music_prompt, sentiment_analysis = (
                    llm_analyzer.generate_music_prompt_from_news(all_articles)
                )

                if music_prompt and sentiment_analysis:
                    print("\n========================================")
                    print("          TODAY'S WORLD THEME")
                    print("========================================")
                    try:
                        analysis_data = json.loads(sentiment_analysis)
                        formatted_analysis = json.dumps(analysis_data, indent=2)
                        print("\n--- LLM Sentiment Analysis ---")
                        print(formatted_analysis)
                    except json.JSONDecodeError:
                        print("\n--- LLM Sentiment Analysis (raw) ---")
                        print(sentiment_analysis)

                    print("\n--- Generated Music Prompt ---")
                    print(music_prompt)
                    print("\n========================================")

                    # --- MUSIC GENERATION STEP ---
                    if args.generate:
                        audio_file_path = music_generator.generate_and_download_music(
                            music_prompt
                        )

                        if audio_file_path:
                            print("\nProcess complete. Music file is ready.")
                        else:
                            print("\nMusic generation failed. Please check the logs.")
                    else:
                        print("\nMusic generation skipped by command-line argument.")
                else:
                    print("\nCould not generate a music prompt.")
        else:
            print("\nAnalysis enabled, but no data could be loaded.")
