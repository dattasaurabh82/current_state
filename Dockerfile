# Use an official Raspberry Pi OS (Debian) base image
FROM debian:bookworm-slim

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies required for audio and GPIO
RUN apt-get update && apt-get install -y \
    curl \
    libportaudio2 \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Install uv, the Python package manager
RUN curl -LsSf https://astral.sh/uv/install.sh | sh

# Copy the dependency files first to leverage Docker's build cache
COPY pyproject.toml uv.lock ./

# Install Python packages using the FULL PATH to uv to avoid PATH issues
RUN /root/.cargo/bin/uv sync --system

# Copy the rest of the application code into the container
COPY . .

# This environment variable is necessary for loguru to display colors
ENV PYTHONUNBUFFERED=1