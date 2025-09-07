import json
import os
from datetime import datetime
import news_fetcher
import emotion_analyzer
from collections import Counter
import argparse

def load_regions_config(filename="config.json"):
    """Loads the region and language configuration from a JSON file."""
    try:
        with open(filename, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: {filename} not found.")
        return None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch and/or analyze world news sentiment.")
    parser.add_argument(
        '--fetch',
        default=True,
        type=lambda x: x.lower() == 'true',
        help="Set to 'True' or 'False' to control fetching new data. (default: True)"
    )
    parser.add_argument(
        '--analyze',
        default=True,
        type=lambda x: x.lower() == 'true',
        help="Set to 'True' or 'False' to control sentiment analysis. (default: True)"
    )
    parser.add_argument(
        '--verbose',
        default=False,
        type=lambda x: x.lower() == 'true',
        help="Set to 'True' to see detailed logs. (default: False)"
    )
    args = parser.parse_args()

    if not args.fetch and not args.analyze:
        print("Both fetching and analysis are disabled. Exiting.")
        exit()

    print("Starting World Sentiment Project...")
    
    today_str = datetime.now().strftime('%Y-%m-%d')
    cache_filename = f"news_data_{today_str}.json"
    all_regional_data = None

    if os.path.exists(cache_filename):
        print(f"Loading news from today's cache file: {cache_filename}")
        with open(cache_filename, 'r', encoding='utf-8') as f:
            all_regional_data = json.load(f)
    elif args.fetch:
        print(f"No cache file found. Fetching live data from API...")
        config = load_regions_config()
        if not config: exit()

        all_regional_data = {}
        for region_name, region_data in config["regions"].items():
            language_code = region_data["language"]
            if args.verbose:
                print(f"  -> Fetching for Region: {region_name} (Language: {language_code.upper()})")
            
            articles = news_fetcher.fetch_news_for_language(language_code)
            
            # --- TO DISPLAY FETCHED ARTICLES ---
            if args.verbose:
                if articles:
                    print("    Fetched Titles:")
                    for i, article in enumerate(articles):
                        print(f"      {i+1}. {article.get('title')}")
                else:
                    print("    -> No articles were returned from the API for this region.")

            all_regional_data[region_name] = {"language": language_code, "articles": articles}
        
        with open(cache_filename, 'w', encoding='utf-8') as f:
            json.dump(all_regional_data, f, ensure_ascii=False, indent=4)
        if args.verbose:
            print(f"Live data fetched and saved to {cache_filename}")
    
    if args.verbose and all_regional_data:
        print("\n--- Summary of Loaded Data ---")
        for region, data in all_regional_data.items():
            article_count = len(data.get('articles', []))
            print(f"Region: {region}, Language: {data['language']}, Articles: {article_count}")

    if args.analyze:
        if all_regional_data:
            regional_sentiments = []
            if args.verbose:
                print("\n--- Analyzing Regional Sentiments ---")

            for region, data in all_regional_data.items():
                if args.verbose:
                    print(f"\nProcessing Region: {region}...")
                articles = data['articles']
                language = data['language']
                
                analysis_results = emotion_analyzer.analyze_articles_sentiment(articles, language)
                sentiment_profile = emotion_analyzer.calculate_sentiment_profile(analysis_results)
                
                dominant_sentiment = sentiment_profile['dominant_sentiment']
                regional_sentiments.append(dominant_sentiment)
                
                if args.verbose:
                    print(f" Dominant Sentiment: {dominant_sentiment}")
                    print(" Sentiment Distribution:")
                    for sentiment, count in sentiment_profile['sentiment_counts'].items():
                        print(f"  - {sentiment}: {count}")

            if regional_sentiments:
                world_sentiment_counts = Counter(regional_sentiments)
                overall_world_sentiment = world_sentiment_counts.most_common(1)[0][0]
                print("\n========================================")
                print(f"Overall World Sentiment Today: {overall_world_sentiment}")
                print("========================================")
        else:
            print("\nAnalysis enabled, but no data could be loaded or fetched. Please run with --fetch True to create a cache file.")
    elif args.verbose:
        print("\nAnalysis disabled by command-line argument.")