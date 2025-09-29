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

# Add uv's directory to the PATH for subsequent commands
ENV PATH="/root/.cargo/bin:${PATH}"

# Copy the dependency files first to leverage Docker's build cache
COPY pyproject.toml uv.lock ./

# Install Python packages using a single uv sync command
RUN uv sync --system

# Copy the rest of the application code into the container
COPY . .

# This environment variable is necessary for loguru to display colors
ENV PYTHONUNBUFFERED=1