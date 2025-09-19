# news_fetcher.py

import os
import requests
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("NEWS_API_KEY")
if not API_KEY:
    raise ValueError("API key not found. Please set NEWS_API_KEY in your .env file.")

# --- Use the /everything endpoint URL ---
BASE_URL = "https://newsapi.org/v2/everything"

def fetch_news_for_language(language_code, article_count=5):
    """
    Fetches recent news articles for a given language from NewsAPI's /everything endpoint.
    
    Args:
        language_code (str): The 2-letter language code (e.g., 'en', 'de').
        article_count (int): The number of articles to fetch.

    Returns:
        list: A list of article dictionaries, or an empty list if an error occurs.
    """
    params = {
        'q': 'news',  # A required search query. 'news' is a good generic term.
        'language': language_code,
        'sortBy': 'publishedAt', # Ensures we get the most recent articles.
        'apiKey': API_KEY,
        'pageSize': article_count
    }
    
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("articles", [])
        
    except requests.exceptions.RequestException as e:
        print(f"Error fetching news for language '{language_code}': {e}")
        return []