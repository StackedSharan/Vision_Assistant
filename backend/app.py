from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
from openai import OpenAI
import base64
import cv2
import numpy as np
import os
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

# --- Object Detector Class (YOLOv8) ---
class ObjectDetector:
    def __init__(self):
        # Load YOLOv8n (Nano) model - small and fast
        # It will automatically download 'yolov8n.pt' if not present
        self.model = YOLO('yolov8n.pt')
        print("✅ YOLOv8 Object Detector Initialized.")

    def detect(self, image_frame):
        # Run inference
        results = self.model(image_frame, verbose=False)
        
        detections = []
        # Process results
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Class ID
                cls = int(box.cls[0])
                # Confidence
                conf = float(box.conf[0])
                # Class Name
                name = self.model.names[cls]
                
                # Filter for relevant objects and confidence > 0.4
                if conf > 0.4 and name in ['person', 'car', 'bicycle', 'motorcycle', 'bus', 'truck', 'cat', 'dog', 'bottle', 'chair']:
                    # Bounding Box
                    x1, y1, x2, y2 = box.xyxy[0].tolist()
                    
                    # Estimate distance (Rough approximation based on width)
                    # This is not accurate without calibration but gives a relative idea
                    width_pixels = x2 - x1
                    # Heuristic: Larger width = closer. 
                    # Assuming a person is ~0.5m wide. Focal length ~600.
                    # Distance = (Real Width * Focal Length) / Pixel Width
                    real_width = 0.5 if name == 'person' else 1.5 # Default widths
                    distance = (real_width * 600) / width_pixels
                    
                    center_x = (x1 + x2) / 2 / image_frame.shape[1] # Normalized 0-1

                    detections.append({
                        'name': name,
                        'distance': float(distance),
                        'position_x': float(center_x),
                        'confidence': conf
                    })
        
        print(f"🔍 YOLO Detections: {len(detections)} found.")
        return detections

# --- SETUP AND INITIALIZATION ---
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
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
    encoded_data = data_url.split(',')[1]
    nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

# --- SOCKETIO EVENTS ---
@socketio.on('connect')
def handle_connect():
    print('✅ Client connected')

@socketio.on('process_frame_for_obstacles')
def handle_process_frame(data):
    """Real-time obstacle detection loop with smart filtering."""
    try:
        image = decode_image_from_data_url(data['image_data'])
        detections = object_detector.detect(image)
        
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
            
    except Exception as e:
        print(f"Error processing frame: {e}")


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

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)