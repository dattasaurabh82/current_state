# Use an official ARM-compatible Python image, which is better for our use case
FROM python:3.11-slim-bookworm

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for audio and GPIO
RUN apt-get update && apt-get install -y \
    libportaudio2 \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv using pip, which is simpler and more reliable in this environment
RUN pip install uv

# Copy the dependency files first
COPY pyproject.toml uv.lock ./

# Create a virtual environment and install dependencies into it
# This is a best practice inside Docker
RUN uv venv && uv sync

# Copy the rest of the application code into the container
COPY . .

# This environment variable is necessary for loguru to display colors
ENV PYTHONUNBUFFERED=1

# Set the default command to run the player using `uv run`
# `uv run` will automatically find and use the virtual environment we just created
CMD ["uv", "run", "python", "run_player.py"]