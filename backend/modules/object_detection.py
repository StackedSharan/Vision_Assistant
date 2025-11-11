# backend/modules/object_detection.py (FINAL - ALL-IN-ONE VERSION)

import cv2
import numpy as np
import tensorflow as tf
import os

# --- THE DISTANCE ESTIMATION CODE IS NOW INSIDE THIS FILE ---

# The focal length you calculated. Please double-check this value.
FOCAL_LENGTH = 833 

# An approximate width in meters for objects in the COCO dataset.
KNOWN_WIDTHS = {
    "person": 0.5, "bicycle": 0.5, "car": 1.8, "motorcycle": 0.8,
    "bus": 3.0, "truck": 3.2, "traffic light": 0.3, "stop sign": 0.75,
    "fire hydrant": 0.3, "backpack": 0.35, "umbrella": 0.4, "handbag": 0.3,
    "tie": 0.1, "suitcase": 0.45, "bottle": 0.07, "cup": 0.08,
    "laptop": 0.35, "cell phone": 0.08, "book": 0.15, "clock": 0.2,
    "chair": 0.5, "couch": 1.8, "potted plant": 0.3, "tv": 1.2
}

def estimate_distance(object_name, pixel_width):
    """Estimates the distance to an object based on its known width."""
    if object_name in KNOWN_WIDTHS:
        known_width = KNOWN_WIDTHS[object_name]
        distance_meters = (known_width * FOCAL_LENGTH) / pixel_width
        return distance_meters
    return None

# --- END OF DISTANCE ESTIMATION CODE ---


class ObjectDetector:
    def __init__(self, model_path='backend/models/ssd_mobilenet_v2.tflite', label_path='backend/models/coco_labels.txt'):
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"TFLite model not found at: {model_path}")
        if not os.path.exists(label_path):
            raise FileNotFoundError(f"Label file not found at: {label_path}")
        with open(label_path, 'r') as f:
            self.labels = [line.strip() for line in f.readlines()]
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        self.height = self.input_details[0]['shape'][1]
        self.width = self.input_details[0]['shape'][2]

    def detect(self, frame, threshold=0.5):
        imH, imW, _ = frame.shape
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        image_resized = cv2.resize(image_rgb, (self.width, self.height))
        input_data = np.expand_dims(image_resized, axis=0)
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()

        boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
        classes = self.interpreter.get_tensor(self.output_details[1]['index'])[0]
        scores = self.interpreter.get_tensor(self.output_details[2]['index'])[0]
        
        detections_with_details = []
        for i in range(len(scores)):
            if scores[i] > threshold:
                object_name = self.labels[int(classes[i])]
                ymin = int(max(1, (boxes[i][0] * imH)))
                xmin = int(max(1, (boxes[i][1] * imW)))
                ymax = int(min(imH, (boxes[i][2] * imH)))
                xmax = int(min(imW, (boxes[i][3] * imW)))
                pixel_width = xmax - xmin
                
                # This function call now works because the function is in the same file
                distance = estimate_distance(object_name, pixel_width)
                
                detection_info = {
                    "name": object_name,
                    "score": float(scores[i]),
                    "distance_meters": distance,
                    "box": [xmin, ymin, xmax, ymax]
                }
                detections_with_details.append(detection_info)
        return detections_with_details