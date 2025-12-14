FROM python:3.11-slim

WORKDIR /app

# Install system deps for audio playback and common image libs (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Copy backend and install requirements
COPY ./backend /app
RUN pip install --upgrade pip
RUN if [ -f requirements.txt ]; then pip install -r requirements.txt; fi

EXPOSE 5000

ENV PYTHONUNBUFFERED=1

CMD ["python", "app.py"]
