import replicate
import json
from typing import Optional
from loguru import logger

# --- NEW: Function to load the system prompt ---
def load_system_prompt() -> str:
    try:
        with open("prompts/musicgen_prompt_crafter_system.md", "r") as f:
            return f.read()
    except FileNotFoundError:
        logger.error("Error: prompts/musicgen_prompt_crafter_system.md not found.")
        # Fallback to a default prompt
        return "You are a creative film score composer."

# Use the loaded prompt to build the template
PROMPT_TEMPLATE = f"""<|begin_of_text|><|start_header_id|>system<|end_header_id|>

{load_system_prompt()}<|eot_id|><|start_header_id|>user<|end_header_id|>

{{prompt}}<|eot_id|><|start_header_id|>assistant<|end_header_id|>
"""

def craft_music_prompt(analysis_json: str) -> Optional[str]:
    logger.info("  -> (Agent 2) Crafting music prompt from analysis...")
    
    try:
        analysis = json.loads(analysis_json)
        # We can create a more detailed context string for the prompt
        mood_context = f"The overall mood is '{analysis.get('overall_mood', 'neutral')}' with key themes of '{', '.join(analysis.get('key_themes', []))}'."

    except json.JSONDecodeError:
        logger.error("  -> (Agent 2) Error: Invalid JSON received from analysis step.")
        return None

    user_prompt = f"""
    **Analysis of World Mood:**
    {mood_context}

    **Your Task:**
    Now, generate the MusicGen prompt based on this analysis.
    """

    try:
        output_chunks = replicate.run(
            "meta/meta-llama-3-70b-instruct",
            input={
                "prompt": user_prompt,
                "prompt_template": PROMPT_TEMPLATE,
                "temperature": 0.85, # Slightly increased for more creativity
                "max_new_tokens": 300,
                "top_p": 0.9,
                "presence_penalty": 1.15
            }
        )

        final_prompt = "".join(output_chunks).strip()

        logger.debug(f"  -> (Agent 2) Raw output from LLM:")
        logger.debug(f"  ---")
        logger.debug(f"  {final_prompt}")
        logger.debug(f"  ---")
        if not final_prompt:
            logger.error("  -> (Agent 2) Error: Received empty response from the API.")
            return None

        logger.info("  -> (Agent 2) Prompt crafting complete.")
        return final_prompt

    except Exception as e:
        logger.error(f"  -> (Agent 2) An unexpected error occurred during prompt crafting: {e}")
        return None