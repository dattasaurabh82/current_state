import os
from dotenv import load_dotenv
from loguru import logger
from llm_agents import news_analyzer, musicgen_prompt_crafter 

load_dotenv()

# Strip whitespace/quotes from the Replicate API token
replicate_token = os.getenv("REPLICATE_API_TOKEN")
if replicate_token:
    os.environ["REPLICATE_API_TOKEN"] = replicate_token.strip().strip('"')

if not os.getenv("REPLICATE_API_TOKEN"):
    raise ValueError("REPLICATE_API_TOKEN not found in .env file.")

def generate_music_prompt_from_news(articles):
    """
    Orchestrates the two-agent process of analyzing news and crafting a music prompt.
    """
    logger.warning("STARTING LLM ANALYSIS PIPELINE...")

    headlines_for_prompt = [f"- {article.get('title', 'No Title')} (Source: {article.get('source', {}).get('name', 'N/A')})" for article in articles]
    
    if not headlines_for_prompt:
        logger.warning("No valid article titles found to analyze.")
        return None, None

    # Step 1: Call the News Analyzer Agent
    analysis_json = news_analyzer.analyze_news_headlines(articles)
    
    if not analysis_json:
        logger.error("Pipeline failed at news analysis step.")
        return None, None

    # Step 2: Call the Prompt Crafter Agent
    music_prompt = musicgen_prompt_crafter.craft_music_prompt(analysis_json)

    if not music_prompt:
        logger.error("Pipeline failed at prompt crafting step.")
        return None, analysis_json # Return analysis for debugging

    logger.success("LLM analysis pipeline completed successfully.")
    return music_prompt, analysis_json