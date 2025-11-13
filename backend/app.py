from flask import Flask
from flask_socketio import SocketIO, emit
import base64
import cv2
import numpy as np
import os
import tensorflow as tf
from modules.navigator import Navigator

# --- Object Detector Class ---
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
                
                ### MODIFIED ### - Calculate the horizontal center of the object
                # xmax and xmin are proportions (0.0 to 1.0) of the image width.
                center_x = (xmin + xmax) / 2.0
                
                object_pixel_width = int((xmax - xmin) * image_width)
                distance = (self.KNOWN_WIDTHS[object_name] * self.CALIBRATED_FOCAL_LENGTH) / object_pixel_width
                
                ### MODIFIED ### - Add the position to the returned data
                detections.append({'name': object_name, 'distance': float(distance), 'position_x': float(center_x)})
                
        return detections

# --- SETUP AND INITIALIZATION ---
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")
object_detector = ObjectDetector()
navigator = Navigator(map_path=os.path.join(os.path.dirname(os.path.abspath(__file__)), 'models', 'map.geojson'))
print("✅ Navigator Initialized.")


### MODIFIED ### - New helper function to get a direction label
def get_position_label(x_coordinate):
    """
    Takes a horizontal coordinate (from 0.0 to 1.0) and returns a human-readable position.
    """
    if x_coordinate < 0.35:
        return "to your left"
    elif x_coordinate > 0.65:
        return "to your right"
    else:
        return "in front of you"

### MODIFIED ### - The "brain" is now smarter
def generate_summary(objects):
    """
    Turns a list of objects (which now include position) into a human-like sentence.
    """
    if not objects:
        return "The path ahead looks clear."

    objects.sort(key=lambda x: x['distance'])
    
    closest_obj = objects[0]
    position_text = get_position_label(closest_obj['position_x'])
    
    # Create the main description with direction
    summary = f"I see a {closest_obj['name']} {position_text}, about {closest_obj['distance']:.1f} meters away."
    
    # Mention other objects if they exist
    if len(objects) > 1:
        # We don't need to add directional info for every other object to keep it simple
        other_object_names = [obj['name'] for obj in objects[1:]]
        if len(other_object_names) > 1:
            other_objects_str = ", a ".join(other_object_names[:-1]) + f", and a {other_object_names[-1]}"
        else:
            other_objects_str = f"a {other_object_names[0]}"
        summary += f" There is also {other_objects_str} nearby."

    return summary

def decode_image_from_data_url(data_url):
    """Decodes a Base64 image data URL into an OpenCV image."""
    encoded_data = data_url.split(',')[1]
    nparr = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img

# --- SOCKETIO EVENTS ---
@socketio.on('connect')
def handle_connect():
    print('✅ Client connected')

@socketio.on('describe_scene')
def handle_describe_scene(json_data):
    """
    The main event handler, now uses the smarter generate_summary function.
    """
    print("Received 'describe_scene' request.")
    try:
        image_frame = decode_image_from_data_url(json_data['image'])
        detected_objects = object_detector.detect(image_frame)
        summary_text = generate_summary(detected_objects)
        
        emit('scene_summary', {'summary': summary_text})
        print(f"Sent summary: {summary_text}")
    except Exception as e:
        print(f"An error occurred in describe_scene: {e}")
        emit('scene_summary', {'summary': 'Sorry, an error occurred while analyzing the scene.'})

# --- Your previous event handlers are still here, just in case ---
@socketio.on('get_navigation')
def handle_get_navigation(data):
    start = data.get('start')
    end = data.get('end')
    instructions = navigator.find_shortest_path(start, end)
    if instructions:
        emit('navigation_response', {'instructions': instructions})
    else:
        emit('navigation_response', {'error': f"Could not find a route from {start} to {end}."})

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)