from flask import Flask
from flask_socketio import SocketIO, emit
import base64
import cv2
import numpy as np
import os
from modules.navigator import Navigator
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
from ultralytics import YOLO

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
        critical_objects = [d for d in detections if d['distance'] < 3.0] # Only objects within 3 meters
        
        if critical_objects:
            summary = generate_summary(critical_objects)
            emit('obstacle_alert', {'message': summary})
        else:
            emit('obstacle_alert', {'message': 'Path is clear.'})
            
    except Exception as e:
        print(f"Error processing frame: {e}")

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

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)