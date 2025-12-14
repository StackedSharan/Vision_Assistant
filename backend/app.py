from flask import Flask, request, jsonify
from flask_socketio import SocketIO, emit
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
import openai
import numpy as np
import json
import math

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
    openai.api_key = OPENAI_API_KEY

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
print("✅ Navigator Initialized.")

# --- NEW GPS FEATURE SETUP ---
geolocator = Nominatim(user_agent="vision_assistant")
CAMPUS_CENTER = (12.9716, 77.5946) 
CAMPUS_RADIUS_METERS = 500
user_is_in_geofence = None 

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
    """Real-time obstacle detection loop."""
    try:
        image = decode_image_from_data_url(data['image_data'])
        detections = object_detector.detect(image)
        
        # Filter for critical obstacles only to reduce noise
        critical_objects = [d for d in detections if d.get('distance', 9999) < 3.0] # Only objects within 3 meters

        if critical_objects:
            summary = generate_summary(critical_objects)
            # compute audio cue for the closest object
            closest = critical_objects[0]
            pan, volume = compute_pan_volume(closest.get('position_x', 0.5), closest.get('distance', 1.0))
            emit('obstacle_alert', {
                'message': summary,
                'audio': {'pan': pan, 'volume': volume}
            })
        else:
            # still send a small cue indicating clear path
            emit('obstacle_alert', {'message': 'Path is clear.', 'audio': {'pan': 0.0, 'volume': 0.0}})
            
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
        conn.close()
        return jsonify({'status': 'ok', 'focal_length': float(focal_length)})
    except Exception as e:
        print(f"Calibration API error: {e}")
        return jsonify({'error': str(e)}), 500

@socketio.on('analyze_surroundings')
def handle_analyze_surroundings(data):
    """On-demand detailed analysis (Long Press)."""
    print("📸 Analyzing surroundings (Long Press)...")
    try:
        image = decode_image_from_data_url(data['image_data'])
        
        # DEBUG: Save image to verify camera input
        cv2.imwrite('debug_frame.jpg', image)
        print("💾 Saved debug_frame.jpg")

        detections = object_detector.detect(image)
        
        if detections:
            # More detailed summary for explicit request
            summary = generate_summary(detections)
            emit('surroundings_analysis', {'message': summary})
        else:
            emit('surroundings_analysis', {'message': "I don't see any obstacles nearby."})
            
    except Exception as e:
        print(f"Error analyzing surroundings: {e}")
        emit('surroundings_analysis', {'message': "Error analyzing image."})

@socketio.on('get_navigation')
def handle_get_navigation(data):
    print(f"\n📍 RECEIVED NAVIGATION REQUEST: {data}")
    start = data.get('start')
    end = data.get('end')
    
    print(f"🔍 Calling navigator.find_shortest_path('{start}', '{end}')...")
    
    try:
        result = navigator.find_shortest_path(start, end)
        
        if result:
            emit('navigation_response', {
                'instructions': result['instructions'],
                'route_coords': result['full_path']
            })
        else:
            emit('navigation_response', {'error': f"Could not find a route from {start} to {end}."})
    except Exception as e:
        print(f"❌ Error in handle_get_navigation: {e}")
        emit('navigation_response', {'error': str(e)})

@socketio.on('location_update')
def handle_location_update(data):
    global user_is_in_geofence
    user_coords = (data['latitude'], data['longitude'])
    distance_to_center = geodesic(user_coords, CAMPUS_CENTER).meters
    is_currently_inside = distance_to_center < CAMPUS_RADIUS_METERS
    
    if is_currently_inside != user_is_in_geofence:
        user_is_in_geofence = is_currently_inside
        if is_currently_inside:
            emit('context_update', {'message': 'Welcome to campus. Navigation Mode is now available.'})
        else:
            emit('context_update', {'message': 'You have left the campus area.'})


@app.route('/api/eta', methods=['POST'])
def api_eta():
    """Compute ETA for a route between named landmarks.

    Request JSON: {"start": "name", "end": "name"}
    Response: {"eta_minutes": float, "message": str, "distance_m": float}
    """
    try:
        body = request.get_json(force=True)
        start = body.get('start')
        end = body.get('end')
        if not start or not end:
            return jsonify({'error': 'start and end required'}), 400

        result = navigator.find_shortest_path(start, end)
        if not result:
            return jsonify({'error': 'could not find route'}), 404

        total_distance = 0.0
        for step in result.get('instructions', []):
            total_distance += float(step.get('distance_m', 0.0))

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
        """RAG chat: accepts { query, context (optional) } and returns model answer.

        Requires OPENAI_API_KEY in env. If backend/kb/ is indexed (embeddings.npy + chunks.json),
        it will retrieve top-k contexts and include them in the prompt.
        """
        if not OPENAI_API_KEY:
            return jsonify({'error': 'OPENAI_API_KEY not configured on server'}), 500

        body = request.get_json(force=True)
        query = body.get('query', '')
        detections = body.get('detections', [])
        location = body.get('location')

        if not query:
            return jsonify({'error': 'query required'}), 400

        # 1) load KB
        emb, chunks = load_kb()
        retrieved_texts = []
        if emb is not None and chunks is not None:
            try:
                # get embedding for query
                resp = openai.Embedding.create(model=os.environ.get('OPENAI_EMBEDDING_MODEL','text-embedding-3-small'), input=query)
                q_emb = np.array(resp['data'][0]['embedding'], dtype=np.float32)
                # cosine similarity
                dists = emb.dot(q_emb) / (np.linalg.norm(emb, axis=1) * (np.linalg.norm(q_emb) + 1e-12))
                topk = min(6, len(dists))
                idx = np.argsort(-dists)[:topk]
                for i in idx:
                    retrieved_texts.append(chunks[i]['text'])
            except Exception as e:
                print('KB retrieval error:', e)

        # assemble system prompt and user prompt
        system = (
            "You are Vision Assistant — a concise, safety-first assistant for blind users. "
            "When answering, start with the most important action, use simple sentences, and provide distances in meters when relevant. "
            "If user asks about navigation, rely on provided route info. If you are uncertain, say so and suggest a safe action."
        )

        context_parts = []
        if retrieved_texts:
            context_parts.append('\n--- Retrieved docs ---\n')
            context_parts += retrieved_texts[:4]

        if detections:
            # include short summary of detections
            det_lines = []
            for d in detections[:6]:
                det_lines.append(f"{d.get('name')} at {d.get('distance',0):.1f}m pos={d.get('position_x',0.5)}")
            context_parts.append('\n--- Camera Detections ---\n' + '\n'.join(det_lines))

        if location:
            context_parts.append(f"\n--- Location ---\n{location}")

        assistant_prompt = (
            system + "\n\n" + ("\n\n".join(context_parts)) + "\n\nUser question: " + query
        )

        # call OpenAI ChatCompletion
        try:
            # Use Chat Completions API (chat.completions) or fallback to completions
            chat_resp = openai.ChatCompletion.create(
                model=os.environ.get('OPENAI_CHAT_MODEL', 'gpt-4o-mini'),
                messages=[{'role':'system','content':system}, {'role':'user','content':assistant_prompt}],
                max_tokens=400,
                temperature=0.2,
            )
            answer = chat_resp['choices'][0]['message']['content']
        except Exception as e:
            print('OpenAI chat error:', e)
            return jsonify({'error': str(e)}), 500

        return jsonify({'answer': answer, 'retrieved': len(retrieved_texts)})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)