# emotion_analyzer.py

from textblob import TextBlob
from deep_translator import GoogleTranslator
from collections import Counter

print("Initializing TextBlob Sentiment Analyzer...")
print("TextBlob Analyzer loaded successfully.")

def get_sentiment_category(text):
    """
    Analyzes a piece of text with TextBlob and returns its sentiment category.
    """
    # TextBlob's polarity score ranges from -1.0 (negative) to +1.0 (positive).
    polarity = TextBlob(text).sentiment.polarity

    # We define thresholds to categorize the sentiment.
    if polarity > 0.05:
        return "POSITIVE"
    elif polarity < -0.05:
        return "NEGATIVE"
    else:
        return "NEUTRAL"

def analyze_articles_sentiment(articles, language_code):
    """
    Analyzes the sentiment of each article's title, translating if necessary.
    """
    results = []
    translator = GoogleTranslator(source='auto', target='en')

    for article in articles:
        title = article.get('title')
        if not title or "[Removed]" in title:
            continue
        
        try:
            # Step 1: Translate the title to English if it's not already
            if language_code != 'en':
                text_to_analyze = translator.translate(title)
            else:
                text_to_analyze = title
            
            # Step 2: Analyze the English text using TextBlob
            sentiment = get_sentiment_category(text_to_analyze)
            results.append({'title': title, 'sentiment': sentiment})

        except Exception as e:
            print(f"Could not analyze title: '{title}'. Error: {e}")
            
    return results

def calculate_sentiment_profile(analysis_results):
    """
    Calculates the overall sentiment profile from a list of analysis results.
    """
    if not analysis_results:
        return {"dominant_sentiment": "UNKNOWN", "sentiment_counts": {}}

    sentiments = [result['sentiment'] for result in analysis_results]
    sentiment_counts = Counter(sentiments)
    
    dominant_sentiment = sentiment_counts.most_common(1)[0][0]
    
    return {"dominant_sentiment": dominant_sentiment, "sentiment_counts": dict(sentiment_counts)}