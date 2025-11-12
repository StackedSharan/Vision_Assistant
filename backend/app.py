# backend/app.py (FINAL VERSION with Navigation)

from flask import Flask, request
from flask_cors import CORS
import base64
import cv2
import numpy as np
import os

# --- Import your custom AI modules ---
from modules.landmark_recognizer import LandmarkRecognizer
from modules.navigator import Navigator # <-- IMPORT THE NAVIGATOR

# --- SETUP FLASK APP ---
app = Flask(__name__)
CORS(app) 

# --- INITIALIZE AI MODULES ---
print("--- Initializing AI modules... ---")

# This makes our file paths robust and independent of where the script is run from
base_dir = os.path.dirname(os.path.abspath(__file__))

# 1. Initialize the Landmark Recognizer
try:
    model_path = os.path.join(base_dir, 'models', 'model.tflite')
    labels_path = os.path.join(base_dir, 'models', 'labels.txt')
    landmark_recognizer = LandmarkRecognizer(model_path=model_path, labels_path=labels_path)
except Exception as e:
    print(f"!!! CRITICAL ERROR: Could not initialize LandmarkRecognizer: {e}")
    landmark_recognizer = None

# 2. Initialize the Navigator
try:
    map_path = os.path.join(base_dir, 'models', 'map.geojson')
    navigator = Navigator(map_path=map_path)
except Exception as e:
    print(f"!!! CRITICAL ERROR: Could not initialize Navigator: {e}")
    navigator = None

print("--- All modules initialized. Server is ready. ---")


# --- API ENDPOINTS ---

@app.route('/api/confirm_position', methods=['POST'])
def confirm_position():
    # ... (This endpoint is complete and correct)
    if not landmark_recognizer:
        return {'error': 'Landmark Recognizer is not available.'}, 500
    try:
        # ... (rest of the function)
        image_b64 = request.json['image']
        image_bytes = base64.b64decode(image_b64.split(',')[1])
        np_arr = np.frombuffer(image_bytes, np.uint8)
        image_frame = cv2.imdecode(np_arr, cv2.IMREAD_COLOR)
        if image_frame is None: return {'error': 'Failed to decode image.'}, 400
        landmark, confidence = landmark_recognizer.predict_landmark(image_frame)
        return {'landmark': landmark, 'confidence': float(confidence)}
    except Exception as e:
        print(f"Error during position confirmation: {e}")
        return {'error': 'An internal error occurred.'}, 500

# --- THIS IS THE NEW, FULLY IMPLEMENTED ENDPOINT ---
@app.route('/api/start_navigation', methods=['POST'])
def start_navigation():
    """
    Receives a start and end landmark, uses the Navigator to find a route,
    and returns a list of instructions.
    """
    if not navigator:
        return {'error': 'Navigation module is not available.'}, 500

    data = request.json
    start_landmark = data.get('start_landmark')
    end_landmark = data.get('end_landmark')

    if not start_landmark or not end_landmark:
        return {'error': 'A start and end landmark are required.'}, 400
    
    print(f"Route requested from '{start_landmark}' to '{end_landmark}'")

    try:
        # Use the navigator module to find the path
        instructions = navigator.find_shortest_path(start_landmark, end_landmark)
        
        if not instructions:
            # This can happen if one of the landmark names doesn't exist in the map
            error_message = f"Could not find a path. Make sure '{start_landmark}' and '{end_landmark}' exist in the map.geojson file."
            print(f"ERROR: {error_message}")
            return {'error': error_message}, 404

        print(f"Route found: {instructions}")
        return {'instructions': instructions}

    except Exception as e:
        print(f"An error occurred in the navigator: {e}")
        return {'error': 'An internal server error occurred while calculating the route.'}, 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)