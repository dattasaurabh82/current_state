# main.py

import json
import os
from datetime import datetime
import news_fetcher

def load_regions_config(filename="config.json"):
    """Loads the region and language configuration from a JSON file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        return None

if __name__ == "__main__":
    print("Starting the News Caching System...")
    
    # --- Caching Logic ---
    today_str = datetime.now().strftime('%Y-%m-%d')
    cache_filename = f"news_data_{today_str}.json"
    all_regional_data = {}

    if os.path.exists(cache_filename):
        print(f"Loading news from today's cache file: {cache_filename}")
        with open(cache_filename, 'r', encoding='utf-8') as f:
            all_regional_data = json.load(f)
    else:
        print(f"No cache file found for today. Fetching live data from API...")
        config = load_regions_config()
        if not config:
            exit()

        for region_name, region_data in config["regions"].items():
            language_code = region_data["language"]
            print(f"  -> Fetching for Region: {region_name} (Language: {language_code.upper()})")
            
            articles = news_fetcher.fetch_news_for_language(language_code)
            all_regional_data[region_name] = {
                "language": language_code,
                "articles": articles
            }
        
        # Save the freshly fetched data to the cache file
        with open(cache_filename, 'w', encoding='utf-8') as f:
            json.dump(all_regional_data, f, ensure_ascii=False, indent=4)
        print(f"Live data fetched and saved to {cache_filename}")

    # --- For testing, we just print a summary of what we have ---
    print("\n--- Summary of Loaded Data ---")
    for region, data in all_regional_data.items():
        print(f"Region: {region}, Language: {data['language']}, Articles Fetched: {len(data['articles'])}")