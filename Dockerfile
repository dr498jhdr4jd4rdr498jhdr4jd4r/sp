# Use a lightweight Python base image
FROM python:3.11-slim

# Install ffmpeg for audio conversion and nodejs for the yt-dlp JS runtime
RUN apt-get update &&     apt-get install -y ffmpeg nodejs &&     rm -rf /var/lib/apt/lists/*

# Set the working directory
WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Start the Gunicorn server
CMD gunicorn app:app --bind 0.0.0.0:$PORT --threads 4
