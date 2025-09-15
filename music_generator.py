import replicate
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional


def generate_and_download_music(prompt: str, duration: int = 30) -> Optional[Path]:
    """
    Generates music using Replicate hosted meta's Audiocraft's MusicGen model and downloads the audio file.
    """
    print("\n--- Generating Music ---")
    clean_prompt = prompt.strip().strip('"')
    print(f'Sending prompt to MusicGen: "{prompt}"')

    try:
        output_iterator = replicate.run(
            "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb",
            input={
                "top_k": 250,
                "top_p": 0,
                "prompt": clean_prompt,
                "duration": duration,
                "temperature": 1,
                "continuation": False,
                "model_version": "stereo-melody-large",
                "output_format": "wav",
                "continuation_start": 0,
                "multi_band_diffusion": False,
                "normalization_strategy": "loudness",
                "classifier_free_guidance": 3
            },
        )
        
        output_list = list(output_iterator)
        
        audio_data = None
        
        if not output_list:
            print("Music generation failed. The API returned an empty response.")
            return None

        # Scenario 1: We received a URL (string)
        if isinstance(output_list[0], str):
            output_url = output_list[0]
            print(f"Music generated successfully! URL: {output_url}")
            print("Downloading audio file...")
            audio_response = requests.get(output_url)
            audio_response.raise_for_status()
            audio_data = audio_response.content
        
        # Scenario 2: We received the raw audio data (bytes)
        elif isinstance(output_list[0], bytes):
            print("Music generated successfully! Received raw audio data.")
            # Join the list of bytes chunks into a single byte string
            audio_data = b"".join(output_list)
        
        if not audio_data:
            print("Music generation failed. The API returned an unexpected data format.")
            print(f"Received raw output type: {type(output_list[0])}")
            return None
        
        # --- Save the Audio File ---
        music_dir = Path("music_generated")
        music_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_path = music_dir / f"world_theme_{timestamp}.wav"

        with open(file_path, "wb") as f:
            f.write(audio_data)

        print(f"Audio file saved to: {file_path}")
        return file_path

    except Exception as e:
        print(f"An error occurred during music generation or download: {e}")
        return None

