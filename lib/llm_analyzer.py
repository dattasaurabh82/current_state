import os
from dotenv import load_dotenv

# Import our specialized agents
from llm_agents import news_analyzer, musicgen_prompt_crafter 

load_dotenv()

if not os.getenv("REPLICATE_API_TOKEN"):
    raise ValueError("REPLICATE_API_TOKEN not found in .env file.")

def generate_music_prompt_from_news(articles):
    """
    Orchestrates the two-agent process of analyzing news and crafting a music prompt.
    """
    print("Starting LLM analysis pipeline...")

    headlines_for_prompt = [f"- {article.get('title', 'No Title')} (Source: {article.get('source', {}).get('name', 'N/A')})" for article in articles]
    
    if not headlines_for_prompt:
        print("No valid article titles found to analyze.")
        return None, None

    # --- Step 1: Call the News Analyzer Agent ---
    analysis_json = news_analyzer.analyze_news_headlines(articles)
    
    if not analysis_json:
        print("Pipeline failed at news analysis step.")
        return None, None

    # --- Step 2: Call the Prompt Crafter Agent ---
    music_prompt = musicgen_prompt_crafter.craft_music_prompt(analysis_json)

    if not music_prompt:
        print("Pipeline failed at prompt crafting step.")
        return None, analysis_json # Return analysis for debugging

    print("LLM analysis pipeline completed successfully.")
    return music_prompt, analysis_json