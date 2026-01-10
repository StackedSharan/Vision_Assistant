import sys
import os
import subprocess
import time
from gtts import gTTS

try:
    import pyttsx3
    HAS_PYTTSX3 = True
except ImportError:
    HAS_PYTTSX3 = False

class TTSEngine:
    def __init__(self, socketio=None):
        self.socketio = socketio
        self.engine = None
        if HAS_PYTTSX3:
            try:
                self.engine = pyttsx3.init()
                print("✅ Offline TTS (pyttsx3) available for server.")
            except Exception as e:
                print(f"Failed to initialize pyttsx3: {e}")

    def speak(self, text, lang='en'):
        print(f"TTS Output: {text}")
        if self.socketio:
            # Emit to frontend for localized playback
            self.socketio.emit('speak', {'text': text, 'lang': lang})
        
        # Local playback (optional, usually disabled in production to avoid server noise)
        # self._local_speak(text, lang)

    def _local_speak(self, text, lang):
        if self.engine:
            try:
                self.engine.say(text)
                self.engine.runAndWait()
                return
            except: pass
        self._gtts_speak(text, lang)

    def _gtts_speak(self, text, lang):
        filename = "temp_speech.mp3"
        try:
            tts = gTTS(text=text, lang=lang)
            tts.save(filename)
            
            if sys.platform == "win32":
                # Using 'start' might be async, better to use a proper player if available
                # But 'start' is the fallback provided in existing code.
                subprocess.run(["start", "/min", filename], shell=True, check=True)
                # Wait based on text length
                time.sleep(max(1.5, len(text.split()) / 5.0))
            elif sys.platform == "darwin":
                subprocess.run(["afplay", filename], check=True)
            else:
                subprocess.run(["mpg123", filename], check=True)
        except Exception as e:
            print(f"gTTS error: {e}")
        finally:
            if os.path.exists(filename):
                try: time.sleep(0.5); os.remove(filename)
                except: pass
