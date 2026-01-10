from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from openai import OpenAI
import base64
import cv2
import numpy as np
import os
<<<<<<< HEAD
import time
import json
import threading
=======
from modules.navigator import Navigator
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from ultralytics import YOLO
import sqlite3
from config import DB_PATH
from modules.audio_cues import compute_pan_volume
from modules.obstacle_filter import ObstacleFilter

import json
import math
import time

# Load KB embeddings if available (lazy load)
KB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'kb')
KB_EMB_PATH = os.path.join(KB_DIR, 'embeddings.npy')
KB_CHUNKS_PATH = os.path.join(KB_DIR, 'chunks.json')
_kb_embeddings = None
_kb_chunks = None

def load_kb():
    global _kb_embeddings, _kb_chunks
    if _kb_embeddings is None:
        try:
            _kb_embeddings = np.load(KB_EMB_PATH)
            with open(KB_CHUNKS_PATH, 'r', encoding='utf-8') as f:
                _kb_chunks = json.load(f)
            print('✅ KB loaded:', len(_kb_chunks), 'chunks')
        except Exception as e:
            print('⚠️ KB not available:', e)
            _kb_embeddings = None
            _kb_chunks = None
    return _kb_embeddings, _kb_chunks

OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if OPENAI_API_KEY:
    openai_client = OpenAI(api_key=OPENAI_API_KEY)
else:
    openai_client = None
>>>>>>> bdc5b15c50262411885aea250c797832ada78e59

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
<<<<<<< HEAD
va_app = VisionAssistantApp(socketio)

def decode_image(data_url):
=======
object_detector = ObjectDetector()
navigator = Navigator(map_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'map.geojson'))
obstacle_filter = ObstacleFilter(max_history=5)
current_route_coords = None  # Track active route for context filtering
print("✅ Navigator Initialized.")

# --- NEW GPS FEATURE SETUP ---
geolocator = Nominatim(user_agent="vision_assistant")
CAMPUS_CENTER = (12.9716, 77.5946) 
CAMPUS_RADIUS_METERS = 500
user_is_in_geofence = None 
last_user_coords = None # (lat, lon)

def get_position_label(x_coordinate):
    if x_coordinate < 0.35: return "to your left"
    elif x_coordinate > 0.65: return "to your right"
    else: return "in front of you"

def generate_summary(objects):
    if not objects: return "The path ahead looks clear."
    objects.sort(key=lambda x: x['distance'])
    closest_obj = objects[0]
    position_text = get_position_label(closest_obj['position_x'])
    summary = f"I see a {closest_obj['name']} {position_text}, about {closest_obj['distance']:.1f} meters away."
    if len(objects) > 1:
        other_object_names = [obj['name'] for obj in objects[1:]]
        other_objects_str = ", a ".join(other_object_names)
        summary += f" There is also a {other_objects_str} nearby."
    return summary

def decode_image_from_data_url(data_url):
>>>>>>> bdc5b15c50262411885aea250c797832ada78e59
    encoded_data = data_url.split(',')[1]
    nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

@socketio.on('connect')
def handle_connect():
    print('✅ Client connected')

@socketio.on('process_frame')
def handle_process_frame(data):
<<<<<<< HEAD
    if va_app.fsm.state == State.IDLE or va_app.fsm.state == State.PAUSE:
        return

=======
    """Real-time obstacle detection loop with smart filtering."""
>>>>>>> bdc5b15c50262411885aea250c797832ada78e59
    try:
        image = decode_image(data['image_data'])
        detections = va_app.detector.detect(image)
        va_app.context.update_detections(detections)
        
<<<<<<< HEAD
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
=======
        # Apply smart filtering: urgency classification + duplicate suppression
        filtered = obstacle_filter.filter_obstacles(detections, time.time())
        
        # Optional: apply context filtering if route is active
        if current_route_coords:
            filtered = obstacle_filter.apply_context_filtering(filtered, current_route_coords)
        
        if filtered:
            # Sort by urgency: critical first
            sorted_dets = sorted(filtered, key=lambda d: {'critical': 0, 'warning': 1}.get(d.get('urgency', 'safe'), 2))
            
            emit('obstacle_alert', {
                'message': message,
                'urgency': urgency,
                'vibrate_pattern': vibrate_pattern,
                'audio': {'pan': pan, 'volume': volume}
            })
        # Don't emit "clear" on every frame if no obstacles; reduces noise
>>>>>>> bdc5b15c50262411885aea250c797832ada78e59
            
        emit('detections_update', {'detections': detections})
        
    except Exception as e:
        print(f"Error processing frame: {e}")

<<<<<<< HEAD
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
=======

@app.route('/api/calibrate', methods=['POST'])
def api_calibrate():
    """Accepts JSON {'focal_length': number} and stores it in settings table."""
    try:
        body = request.get_json(force=True)
        focal_length = body.get('focal_length')
        if focal_length is None:
            return jsonify({'error': 'focal_length required'}), 400

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('INSERT OR REPLACE INTO settings(key, value) VALUES(?, ?)', ('focal_length', str(float(focal_length))))
        conn.commit()
        # Estimate walking speed (m/s) — conservative 1.2 m/s (~4.3 km/h)
        walking_speed = 1.2
        eta_seconds = total_distance / walking_speed
        eta_minutes = max(1, round(eta_seconds / 60.0))

        human_msg = f"You should be there in about {eta_minutes} minutes. Keep walking straight."

        return jsonify({'eta_minutes': eta_minutes, 'message': human_msg, 'distance_m': total_distance})

    except Exception as e:
        print(f"ETA API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/landmarks', methods=['GET'])
def api_landmarks():
    try:
        names = list(navigator.landmarks.keys())
        return jsonify({'landmarks': names})
    except Exception as e:
        print(f"Landmarks API error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """RAG chat with smart navigation context.
    
    Request: { query, detections (optional), location (optional) }
    Returns: { answer, retrieved }
    """
    if not openai_client:
        return jsonify({'error': 'OPENAI_API_KEY not configured on server'}), 500

    body = request.get_json(force=True)
    query = body.get('query', '')
    detections = body.get('detections', [])
    location = body.get('location')

    if not query:
        return jsonify({'error': 'query required'}), 400

    # Smart context: detect if query is navigation-related
    nav_keywords = ['from', 'to', 'route', 'navigate', 'how long', 'distance', 'eta', 'path', 'where']
    is_nav_query = any(kw in query.lower() for kw in nav_keywords)
    
    # 1) Load KB and retrieve similar chunks
    emb, chunks = load_kb()
    retrieved_texts = []
    if emb is not None and chunks is not None:
        try:
            resp = openai_client.embeddings.create(model='text-embedding-3-small', input=query)
            q_emb = np.array(resp.data[0].embedding, dtype=np.float32)
            # cosine similarity
            dists = emb.dot(q_emb) / (np.linalg.norm(emb, axis=1) * (np.linalg.norm(q_emb) + 1e-12))
            topk = min(6, len(dists))
            idx = np.argsort(-dists)[:topk]
            for i in idx:
                retrieved_texts.append(chunks[i]['text'])
        except Exception as e:
            print('KB retrieval error:', e)

    # Build system prompt with navigation context
    system = (
        "You are Vision Assistant — a concise, accessible assistant for blind users navigating a college campus. "
        "Guidelines: (1) Start with the most important action; (2) Use simple, short sentences; (3) Provide distances in meters; "
        "(4) For navigation, reference known landmarks: Main Entrance, Architecture Block (Arch), Engineering Building (Engg), "
        "Canteen, Underground Hostel (UG), Postgraduate Building (UGPG); (5) If uncertain, suggest a safe action."
    )

    context_parts = []
    
    # Add retrieved KB context
    if retrieved_texts:
        context_parts.append('=== Relevant Information ===')
        context_parts += retrieved_texts[:4]

    # Add navigation-specific context if query is navigation-related
    if is_nav_query:
        nav_context = (
            "=== Campus Landmarks ===\n"
            "- Main Entrance: Primary entry point\n"
            "- Architecture Block (Arch): Near main entrance\n"
            "- Engineering Building (Engg): Central location\n"
            "- Canteen: Food facility, central area\n"
            "- UG Hostel: Residential, quieter area\n"
            "- UGPG Building: Research/postgraduate facilities\n\n"
            "Walking speed: ~1.2 m/s (4.3 km/h). "
            "Example routes: Main Entrance to Canteen ~3-4 min, Engg to UG ~5-7 min."
        )
        context_parts.insert(0, nav_context)

    # Add camera detections context
    if detections:
        det_lines = []
        for d in detections[:6]:
            det_lines.append(f"  - {d.get('name')} at {d.get('distance',0):.1f}m")
        context_parts.append(f"=== Current Obstacles ===\n" + '\n'.join(det_lines))

    # Add location context
    if location:
        context_parts.append(f"=== Your Location ===\n{location}")

    full_context = "\n\n".join(context_parts)

    # Call OpenAI ChatCompletion with modern client
    try:
        chat_resp = openai_client.chat.completions.create(
            model='gpt-4o-mini',
            messages=[
                {'role': 'system', 'content': system},
                {'role': 'user', 'content': f"{full_context}\n\nQuestion: {query}"}
            ],
            max_tokens=400,
            temperature=0.2,
        )
        answer = chat_resp.choices[0].message.content
    except Exception as e:
        print('OpenAI chat error:', e)
        # Fallback: provide simple navigation answer based on keywords
        if is_nav_query:
            answer = "I can help with navigation. Try saying 'from [landmark] to [landmark]' or ask about specific landmarks like Canteen, Engineering, or Architecture Block."
        else:
            return jsonify({'error': str(e)}), 500

    return jsonify({'answer': answer, 'retrieved': len(retrieved_texts)})
>>>>>>> bdc5b15c50262411885aea250c797832ada78e59

if __name__ == '__main__':
    # Initial greeting
    print("🚀 Vision Assistant Server Starting...")
    socketio.run(app, host='0.0.0.0', port=5000, debug=False)