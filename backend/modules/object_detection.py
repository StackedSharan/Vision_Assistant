# backend/modules/object_detection.py (FINAL VERSION)

import cv2
import numpy as np
import tensorflow as tf
import os

class ObjectDetector:
    def __init__(self, model_path='backend/models/ssd_mobilenet_v2.tflite', label_path='backend/models/coco_labels.txt'):
        """Initializes the object detector with a TFLite model and labels."""

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
        """
        Takes a single frame (image) and returns a list of detected objects.
        """
        image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        imH, imW, _ = frame.shape
        image_resized = cv2.resize(image_rgb, (self.width, self.height))
        input_data = np.expand_dims(image_resized, axis=0)

        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        self.interpreter.invoke()

        # The model we are using has this specific output order.
        boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
        classes = self.interpreter.get_tensor(self.output_details[1]['index'])[0]
        scores = self.interpreter.get_tensor(self.output_details[2]['index'])[0]

        detections = []

        for i in range(len(scores)):
            if ((scores[i] > threshold) and (scores[i] <= 1.0)):
                object_name = self.labels[int(classes[i])]
                description = f"{object_name} detected."
                detections.append(description)

        return detections