import replicate
from dotenv import load_dotenv

# Load environment variables from the .env file
load_dotenv()

output = replicate.run(
    "meta/musicgen:671ac645ce5e552cc63a54a2bbff63fcf798043055d2dac5fc9e36a837eedcfb",
    input={
        "top_k": 250,
        "top_p": 0,
        "prompt": "Melodies that sound triumphant and cinematic. Leading up to a crescendo that resolves in a 9th harmonic",
        "duration": 20,
        "temperature": 1,
        "continuation": False,
        "model_version": "stereo-melody-large",
        "output_format": "wav",
        "continuation_start": 0,
        "multi_band_diffusion": False,
        "normalization_strategy": "loudness",
        "classifier_free_guidance": 3
    }
)


print(output)

# # To write the file to disk:
# with open("my-image.png", "wb") as file:
#     file.write(output.read())