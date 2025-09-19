import replicate
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional
from loguru import logger

current_prediction = None


def cancel_current_prediction():
    """Cancels the currently running Replicate prediction if there is one."""
    global current_prediction
    if current_prediction:
        logger.warning("Attempting to cancel the current Replicate prediction...")
        try:
            current_prediction.cancel()
            logger.info("Cancellation request sent successfully.")
        except Exception as e:
            logger.error(f"Error sending cancellation request: {e}")
        current_prediction = None


def generate_and_download_music(prompt: str, duration: int = 30) -> Optional[Path]:
    """
    Generates music using Replicate's MusicGen model and downloads the audio file.
    """
    global current_prediction

    logger.warning("GENERATING MUSIC...")
    clean_prompt = prompt.strip().strip('"')
    logger.warning('Sending prompt to MusicGen:')
    logger.debug(f'"{clean_prompt}"')

    prediction = None
    try:
        prediction = replicate.predictions.create(
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
                "classifier_free_guidance": 3,
            },
        )

        current_prediction = prediction
        logger.warning(f"Music generation started with ID: {prediction.id}")
        logger.debug("Waiting for generation to complete... (Press Ctrl+C to cancel)")

        # This is a blocking call. It waits until the prediction is done.
        prediction.wait()

        # --- Get the output from the prediction object itself ---
        # After .wait() completes, the .output attribute is populated.
        output = prediction.output
        current_prediction = None  # The job is done, clear the global variable

        if output is None:
            logger.error("Music generation failed. The API returned no output.")
            # Optionally, print logs from the failed prediction
            if prediction.logs:
                logger.info("--- Replicate Logs ---")
                logger.info(prediction.logs)
            return None

        audio_data = None
        # The output can be a single URL or a list containing a URL.
        # yes that happened (so that's why ...)
        # We also handle the raw bytes case just in case.
        logger.info("")
        if isinstance(output, str):
            output_url = output
            logger.success(f"Music generated successfully!")
            logger.info(f"URL: {output_url}")
            logger.warning("Downloading audio file...")
            audio_response = requests.get(output_url)
            audio_response.raise_for_status()
            audio_data = audio_response.content
        elif isinstance(output, list) and output and isinstance(output[0], str):
            output_url = output[0]
            logger.success(f"Music generated successfully!")
            logger.info(f"URL: {output_url}")
            logger.warning("Downloading audio file...")
            audio_response = requests.get(output_url)
            audio_response.raise_for_status()
            audio_data = audio_response.content
        elif isinstance(output, bytes):
            logger.success("Music generated successfully!")
            logger.info("Received raw audio data.")
            audio_data = output

        if not audio_data:
            logger.error(
                "Music generation failed.The API returned an unexpected data format."
            )
            logger.info(f"Received output type: {type(output)}")
            return None

        # --- Save the Audio File ---
        music_dir = Path("music_generated")
        music_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        file_path = music_dir / f"world_theme_{timestamp}.wav"
        with open(file_path, "wb") as f:
            f.write(audio_data)
        logger.success(f"Audio file saved to: {file_path}")
        return file_path

    except Exception as e:
        if prediction:
            logger.error(f"An error occurred during prediction {prediction.id}: {e}")
            if prediction.logs:
                logger.info("--- Replicate Logs ---")
                logger.info(prediction.logs)
        else:
            logger.error(f"An error occurred during music generation: {e}")
        return None
