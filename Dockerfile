# Use an official ARM-compatible Python image
FROM python:3.11-slim-bookworm

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    libportaudio2 \
    python3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml uv.lock ./

# Install Python packages
RUN uv venv && uv sync

# Copy the silent audio file into the image, relying on .dockerignore
COPY keep_audio_ch_active.wav .

# Copy the rest of the application code
COPY . .

# Set environment variable for logging
ENV PYTHONUNBUFFERED=1

# Set the default command to run the player
CMD ["uv", "run", "python", "run_player.py"]