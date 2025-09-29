import os
import requests
from dotenv import load_dotenv
from loguru import logger

load_dotenv()

# Read the API key from the environment
API_KEY = os.getenv("NEWS_API_KEY")

# Strip leading/trailing whitespace and quotes from the key
if API_KEY:
    API_KEY = API_KEY.strip().strip('"')

if not API_KEY:
    raise ValueError("API key not found. Please set NEWS_API_KEY in your .env file.")

# Use the /everything endpoint URL
BASE_URL = "https://newsapi.org/v2/everything"

def fetch_news_for_language(language_code, article_count=5):
    """
    Fetches recent news articles for a given language from NewsAPI's /everything endpoint.
    """
    params = {
        'q': 'news',
        'language': language_code,
        'sortBy': 'publishedAt',
        'apiKey': API_KEY,
        'pageSize': article_count
    }
    
    try:
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        return data.get("articles", [])
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching news for language '{language_code}': {e}")
        return []