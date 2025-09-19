import replicate
import json
import re
from typing import Optional
from loguru import logger

# --- Function to load the system prompt ---
def load_system_prompt() -> str:
    try:
        with open("prompts/news_analyzer_system.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        logger.error("Error: prompts/news_analyzer_system.md not found.")
        # Fallback to a default prompt
        return "You are a world-mood analyst. You MUST output ONLY a valid JSON object."

# Use the loaded prompt to build the template
PROMPT_TEMPLATE = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{load_system_prompt()}<|eot_id|><|start_header_id|>user<|end_header_id|>

{{prompt}}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""

def analyze_news_headlines(articles: list[dict]) -> Optional[str]:
    logger.info("[Agent 1] Analyzing headlines for themes and mood...")

    headlines_for_prompt = [f"- {article.get('title', 'No Title')} (Source: {article.get('source', {}).get('name', 'N/A')})" for article in articles]

    headlines_str = "\n".join(headlines_for_prompt)

    user_prompt = f"""
    **Instructions:**
    1. Read the headlines provided below.
    2. Write a brief, one-sentence summary of the day's events.
    3. Identify and list up to 5 key themes.
    4. Describe the overall mood in 2-3 descriptive words.
    5. List the top 3-5 news sources that were most influential in your analysis.

    **Output Format:**
    Provide your response as a single, raw JSON object with keys: "summary", "key_themes", "overall_mood", and "influential_sources".

    **Headlines:**
    {headlines_str}
    """
    
    try:
        output_chunks = replicate.run(
            "meta/meta-llama-3-70b-instruct",
            input={
                "prompt": user_prompt,
                "prompt_template": PROMPT_TEMPLATE,
                "temperature": 0.6,
                "max_new_tokens": 500,
                "frequency_penalty": 0.2
            }
        )
        
        full_output = "".join(output_chunks)
        
        if not full_output or not full_output.strip():
            logger.error("[Agent 1] Error: Received empty response from the API.")
            return None

        # Find the JSON object within the raw output
        match = re.search(r'\{.*\}', full_output, re.DOTALL)
        
        if not match:
            logger.error("[Agent 1] Error: Could not find a JSON object in the LLM's response.")
            logger.debug(f"[Agent 1] Raw output from LLM:")
            logger.debug(f"{full_output}")
            return None

        json_str = match.group(0)
        
        # Try to parse and pretty-print the JSON
        try:
            parsed_json = json.loads(json_str)
            pretty_json = json.dumps(parsed_json, indent=2)
            logger.info(f"[Agent 1] Formatted JSON output from LLM:")
            logger.info(f"{pretty_json}")
        except json.JSONDecodeError:
            logger.error("[Agent 1] Error: Failed to parse JSON, showing raw output.")
            logger.debug(f"[Agent 1] Raw output from LLM:")
            logger.debug(f"{json_str}")
            return None
        
        logger.success("[Agent 1] Successfully extracted and validated JSON.")
        return json_str

    except Exception as e:
        logger.error(f"[Agent 1] An unexpected error occurred: {e}")
        return None