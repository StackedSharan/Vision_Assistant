import cv2
import numpy as np
import os
from .distance import KNOWN_WIDTHS, estimate_distance, classify_urgency

# Try to import ultralytics for YOLOv8
try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    print("Warning: ultralytics (YOLO) not found. Falling back to TFLite if available.")

# Try to import tensorflow for TFLite
try:
    import tensorflow as tf
    HAS_TFLITE = True
except ImportError:
    HAS_TFLITE = False
    print("Warning: tensorflow not found.")

class ObjectDetector:
    def __init__(self, mode='yolo', model_path=None):
        self.mode = mode
        self.model = None
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(current_dir)
        
        if mode == 'yolo' and HAS_YOLO:
            yolo_path = model_path or os.path.join(backend_dir, 'yolov8n.pt')
            if os.path.exists(yolo_path):
                self.model = YOLO(yolo_path)
                print(f"✅ YOLOv8 initialized from {yolo_path}")
            else:
                print(f"!!! YOLO model not found at {yolo_path}. Falling back to TFLite.")
                self.mode = 'tflite'
        
        if self.mode == 'tflite' and HAS_TFLITE:
            tflite_path = model_path or os.path.join(backend_dir, 'models', 'ssd_mobilenet_v2.tflite')
            label_path = os.path.join(backend_dir, 'models', 'coco_labels.txt')
            
            if os.path.exists(tflite_path):
                self.interpreter = tf.lite.Interpreter(model_path=tflite_path)
                self.interpreter.allocate_tensors()
                self.input_details = self.interpreter.get_input_details()
                self.output_details = self.interpreter.get_output_details()
                _, self.height, self.width, _ = self.input_details[0]['shape']
                
                with open(label_path, 'r') as f:
                    self.labels = [line.strip() for line in f.readlines()]
                print(f"✅ TFLite initialized from {tflite_path}")
            else:
                print(f"!!! TFLite model not found at {tflite_path}")

    def detect(self, frame):
        if self.mode == 'yolo' and self.model:
            results = self.model(frame, verbose=False)[0]
            detections = []
            for box in results.boxes:
                cls_id = int(box.cls[0])
                label = results.names[cls_id]
                conf = float(box.conf[0])
                
                if conf < 0.4: continue
                
                x1, y1, x2, y2 = box.xyxy[0]
                center_x = (x1 + x2) / 2 / frame.shape[1]
                
                res = {
                    'name': label, 
                    'confidence': conf,
                    'position_x': float(center_x)
                }
                
                if label in KNOWN_WIDTHS:
                    pixel_width = float(x2 - x1)
                    dist = estimate_distance(pixel_width, KNOWN_WIDTHS[label])
                    res['distance'] = dist
                    res['urgency'] = classify_urgency(dist)
                
                detections.append(res)
            return detections
            
        elif self.mode == 'tflite' and hasattr(self, 'interpreter'):
            # Existing TFLite logic refactored
            h, w, _ = frame.shape
            input_image = cv2.resize(frame, (self.width, self.height))
            input_data = np.expand_dims(input_image, axis=0)
            
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            self.interpreter.invoke()
            
            boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
            classes = self.interpreter.get_tensor(self.output_details[1]['index'])[0]
            scores = self.interpreter.get_tensor(self.output_details[2]['index'])[0]
            
            detections = []
            for i in range(len(scores)):
                if scores[i] > 0.4:
                    label = self.labels[int(classes[i])]
                    ymin, xmin, ymax, xmax = boxes[i]
                    center_x = (xmin + xmax) / 2 # TFLite boxes are already normalized 0-1
                    
                    res = {
                        'name': label, 
                        'confidence': float(scores[i]),
                        'position_x': float(center_x)
                    }
                    
                    if label in KNOWN_WIDTHS:
                        pixel_width = (xmax - xmin) * w
                        dist = estimate_distance(pixel_width, KNOWN_WIDTHS[label])
                        res['distance'] = dist
                        res['urgency'] = classify_urgency(dist)
                    
                    detections.append(res)
            return detections
            
        return []
