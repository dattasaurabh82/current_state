# create_silent_wav.py

import numpy as np
import soundfile as sf
from pathlib import Path

# --- Parameters ---
samplerate = 44100  # 44.1kHz
duration = 1.0      # 1 second
amplitude = 0.0     # Silence
filename = "silent.wav"

# --- Generate Audio Data ---
# Create an array of zeros, which represents silence
num_samples = int(samplerate * duration)
silent_data = np.zeros(num_samples, dtype=np.float32)

# --- Write to File ---
try:
    sf.write(filename, silent_data, samplerate)
    print(f"Successfully created '{filename}'")
except Exception as e:
    print(f"An error occurred: {e}")