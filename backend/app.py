from flask import Flask
from flask_socketio import SocketIO, emit
import base64
import cv2
import numpy as np
import os
import tensorflow as tf
from modules.navigator import Navigator
from geopy.geocoders import Nominatim
from geopy.distance import geodesic

# --- Object Detector Class (Unchanged) ---
class ObjectDetector:
    def __init__(self, model_filename='ssd_mobilenet_v2.tflite', label_filename='coco_labels.txt'):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        model_path = os.path.join(base_dir, 'models', model_filename)
        label_path = os.path.join(base_dir, 'models', label_filename)
        self.CALIBRATED_FOCAL_LENGTH = 600
        self.KNOWN_WIDTHS = {"person": 0.5, "car": 1.8, "bicycle": 0.6, "bottle": 0.07}
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        _, self.height, self.width, _ = self.input_details[0]['shape']
        with open(label_path, 'r') as f:
            self.labels = [line.strip() for line in f.readlines()]
        print("✅ Object Detector Initialized.")

    def detect(self, image_frame):
        # ... (Your existing detection logic remains unchanged) ...
        image_height, image_width, _ = image_frame.shape
        input_image = cv2.resize(image_frame, (self.width, self.height))
        input_data = np.expand_dims(input_image, axis=0)
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()
        boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
        classes = self.interpreter.get_tensor(self.output_details[1]['index'])[0]
        scores = self.interpreter.get_tensor(self.output_details[2]['index'])[0]
        detections = []
        for i in range(len(scores)):
            if scores[i] > 0.5 and int(classes[i]) < len(self.labels) and self.labels[int(classes[i])] in self.KNOWN_WIDTHS:
                object_name = self.labels[int(classes[i])]
                ymin, xmin, ymax, xmax = boxes[i]
                center_x = (xmin + xmax) / 2.0
                object_pixel_width = int((xmax - xmin) * image_width)
                distance = (self.KNOWN_WIDTHS[object_name] * self.CALIBRATED_FOCAL_LENGTH) / object_pixel_width
                detections.append({'name': object_name, 'distance': float(distance), 'position_x': float(center_x)})
        return detections

# --- SETUP AND INITIALIZATION ---
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
object_detector = ObjectDetector()
navigator = Navigator(map_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'map.geojson'))
print("✅ Navigator Initialized.")

# --- NEW GPS FEATURE SETUP ---
geolocator = Nominatim(user_agent="vision_assistant")
# IMPORTANT: Replace these coordinates with the center of YOUR campus/map area
CAMPUS_CENTER = (12.9716, 77.5946) # Example: Bangalore, India.
CAMPUS_RADIUS_METERS = 500
user_is_in_geofence = None # Use None to handle the very first check

def get_position_label(x_coordinate):
    # ... (Your existing helper function remains unchanged) ...
    if x_coordinate < 0.35: return "to your left"
    elif x_coordinate > 0.65: return "to your right"
    else: return "in front of you"

def generate_summary(objects):
    # ... (Your existing helper function remains unchanged) ...
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
    # ... (Your existing helper function remains unchanged) ...
    encoded_data = data_url.split(',')[1]
    nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

# --- SOCKETIO EVENTS ---
@socketio.on('connect')
def handle_connect():
    print('✅ Client connected')

# --- Existing Vision and Navigation Handlers (Unchanged) ---
@socketio.on('describe_scene')
def handle_describe_scene(json_data):
    # ... (Your existing handler) ...
    image_frame = decode_image_from_data_url(json_data['image'])
    detected_objects = object_detector.detect(image_frame)
    summary_text = generate_summary(detected_objects)
    emit('scene_summary', {'summary': summary_text})

@socketio.on('get_navigation')
def handle_get_navigation(data):
    # ... (Your existing handler) ...
    instructions = navigator.find_shortest_path(data.get('start'), data.get('end'))
    if instructions:
        emit('navigation_response', {'instructions': instructions})
    else:
        emit('navigation_response', {'error': f"Could not find a route."})

# --- NEW GPS EVENT HANDLERS ---
@socketio.on('location_update')
def handle_location_update(data):
    """Handles automatic geofence detection."""
    global user_is_in_geofence
    user_coords = (data['latitude'], data['longitude'])
    distance_to_center = geodesic(user_coords, CAMPUS_CENTER).meters
    is_currently_inside = distance_to_center < CAMPUS_RADIUS_METERS
    
    # Check if the state has changed since the last update
    if is_currently_inside != user_is_in_geofence:
        user_is_in_geofence = is_currently_inside
        if is_currently_inside:
            emit('context_update', {'message': 'Welcome to campus. Navigation Mode is now available.'})
        else:
            emit('context_update', {'message': 'You have left the campus area.'})

@socketio.on('where_am_i')
def handle_where_am_i(data):
    """Handles the on-demand "Where Am I?" query."""
    user_coords = (data['latitude'], data['longitude'])
    try:
        location = geolocator.reverse(user_coords, exactly_one=True, language='en')
        address = location.address if location else "an unknown location."
        emit('location_query_response', {'address': f"You are near {address}"})
    except Exception as e:
        emit('location_query_response', {'address': "Sorry, I could not determine your current location."})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)