# backend/modules/voice_assistant.py (FINAL - Subprocess Version)

import vosk
import json
import sounddevice as sd
from gtts import gTTS
import os
import subprocess
import sys
import time

# Prefer an offline TTS engine when available for low-latency, offline speech.
try:
    import pyttsx3
    HAS_PYTTSX3 = True
except Exception:
    HAS_PYTTSX3 = False

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

        # 1) Prefer offline TTS (pyttsx3) if available — it plays audio synchronously.
        if HAS_PYTTSX3:
            try:
                engine = pyttsx3.init()
                # Optional: tune voice rate/volume here if desired
                engine.say(text)
                engine.runAndWait()
                return
            except Exception as e:
                print(f"pyttsx3 failed, falling back to gTTS: {e}")

        # 2) Fallback to gTTS (network-dependent) with file playback
        filename = "temp_speech.mp3"
        try:
            tts = gTTS(text=text, lang=lang)
            tts.save(filename)

            # Play the file using platform-appropriate command
            if sys.platform == "win32":
                command = ["start", "/min", filename]
                subprocess.run(command, shell=True, check=True)
            elif sys.platform == "darwin":
                subprocess.run(["afplay", filename], check=True)
            else:
                subprocess.run(["mpg123", filename], check=True)

            # Estimate duration and wait a little on Windows to ensure playback finishes
            if sys.platform == "win32":
                duration_estimate = max(1.5, len(text.split()) / 5.0)
                time.sleep(duration_estimate)

        except Exception as e:
            print(f"Error playing sound via gTTS fallback: {e}")
        finally:
            if os.path.exists(filename):
                try:
                    time.sleep(0.2)
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