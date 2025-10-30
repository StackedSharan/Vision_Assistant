# test_object_detection.py (FINAL, CORRECTED VERSION 2)

import cv2
from backend.modules.object_detection import ObjectDetector
import numpy as np

# --- We need to slightly modify the detector to give us box coordinates ---
# Let's redefine the detect function inside the class for this test
def detect_with_boxes(self, frame, threshold=0.5):
    image_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    imH, imW, _ = frame.shape
    image_resized = cv2.resize(image_rgb, (self.width, self.height))
    input_data = np.expand_dims(image_resized, axis=0)

    self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
    self.interpreter.invoke()

    boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
    classes = self.interpreter.get_tensor(self.output_details[1]['index'])[0]
    scores = self.interpreter.get_tensor(self.output_details[2]['index'])[0]

    results = []
    for i in range(len(scores)):
        if ((scores[i] > threshold) and (scores[i] <= 1.0)):
            object_name = self.labels[int(classes[i])]
            
            ymin = int(max(1, (boxes[i][0] * imH)))
            xmin = int(max(1, (boxes[i][1] * imW)))
            ymax = int(min(imH, (boxes[i][2] * imH)))
            xmax = int(min(imW, (boxes[i][3] * imW)))
            
            results.append({'name': object_name, 'box': [xmin, ymin, xmax, ymax]})
    return results

# Replace the original detect method with our new one for this test
ObjectDetector.detect = detect_with_boxes
# --- End of modification ---


# Initialize the detector
detector = ObjectDetector()

# Initialize the webcam
cap = cv2.VideoCapture(0)

if not cap.isOpened():
    print("Error: Could not open video stream.")
    exit()

while True:
    ret, frame = cap.read()
    if not ret:
        break

    detections = detector.detect(frame, threshold=0.6)
    
    for detection in detections:
        box = detection['box']
        name = detection['name']
        
        cv2.rectangle(frame, (box[0], box[1]), (box[2], box[3]), (10, 255, 0), 2)
        
        label = f"{name}"
        # --- THIS IS THE CORRECTED LINE ---
        cv2.putText(frame, label, (box[0], box[1] - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)

    cv2.imshow('Object Detection', frame)

    if cv2.waitKey(1) & 0xFF == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()