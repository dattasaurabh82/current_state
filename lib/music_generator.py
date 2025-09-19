import replicate
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Union, List, Any

current_prediction = None


def cancel_current_prediction():
    """Cancels the currently running Replicate prediction if there is one."""
    global current_prediction
    if current_prediction:
        print("\nAttempting to cancel the current Replicate prediction...")
        try:
            current_prediction.cancel()
            print("Cancellation request sent successfully.")
        except Exception as e:
            print(f"Error sending cancellation request: {e}")
        current_prediction = None


def generate_and_download_music(prompt: str, duration: int = 30) -> Optional[Path]:
    """
    Generates music using Replicate's MusicGen model and downloads the audio file.
    """
    global current_prediction

    print("\nGENERATING MUSIC...")
    clean_prompt = prompt.strip().strip('"')
    print(f'Sending prompt to MusicGen: "{clean_prompt}"')

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
        print(f"\nMusic generation started with ID: {prediction.id}")
        print("Waiting for generation to complete... (Press Ctrl+C to cancel)")

        # This is a blocking call. It waits until the prediction is done.
        prediction.wait()

        # --- Get the output from the prediction object itself ---
        # After .wait() completes, the .output attribute is populated.
        output = prediction.output
        current_prediction = None  # The job is done, clear the global variable

        if output is None:
            print("Music generation failed. The API returned no output.")
            # Optionally, print logs from the failed prediction
            if prediction.logs:
                print("--- Replicate Logs ---")
                print(prediction.logs)
            return None

        audio_data = None
        # The output can be a single URL or a list containing a URL.
        # yes that happened (so that's why ...)
        # We also handle the raw bytes case just in case.
        print("")
        if isinstance(output, str):
            output_url = output
            print(f"Music generated successfully!\nURL: {output_url}")
            print("\nDownloading audio file...")
            audio_response = requests.get(output_url)
            audio_response.raise_for_status()
            audio_data = audio_response.content
        elif isinstance(output, list) and output and isinstance(output[0], str):
            output_url = output[0]
            print(f"Music generated successfully!\nURL: {output_url}")
            print("\nDownloading audio file...")
            audio_response = requests.get(output_url)
            audio_response.raise_for_status()
            audio_data = audio_response.content
        elif isinstance(output, bytes):
            print("\nMusic generated successfully!\nReceived raw audio data.")
            audio_data = output

        if not audio_data:
            print(
                "\nMusic generation failed.\nThe API returned an unexpected data format."
            )
            print(f"\nReceived output type: {type(output)}")
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
        if prediction:
            print(f"An error occurred during prediction {prediction.id}: {e}")
            if prediction.logs:
                print("--- Replicate Logs ---")
                print(prediction.logs)
        else:
            print(f"An error occurred during music generation: {e}")
        return None
