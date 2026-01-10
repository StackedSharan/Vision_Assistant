"""
Object Detector - YOLO and TensorFlow Lite integration
Detects obstacles, people, vehicles for navigation and safety
"""
import cv2
import numpy as np
import os
import base64
from .distance import KNOWN_WIDTHS, estimate_distance, classify_urgency

# Try to import ultralytics for YOLOv8
try:
    from ultralytics import YOLO
    HAS_YOLO = True
except ImportError:
    HAS_YOLO = False
    print("⚠️ Warning: ultralytics (YOLO) not found. Will fallback to TFLite.")

# Try to import tensorflow for TFLite
try:
    import tensorflow as tf
    HAS_TFLITE = True
except ImportError:
    HAS_TFLITE = False
    print("⚠️ Warning: tensorflow not found.")

class ObjectDetector:
    """
    Detects objects in images using YOLO (preferred) or TensorFlow Lite
    Returns list of detections with: name, confidence, distance, urgency, position_x
    """
    
    def __init__(self, mode='yolo', model_path=None):
        """
        Initialize detector with specified mode
        Args:
            mode: 'yolo' or 'tflite'
            model_path: Optional custom model path
        """
        self.mode = mode
        self.model = None
        self.interpreter = None
        self.labels = []
        
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(current_dir)
        
        # Try YOLO first
        if mode == 'yolo' and HAS_YOLO:
            yolo_path = model_path or os.path.join(backend_dir, 'yolov8n.pt')
            if os.path.exists(yolo_path):
                try:
                    self.model = YOLO(yolo_path)
                    print(f"✅ YOLOv8 loaded: {yolo_path}")
                except Exception as e:
                    print(f"❌ YOLO load error: {e}. Trying TFLite...")
                    self.mode = 'tflite'
            else:
                print(f"❌ YOLO model not found: {yolo_path}")
                self.mode = 'tflite'
        
        # Fallback to TFLite
        if self.mode == 'tflite' and HAS_TFLITE:
            tflite_path = model_path or os.path.join(backend_dir, 'models', 'ssd_mobilenet_v2.tflite')
            label_path = os.path.join(backend_dir, 'models', 'coco_labels.txt')
            
            if os.path.exists(tflite_path) and os.path.exists(label_path):
                try:
                    self.interpreter = tf.lite.Interpreter(model_path=tflite_path)
                    self.interpreter.allocate_tensors()
                    self.input_details = self.interpreter.get_input_details()
                    self.output_details = self.interpreter.get_output_details()
                    
                    input_shape = self.input_details[0]['shape']
                    self.height = input_shape[1]
                    self.width = input_shape[2]
                    
                    with open(label_path, 'r') as f:
                        self.labels = [line.strip() for line in f.readlines()]
                    
                    print(f"✅ TFLite loaded: {tflite_path}")
                except Exception as e:
                    print(f"❌ TFLite load error: {e}")
            else:
                print(f"❌ TFLite files not found")
        
        if not self.model and not self.interpreter:
            print("⚠️ No detector available. Detection will return empty results.")
    
    def detect(self, image_input):
        """
        Detect objects in image
        Args:
            image_input: numpy array OR base64 string
        Returns:
            List of detections: [{'name': str, 'confidence': float, 'distance': float, 
                                 'urgency': str, 'position_x': float}, ...]
        """
        # Handle base64 input
        if isinstance(image_input, str):
            try:
                encoded_data = image_input.split(',')[1] if ',' in image_input else image_input
                img_array = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
                frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
            except Exception as e:
                print(f"❌ Image decode error: {e}")
                return []
        else:
            frame = image_input
        
        if frame is None or frame.size == 0:
            return []
        
        if self.mode == 'yolo' and self.model:
            return self._detect_yolo(frame)
        elif self.mode == 'tflite' and self.interpreter:
            return self._detect_tflite(frame)
        else:
            return []
    
    def _detect_yolo(self, frame):
        """Detect using YOLOv8"""
        try:
            results = self.model(frame, verbose=False)[0]
            detections = []
            
            for box in results.boxes:
                cls_id = int(box.cls[0])
                label = results.names[cls_id]
                conf = float(box.conf[0])
                
                # Filter by confidence
                if conf < 0.4:
                    continue
                
                # Calculate position
                x1, y1, x2, y2 = box.xyxy[0]
                center_x = (x1 + x2) / 2.0 / frame.shape[1]
                pixel_width = float(x2 - x1)
                
                detection = {
                    'name': label,
                    'confidence': conf,
                    'position_x': float(center_x),
                    'distance': None,
                    'urgency': 'safe'
                }
                
                # Estimate distance if model available
                if label in KNOWN_WIDTHS:
                    dist = estimate_distance(pixel_width, KNOWN_WIDTHS[label])
                    detection['distance'] = dist
                    detection['urgency'] = classify_urgency(dist)
                
                detections.append(detection)
            
            return sorted(detections, key=lambda x: x.get('distance') or 999)
        
        except Exception as e:
            print(f"❌ YOLO detection error: {e}")
            return []
    
    def _detect_tflite(self, frame):
        """Detect using TensorFlow Lite"""
        try:
            # Preprocess
            input_image = cv2.resize(frame, (self.width, self.height))
            input_data = np.expand_dims(input_image, axis=0).astype(np.uint8)
            
            # Run inference
            self.interpreter.set_tensor(self.input_details[0]['index'], input_data)
            self.interpreter.invoke()
            
            # Extract outputs
            boxes = self.interpreter.get_tensor(self.output_details[0]['index'])[0]
            classes = self.interpreter.get_tensor(self.output_details[1]['index'])[0]
            scores = self.interpreter.get_tensor(self.output_details[2]['index'])[0]
            
            detections = []
            for i in range(len(scores)):
                if scores[i] > 0.4:
                    class_id = int(classes[i])
                    if class_id < len(self.labels):
                        label = self.labels[class_id]
                        
                        # Get box coordinates
                        box = boxes[i]
                        h, w, _ = frame.shape
                        y1, x1, y2, x2 = box
                        x1, y1, x2, y2 = int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h)
                        
                        center_x = (x1 + x2) / 2.0 / w
                        pixel_width = x2 - x1
                        
                        detection = {
                            'name': label,
                            'confidence': float(scores[i]),
                            'position_x': float(center_x),
                            'distance': None,
                            'urgency': 'safe'
                        }
                        
                        if label in KNOWN_WIDTHS:
                            dist = estimate_distance(pixel_width, KNOWN_WIDTHS[label])
                            detection['distance'] = dist
                            detection['urgency'] = classify_urgency(dist)
                        
                        detections.append(detection)
            
            return sorted(detections, key=lambda x: x.get('distance') or 999)
        
        except Exception as e:
            print(f"❌ TFLite detection error: {e}")
            return []
