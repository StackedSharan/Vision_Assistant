# backend/app.py (With Detailed Debugging)

# ... (all your imports are the same) ...
# --- Path Hack and Imports ---
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask, jsonify, request
from flask_cors import CORS
import cv2, numpy as np, base64, io
from PIL import Image
from backend.modules.object_detection import ObjectDetector
from backend.modules.voice_assistant import VoiceAssistant
from backend.modules.navigator import Navigator

# ... (Initialization is the same) ...
app = Flask(__name__)
CORS(app)
# ... (loading models is the same) ...
detector = ObjectDetector()
# ... etc ...

# ... (get_route endpoint is the same) ...

# --- MODIFIED OBSTACLE CHECKER ENDPOINT ---
@app.route('/api/check_obstacle', methods=['POST'])
def check_obstacle():
    data = request.get_json()
    if not data or 'image' not in data:
        return jsonify({'obstacles': []})

    try:
        image_data = base64.b64decode(data['image'])
        image = Image.open(io.BytesIO(image_data))
        frame = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)

        # --- THIS IS THE NEW DEBUGGING PART ---
        # 1. Run detection with a LOWER threshold for debugging
        all_detections = detector.detect(frame, threshold=0.4) 
        
        # 2. Print EVERYTHING the model found
        print("\n-------------------------------------------")
        print(f"--- All Detections Found (Threshold > 0.4): {all_detections} ---")
        print("-------------------------------------------\n")
        # --- END OF DEBUGGING PART ---

        obstacles = []
        for det in all_detections:
            # We still only alert for significant obstacles with high confidence
            if det['name'] in ['person', 'car', 'bicycle', 'motorcycle', 'bus', 'truck'] and det['score'] > 0.6:
                obstacles.append(det['name'])
        
        return jsonify({'obstacles': obstacles})

    except Exception as e:
        print(f"Error in check_obstacle: {e}")
        return jsonify({'obstacles': []})

# ... (the rest of the file is the same) ...
if __name__ == '__main__':
    # ... (code to run the app is the same) ...
    print("Starting Flask server...")
    app.run(host='0.0.0.0', port=5001, debug=False)