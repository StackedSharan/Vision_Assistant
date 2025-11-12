# backend/modules/landmark_recognizer.py (FINAL CORRECTED VERSION)

import tensorflow as tf
import numpy as np
import cv2

class LandmarkRecognizer:
    def __init__(self, model_path, labels_path):
        """
        Initializes the landmark recognizer by loading the TFLite model and labels.
        """
        self.labels = self._load_labels(labels_path)
        
        # Load the TFLite model and allocate tensors.
        self.interpreter = tf.lite.Interpreter(model_path=model_path)
        self.interpreter.allocate_tensors()

        # Get model input and output details.
        self.input_details = self.interpreter.get_input_details()
        self.output_details = self.interpreter.get_output_details()
        
        # Get the expected input size from the model
        _, self.height, self.width, _ = self.input_details[0]['shape']

        print(f"✅ Landmark Recognizer initialized. Expecting {self.height}x{self.width} images.")
        print(f"   Labels loaded: {self.labels}")

    def _load_labels(self, path):
        """Loads labels from a text file."""
        with open(path, 'r') as f:
            return [line.strip() for line in f.readlines()]

    def predict_landmark(self, image_frame):
        """
        Takes a single image frame (from OpenCV) and returns the predicted landmark.
        """
        # 1. Pre-process the image to match the model's input requirements
        # Resize the image
        input_image = cv2.resize(image_frame, (self.width, self.height))
        
        # Convert the image to FLOAT32 and normalize pixel values to be between 0 and 1.
        # This is the crucial step that fixes the data type mismatch.
        input_image = np.asarray(input_image, dtype=np.float32) / 255.0
        
        # Add a batch dimension because the model expects a list of images
        input_data = np.expand_dims(input_image, axis=0)
        
        # 2. Set the image data as the model's input
        self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
        
        # 3. Run the prediction
        self.interpreter.invoke()
        
        # 4. Get the results
        output_data = self.interpreter.get_tensor(self.output_details[0]['index'])
        scores = output_data[0]
        
        # 5. Find the best prediction
        predicted_index = np.argmax(scores)
        predicted_landmark = self.labels[predicted_index]
        confidence = float(scores[predicted_index])
        
        return (predicted_landmark, confidence)