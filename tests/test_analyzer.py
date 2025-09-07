# test_analyzer.py

import json
from datetime import datetime
import emotion_analyzer # Import the module we want to test

print("🧪 Starting analyzer test script...")

# --- 1. Load the Cached Data ---
today_str = datetime.now().strftime('%Y-%m-%d')
cache_filename = f"news_data_{today_str}.json"

try:
    with open(cache_filename, 'r', encoding='utf-8') as f:
        all_regional_data = json.load(f)
    print(f"✅ Successfully loaded data from {cache_filename}")
except FileNotFoundError:
    print(f"❌ Error: Cache file not found: {cache_filename}")
    print("Please run the main script first to create the cache.")
    exit()

# --- 2. Select a Sample to Test ---
test_region_name = "English_Speaking"
if test_region_name in all_regional_data:
    sample_data = all_regional_data[test_region_name]
    articles = sample_data['articles']
    # --- THIS IS THE ADDED LINE ---
    language = sample_data['language']
    
    print(f"🔬 Using {len(articles)} articles from '{test_region_name}' (Language: {language}) for the test.\n")

    # --- 3. Run the Analyzer Functions ---
    print("--- Testing: Individual Article Analysis ---")
    analysis_results = emotion_analyzer.analyze_articles_sentiment(articles, language)
    for result in analysis_results:
        print(f"  Sentiment: {result['sentiment']} | Title: {result['title']}")
    
    print("\n--- Testing: Regional Profile Calculation ---")
    sentiment_profile = emotion_analyzer.calculate_sentiment_profile(analysis_results)
    
    dominant_sentiment = sentiment_profile['dominant_sentiment']
    print(f"  Dominant Sentiment: {dominant_sentiment}")
    print("  Sentiment Distribution:")
    for sentiment, count in sentiment_profile['sentiment_counts'].items():
        print(f"  - {sentiment}: {count}")

else:
    print(f"❌ Error: Region '{test_region_name}' not found in the cache file.")