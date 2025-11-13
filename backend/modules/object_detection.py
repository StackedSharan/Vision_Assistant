# backend/modules/object_detection.py (FINAL VERSION WITH DISTANCE ESTIMATION)

import cv2
import numpy as np
import tensorflow as tf
import os

# --- CONFIGURATION ---
# You need to calibrate this value for your specific phone camera.
# See the calibration instructions in the main response. A typical phone is 500-800.
CALIBRATED_FOCAL_LENGTH = 600 # Pixels

# Define the approximate real-world widths of objects we care about (in meters)
KNOWN_WIDTHS = {
    "person": 0.5,
    "car": 1.8,
    "bicycle": 0.6,
    "motorcycle": 0.8,
    "bus": 2.5,
    "truck": 2.6
}

def estimate_distance(pixel_width, real_width, focal_length):
    """Calculates the distance to an object."""
    if pixel_width == 0:
        return float('inf')
    return (real_width * focal_length) / pixel_width

class ObjectDetector:
    def __init__(self, model_filename='ssd_mobilenet_v2.tflite', label_filename='coco_labels.txt'):
        module_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(module_dir)
        model_path = os.path.join(backend_dir, 'models', model_filename)
        label_path = os.path.join(backend_dir, 'models', label_filename)
        
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        _, self.height, self.width, _ = self.input_details[0]['shape']

        try:
            with open(label_path, 'r') as f:
                self.labels = [line.strip() for line in f.readlines()]
            print("✅ Object Detector initialized.")
        except FileNotFoundError:
            print(f"!!! CRITICAL ERROR: Labels file not found at {label_path}")
            self.labels = []

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
            if scores[i] > 0.5:
                object_name = self.labels[int(classes[i])]
                
                detection = {
                    'name': object_name,
                    'confidence': float(scores[i]),
                }

                # --- NEW DISTANCE LOGIC ---
                if object_name in KNOWN_WIDTHS:
                    # De-normalize bounding box coordinates to get pixel values
                    ymin, xmin, ymax, xmax = boxes[i]
                    pixel_xmin = int(xmin * image_width)
                    pixel_xmax = int(xmax * image_width)
                    object_pixel_width = pixel_xmax - pixel_xmin
                    
                    # Estimate the distance
                    distance = estimate_distance(object_pixel_width, KNOWN_WIDTHS[object_name], CALIBRATED_FOCAL_LENGTH)
                    detection['distance'] = float(distance) # Add distance to our results
                
                detections.append(detection)
        
        return detections