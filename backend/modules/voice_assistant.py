# backend/modules/voice_assistant.py (FINAL - Subprocess Version)

import vosk
import json
import sounddevice as sd
from gtts import gTTS
import os
import subprocess
import sys

# --- Configuration ---
MODEL_PATH = "backend/models/vosk-model-en"
SAMPLE_RATE = 16000

class VoiceAssistant:
    def __init__(self):
        """Initializes the voice assistant."""
        if not os.path.exists(MODEL_PATH):
            raise FileNotFoundError(f"Vosk model not found at {MODEL_PATH}.")
            
        self.model = vosk.Model(MODEL_PATH)
        self.recognizer = vosk.KaldiRecognizer(self.model, SAMPLE_RATE)
        print("Voice Assistant initialized.")

    def speak(self, text, lang='en'):
        """
        Converts text to speech and plays it using a robust, blocking method.
        This will solve the issue of sound not playing before the request ends.
        """
        print(f"Assistant Speaking: {text}")
        filename = "temp_speech.mp3"
        try:
            # 1. Create the audio file
            tts = gTTS(text=text, lang=lang)
            tts.save(filename)

            # 2. Determine the correct command to play audio based on the OS
            if sys.platform == "win32":
                # On Windows, 'start' can run the default media player
                # The /min flag starts it minimized so no window pops up
                command = ["start", "/min", filename]
                # We use shell=True for this specific Windows command
                subprocess.run(command, shell=True, check=True)
            elif sys.platform == "darwin": # macOS
                command = ["afplay", filename]
                subprocess.run(command, check=True)
            else: # Linux
                command = ["mpg123", filename]
                subprocess.run(command, check=True)

            # NOTE: For this method to be truly blocking on Windows,
            # we need to add a small manual wait. We'll use a simple time.sleep
            # based on a rough estimate of speech duration.
            # A more advanced solution would be needed for perfect sync,
            # but this will solve the "no sound" problem.
            if sys.platform == "win32":
                import time
                # Estimate duration: 1 second per 5 words
                duration_estimate = max(1.5, len(text.split()) / 5.0)
                time.sleep(duration_estimate)

        except Exception as e:
            # If the command fails (e.g., mpg123 not installed on Linux)
            print(f"Error playing sound: {e}")
            print("Please ensure you have a command-line MP3 player installed if you are on Linux (e.g., 'sudo apt-get install mpg123')")
        finally:
            # 3. Clean up the file
            if os.path.exists(filename):
                try:
                    # Add a tiny delay to ensure the file is released by the player
                    if sys.platform == "win32":
                       time.sleep(0.5)
                    os.remove(filename)
                except Exception as e:
                    print(f"Error removing temp file: {e}")

    def listen(self):
        """Listens for a command and returns the transcribed text."""
        print("Listening for a user command...")
        
        with sd.RawInputStream(samplerate=SAMPLE_RATE, blocksize=8000, dtype='int16', channels=1) as stream:
            while True:
                data, overflowed = stream.read(8000)
                if self.recognizer.AcceptWaveform(bytes(data)):
                    result_json = self.recognizer.Result()
                    result_dict = json.loads(result_json)
                    command = result_dict.get('text', '')
                    if command:
                        print(f"User Said: {command}")
                        return command