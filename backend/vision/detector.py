"""
Object Detector - YOLO and TensorFlow Lite integration
Detects obstacles, people, vehicles for navigation and safety
"""
import cv2
import numpy as np
import os
import base64
from .distance import KNOWN_WIDTHS, ALERT_CLASSES, estimate_distance, classify_urgency

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
        """Detect using YOLOv8 with real-time optimization"""
        try:
            # Aggressive frame resizing for speed (480p max)
            h, w = frame.shape[:2]
            if w > 480:
                scale = 480 / w
                frame = cv2.resize(frame, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_LINEAR)
            
            # Fast inference with reduced confidence threshold
            results = self.model(frame, verbose=False, conf=0.25)[0]
            detections = []
            
            for box in results.boxes:
                cls_id = int(box.cls[0])
                label = results.names[cls_id].lower()
                conf = float(box.conf[0])
                
                # Accept objects with lower confidence for real-time detection
                if conf < 0.25:
                    continue
                
                # Map object names to standardized names
                label = self._normalize_label(label)
                
                # Calculate position and size
                x1, y1, x2, y2 = box.xyxy[0]
                center_x = (x1 + x2) / 2.0 / frame.shape[1]
                pixel_width = float(x2 - x1)
                pixel_height = float(y2 - y1)
                
                # Filter out very small noise (less than 3 pixels)
                if pixel_width < 3 or pixel_height < 3:
                    continue
                
                detection = {
                    'name': label,
                    'confidence': round(conf, 2),
                    'position_x': round(float(center_x), 2),
                    'distance': None,
                    'urgency': 'SAFE',
                    'box': {
                        'x1': float(x1),
                        'y1': float(y1),
                        'x2': float(x2),
                        'y2': float(y2)
                    }
                }
                
                # Estimate distance for known objects
                if label in KNOWN_WIDTHS:
                    dist = estimate_distance(pixel_width, KNOWN_WIDTHS[label])
                    detection['distance'] = round(dist, 2)
                    detection['urgency'] = classify_urgency(dist)
                
                detections.append(detection)
            
            # Sort by distance (nearest first)
            detections = sorted(detections, 
                              key=lambda x: x.get('distance') or 999)
            
            return detections
        
        except Exception as e:
            print(f"❌ YOLO detection error: {e}")
            return []
    
    def _normalize_label(self, label):
        """Normalize object labels to match KNOWN_WIDTHS keys.
        
        Maps various YOLO output labels to standardized names for distance estimation.
        """
        label = label.strip().lower()
        
        # Direct mappings for common variations
        label_mappings = {
            # Phones/Mobile
            'cell phone': 'cell phone',
            'cellphone': 'cell phone',
            'mobile': 'mobile phone',
            'mobile phone': 'mobile phone',
            'iphone': 'cell phone',
            'smartphone': 'cell phone',
            'phone': 'cell phone',
            
            # People/Body parts
            'person': 'person',
            'human': 'person',
            'people': 'person',
            'man': 'person',
            'woman': 'person',
            'child': 'person',
            'adult': 'person',
            'hand': 'hand',
            'hands': 'hand',
            'face': 'face',
            'head': 'head',
            'arm': 'arm',
            'leg': 'leg',
            'body': 'person',
            
            # Containers/Bottles
            'bottle': 'bottle',
            'bottles': 'bottle',
            'water bottle': 'bottle',
            'wine bottle': 'bottle',
            'cup': 'cup',
            'cups': 'cup',
            'mug': 'cup',
            'glass': 'cup',
            'can': 'bottle',
            
            # Electronics/Computers
            'keyboard': 'keyboard',
            'mouse': 'mouse',
            'laptop': 'laptop',
            'monitor': 'monitor',
            'screen': 'monitor',
            'computer': 'laptop',
            'tv': 'monitor',
            'television': 'monitor',
            
            # Books/Paper
            'book': 'book',
            'books': 'book',
            'paper': 'book',
            
            # Bags/Luggage
            'backpack': 'backpack',
            'handbag': 'handbag',
            'purse': 'handbag',
            'suitcase': 'suitcase',
            'luggage': 'suitcase',
            'bag': 'backpack',
            'bags': 'backpack',
            
            # Furniture
            'chair': 'chair',
            'chairs': 'chair',
            'bench': 'bench',
            'table': 'table',
            'tables': 'table',
            'desk': 'desk',
            'bed': 'bed',
            'couch': 'table',
            'sofa': 'table',
            
            # Doors/Windows
            'door': 'door',
            'doors': 'door',
            'window': 'window',
            'windows': 'window',
            'cabinet': 'cabinet',
            'shelf': 'shelf',
            'shelves': 'shelf',
            
            # Outdoor
            'tree': 'tree',
            'trees': 'tree',
            'plant': 'potted plant',
            'plants': 'potted plant',
            'potted plant': 'potted plant',
            'bush': 'tree',
            'pole': 'pole',
            'poles': 'pole',
            'lamppost': 'lamppost',
            'street light': 'lamppost',
            'traffic light': 'traffic light',
            'fire hydrant': 'fire hydrant',
            'parking meter': 'parking meter',
            'sign': 'pole',
            'fence': 'fence',
            'gate': 'gate',
            'wall': 'wall',
            'barrier': 'fence',
            'ramp': 'table',
            'stairs': 'table',
            'steps': 'table',
            'curb': 'pole',
            
            # Vehicles
            'car': 'car',
            'cars': 'car',
            'automobile': 'car',
            'vehicle': 'car',
            'motorcycle': 'motorcycle',
            'motorcycles': 'motorcycle',
            'motorbike': 'motorcycle',
            'bus': 'bus',
            'buses': 'bus',
            'truck': 'truck',
            'trucks': 'truck',
            'bicycle': 'bicycle',
            'bicycles': 'bicycle',
            'bike': 'bicycle',
            'scooter': 'scooter',
            'skateboard': 'skateboard',
            'skateboard': 'skateboard',
            'trolley': 'cart',
            'cart': 'skateboard',
            
            # Animals
            'dog': 'dog',
            'dogs': 'dog',
            'puppy': 'dog',
            'cat': 'cat',
            'cats': 'cat',
            'kitten': 'cat',
            'bird': 'bird',
            'birds': 'bird',
            'horse': 'horse',
            'horses': 'horse',
            'cow': 'cow',
            'cows': 'cow',
            'sheep': 'sheep',
            'animal': 'dog',
            'animals': 'dog',
            
            # Sports/Toys
            'sports ball': 'sports ball',
            'ball': 'sports ball',
            'basketball': 'sports ball',
            'soccer ball': 'sports ball',
            'baseball': 'baseball',
            'tennis ball': 'tennis ball',
            'baseball bat': 'baseball bat',
            'baseball glove': 'baseball glove',
            'kite': 'kite',
            'toy': 'sports ball',
            'toys': 'sports ball',
            'box': 'table',
            'boxes': 'table',
            
            # Buildings
            'building': 'building',
            'buildings': 'building',
        }
        
        # Return mapped label if exists, otherwise return original
        return label_mappings.get(label, label)
    
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
            h, w, _ = frame.shape
            
            for i in range(len(scores)):
                if scores[i] > 0.45:  # Lower confidence threshold to catch more objects
                    class_id = int(classes[i])
                    if class_id < len(self.labels):
                        label = self.labels[class_id].lower()
                        
                        # Accept all objects
                        
                        # Get box coordinates
                        box = boxes[i]
                        y1, x1, y2, x2 = box
                        x1, y1, x2, y2 = int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h)
                        
                        pixel_width = x2 - x1
                        pixel_height = y2 - y1
                        
                        # Filter out very small detections
                        min_size = min(h, w) * 0.02  # 2% of image
                        if pixel_width < min_size or pixel_height < min_size:
                            continue
                        
                        center_x = (x1 + x2) / 2.0 / w
                        
                        detection = {
                            'name': label,
                            'confidence': round(float(scores[i]), 2),
                            'position_x': round(float(center_x), 2),
                            'distance': None,
                            'urgency': 'SAFE',
                            'box': {
                                'x1': x1,
                                'y1': y1,
                                'x2': x2,
                                'y2': y2
                            }
                        }
                        
                        if label in KNOWN_WIDTHS:
                            dist = estimate_distance(pixel_width, KNOWN_WIDTHS[label])
                            detection['distance'] = round(dist, 1)
                            detection['urgency'] = classify_urgency(dist)
                        
                        detections.append(detection)
            
            # Sort by distance and return ALL detections
            detections = sorted(detections, 
                              key=lambda x: x.get('distance') or 999)
            
            return detections
        
        except Exception as e:
            print(f"❌ TFLite detection error: {e}")
            return []
