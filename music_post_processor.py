import numpy as np
import soundfile as sf
from pathlib import Path

def apply_fade(
    audio_array: np.ndarray,
    sample_rate: int,
    fade_in_duration: float = 1.5,
    fade_out_duration: float = 2.0,
) -> np.ndarray:
    """
    Applies a linear fade-in and fade-out to a NumPy audio array.
    """
    # Convert fade durations from seconds to sample counts
    fade_in_samples = int(fade_in_duration * sample_rate)
    fade_out_samples = int(fade_out_duration * sample_rate)

    # Make a copy to avoid modifying the original array
    processed_audio = audio_array.copy()

    # Apply fade-in
    if fade_in_samples > 0 and fade_in_samples <= len(processed_audio):
        fade_in_envelope = np.linspace(0, 1, fade_in_samples, dtype=np.float32)
        processed_audio[:fade_in_samples] *= fade_in_envelope

    # Apply fade-out
    if fade_out_samples > 0 and fade_out_samples <= len(processed_audio):
        fade_out_envelope = np.linspace(1, 0, fade_out_samples, dtype=np.float32)
        processed_audio[-fade_out_samples:] *= fade_out_envelope

    return processed_audio


def process_and_replace(file_path: Path) -> bool:
    """
    Loads an audio file, applies fade effects, and overwrites the original file.

    Returns:
        True if successful, False otherwise.
    """
    print(f"\n--- Post-Processing Audio ---")
    print(f"Applying fade effects to: {file_path.name}")
    try:
        # 1. Load the audio file
        original_audio, sample_rate = sf.read(file_path, dtype='float32')
        
        # 2. Apply the fade effect
        processed_audio = apply_fade(original_audio, sample_rate)

        # 3. Overwrite the original file with the new data
        sf.write(file_path, processed_audio, sample_rate)
        
        print("Post-processing complete. File has been updated.")
        return True

    except Exception as e:
        print(f"An error occurred during post-processing: {e}")
        return False