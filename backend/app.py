from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
import base64
import cv2
import numpy as np
import os
import time
import json
import threading

# Import our new modules
from assistant.state_machine import VisionAssistantFSM, State
from assistant.intent_parser import IntentParser
from assistant.context_manager import ContextManager
from vision.detector import ObjectDetector
from vision.distance import classify_urgency
from navigation.navigator import Navigator
from audio.tts import TTSEngine
from audio.sound_classifier import SoundClassifier

class VisionAssistantApp:
    def __init__(self, socketio):
        self.socketio = socketio
        self.tts = TTSEngine(socketio)
        self.fsm = VisionAssistantFSM(self.tts)
        self.intent_parser = IntentParser()
        self.context = ContextManager()
        self.detector = ObjectDetector(mode='yolo') # Prefers YOLO
        self.navigator = Navigator(self.context)
        self.sound_classifier = SoundClassifier(callback=self.handle_sound_hazard)
        
        # Start sound classifier in a background check loop or separate thread if needed
        self.sound_classifier.start()
        
        self.last_critical_alert_time = 0
        self.critical_alert_cooldown = 5.0
        self.last_periodic_info_time = time.time()
        self.periodic_info_interval = 45.0 # Random 30-60 in logic
        self.last_spoken_nav_step = -1

    def handle_sound_hazard(self, hazard_type):
        self.fsm.handle_event("HAZARD_DETECTED", {"type": "sound", "hazard": hazard_type})
        self.tts.speak(f"Warning. {hazard_type} detected.")
        # Hazard clearing logic would normally be more complex
        threading.Timer(5.0, lambda: self.fsm.handle_event("HAZARD_CLEARED")).start()

    def process_voice_command(self, text):
        parsed = self.intent_parser.parse(text)
        intent = parsed['intent']
        data = parsed['data']
        
        print(f"Parsed Intent: {intent}, Data: {data}")

        # Navigation-specific hint
        hint = ". Swipe up to hear the next instruction and swipe down for the previous instruction."
        
        if intent == "start_assistance":
            self.fsm.handle_event("VOICE_COMMAND", {"intent": "start_assistance"})
            self.tts.speak("Vision assistant active. Scanning environment.")
        
        elif intent == "guide_me":
            dest = data.get("destination")
            if dest:
                self.tts.speak(f"Calculating route to {dest}")
                # Assuming start_navigation now returns the first instruction
                instr = self.navigator.start_navigation('entrance', dest) 
                self.fsm.handle_event("VOICE_COMMAND", {"intent": intent})
                self.tts.speak(f"Guiding you to {dest}. {instr}" + hint)
            else:
                self.tts.speak("Where would you like to go?")
        
        elif intent == "next_step":
            msg = self.navigator.get_next_step()
            self.tts.speak(msg + hint)
        
        elif intent == "repeat":
            msg = self.navigator.get_prev_step()
            self.tts.speak(msg + hint)
            
        elif intent == "stop_navigation":
            msg = self.navigator.stop_navigation()
            self.fsm.handle_event("VOICE_COMMAND", {"intent": "stop_navigation"})
            self.tts.speak(msg)
            
        elif intent == "what_is_front":
            summary = self.context.get_summary_for_rag() # Basic summary for now
            self.tts.speak(summary)
            
        elif intent == "where_am_i":
            if self.context.current_location:
                # In a real app, use reverse geocoding or landmark name
                self.tts.speak(f"You are at your current GPS location.")
            else:
                self.tts.speak("I'm sorry, I don't know your exact location yet.")
        
        elif intent == "pause":
            self.fsm.handle_event("VOICE_COMMAND", {"intent": "pause"})
            self.tts.speak("Assistance paused.")
        
        elif intent == "resume":
            self.fsm.handle_event("VOICE_COMMAND", {"intent": "resume"})
            self.tts.speak("Assistance resumed.")

# --- Flask & SocketIO Setup ---
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
va_app = VisionAssistantApp(socketio)

def decode_image(data_url):
    encoded_data = data_url.split(',')[1]
    nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

@socketio.on('connect')
def handle_connect():
    print('✅ Client connected')

@socketio.on('process_frame')
def handle_process_frame(data):
    if va_app.fsm.state == State.IDLE or va_app.fsm.state == State.PAUSE:
        return

    try:
        image = decode_image(data['image_data'])
        detections = va_app.detector.detect(image)
        va_app.context.update_detections(detections)
        
        now = time.time()
        
        # 1. Critical Obstacle Logic (Every 5 seconds)
        critical = [d for d in detections if d.get('urgency') == 'CRITICAL']
        if critical:
            if now - va_app.last_critical_alert_time > va_app.critical_alert_cooldown:
                obj = critical[0]
                va_app.fsm.handle_event("HAZARD_DETECTED", {"type": "vision", "obj": obj})
                
                # Descriptive safety alerts
                name = obj['name'].lower()
                if any(v in name for v in ["car", "bus", "truck", "vehicle"]):
                    alert_msg = f"Please stop for a while, vehicle approaching."
                elif "person" in name:
                    alert_msg = f"Please stop, there is a person in front of you."
                else:
                    alert_msg = f"Caution. there is a {obj['name']} very close. Please stop."

                socketio.emit('alert_sound', {'type': 'critical'})
                va_app.tts.speak(alert_msg)
                va_app.last_critical_alert_time = now
        else:
            # AUTO-RECOVERY: If we were in ALERT_MODE but no hazards are left, clear it
            if va_app.fsm.state == State.ALERT_MODE and va_app.fsm.hazard_detected:
                print("✨ Hazard cleared automatically (Vision)")
                va_app.fsm.handle_event("HAZARD_CLEARED")
                # Repeat current instruction if navigating
                if va_app.fsm.navigation_active:
                    instr = va_app.navigator.get_prev_step() # Repeat current step
                    hint = ". Swipe up to hear the next instruction and swipe down for the previous instruction."
                    va_app.tts.speak(instr + hint)
        
        # 2. Periodic Info Scan (Every 30-60 seconds)
        if not critical and detections and va_app.fsm.state != State.ALERT_MODE:
            if now - va_app.last_periodic_info_time > va_app.periodic_info_interval:
                # Pick the closest non-critical object
                obj = min(detections, key=lambda x: x.get('distance', 99))
                pos_label = "front"
                if obj.get('position_x', 0.5) < 0.35: pos_label = "left"
                elif obj.get('position_x', 0.5) > 0.65: pos_label = "right"
                
                info_text = f"There is a {obj['name']} {obj.get('distance', '?'):.1f} meters away to your {pos_label}."
                va_app.tts.speak(info_text)
                va_app.last_periodic_info_time = now
                import random
                va_app.periodic_info_interval = random.uniform(30.0, 60.0)
            
        emit('detections_update', {'detections': detections})
        
    except Exception as e:
        print(f"Error processing frame: {e}")

@socketio.on('voice_command')
def handle_voice_command(data):
    text = data.get('text', '')
    if text:
        # Override navigator speak to include swipe hint
        original_speak = va_app.tts.speak
        def nav_speak(msg, is_nav=False):
            if is_nav:
                msg += ". Swipe up to hear the next instruction and swipe down for the previous instruction."
            original_speak(msg)
        
        # Temporarily swap for navigation intents (or just bake it into process_voice_command)
        va_app.process_voice_command(text)

@socketio.on('location_update')
def handle_location_update(data):
    lat, lon = data.get('latitude'), data.get('longitude')
    if lat and lon:
        instr = va_app.navigator.update_position(lat, lon)
        if instr and va_app.fsm.state == State.NAVIGATION_MODE:
            hint = ". Swipe up for the next instruction and swipe down for the previous instruction."
            va_app.tts.speak(instr + hint)
        emit('navigation_status', va_app.context.navigation_status)

if __name__ == '__main__':
    # Initial greeting
    print("🚀 Vision Assistant Server Starting...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)