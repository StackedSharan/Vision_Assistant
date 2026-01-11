# backend/vision/distance.py

# Define the approximate real-world widths of objects we care about (in meters)
KNOWN_WIDTHS = {
    # People and body parts
    "person": 0.5,
    "hand": 0.08,          # Average hand width
    "head": 0.20,          # Average head width
    "face": 0.18,          # Average face width
    
    # Common objects (mobile, bottle, etc.)
    "cell phone": 0.08,    # Smartphone width
    "phone": 0.08,         # Phone (generic)
    "mobile phone": 0.08,  # Mobile phone
    "bottle": 0.08,        # Water bottle width
    "cup": 0.08,           # Cup width
    "keyboard": 0.45,      # Keyboard width
    "mouse": 0.07,         # Computer mouse
    "laptop": 0.35,        # Laptop width
    "monitor": 0.50,       # Monitor width
    "book": 0.25,          # Book width
    "backpack": 0.4,       # Backpack
    "handbag": 0.3,        # Handbag
    "suitcase": 0.45,      # Suitcase
    
    # Furniture and indoor objects
    "chair": 0.4,          # Chair width
    "bench": 0.5,          # Bench width
    "table": 1.0,          # Table width
    "desk": 1.2,           # Desk width
    "bed": 1.0,            # Bed width
    "door": 0.9,           # Door width
    "window": 1.0,         # Window width
    "cabinet": 0.6,        # Cabinet width
    "shelf": 0.8,          # Shelf width
    
    # Outdoor objects
    "tree": 1.0,           # Tree trunk width
    "potted plant": 0.5,   # Plant width
    "pole": 0.15,          # Pole width
    "lamppost": 0.15,      # Lamppost width
    "traffic light": 0.35, # Traffic light width
    "fire hydrant": 0.30,  # Fire hydrant width
    "parking meter": 0.20, # Parking meter width
    "fence": 0.1,          # Fence post
    "gate": 1.2,           # Gate width
    
    # Vehicles
    "car": 1.8,            # Car width
    "motorcycle": 0.8,     # Motorcycle width
    "bicycle": 0.6,        # Bicycle width
    "bus": 2.5,            # Bus width
    "truck": 2.6,          # Truck width
    "scooter": 0.6,        # Scooter width
    "skateboard": 0.25,    # Skateboard width
    
    # Animals
    "dog": 0.6,            # Dog width
    "cat": 0.3,            # Cat width
    "bird": 0.3,           # Bird width
    "horse": 1.5,          # Horse width
    "cow": 1.8,            # Cow width
    "sheep": 1.0,          # Sheep width
    
    # Miscellaneous
    "sports ball": 0.24,   # Sports ball (basketball size)
    "baseball": 0.074,     # Baseball
    "tennis ball": 0.067,  # Tennis ball
    "baseball bat": 0.07,  # Bat width
    "baseball glove": 0.25, # Glove width
    "kite": 0.5,           # Kite width
    
    # Building structures
    "building": 5.0,       # Generic building (large)
    "wall": 0.3,           # Wall width (for edge)
}

# List of relevant obstacle classes to alert on
ALERT_CLASSES = {
    # People and body parts
    "person", "human", "head", "face", "hand", "arm", "leg", "body",
    
    # Common objects to avoid
    "cell phone", "phone", "mobile phone", "mobile",
    "bottle", "cup", "glass", "can", "mug",
    "keyboard", "mouse", "laptop", "monitor", "screen", "computer",
    "book", "books", "paper",
    
    # Personal items
    "backpack", "handbag", "suitcase", "bag", "luggage",
    
    # Furniture and indoor obstacles
    "chair", "bench", "table", "desk", "bed", "couch", "sofa",
    "door", "window", "cabinet", "shelf", "shelves",
    "stairs", "steps", "ladder", "railing",
    
    # Outdoor obstacles
    "tree", "trees", "bush", "plant", "potted plant", "flowers",
    "pole", "poles", "lamppost", "streetlight", "traffic light",
    "fire hydrant", "parking meter", "sign",
    "fence", "gate", "wall", "barrier", "ramp",
    "stairs", "steps", "curb", "sidewalk",
    
    # Vehicles
    "car", "cars", "motorcycle", "motorcycles", "bus", "buses",
    "truck", "trucks", "bicycle", "bicycles", "bike",
    "scooter", "skateboard", "trolley", "cart",
    
    # Animals
    "dog", "dogs", "cat", "cats", "bird", "birds",
    "horse", "horses", "cow", "cows", "sheep",
    "person", "people", "animal", "animals",
    
    # Miscellaneous obstacles
    "sports ball", "ball", "basketball", "soccer ball",
    "baseball", "baseball bat", "baseball glove", "tennis ball",
    "kite", "toy", "toys", "box", "boxes",
    
    # Building structures
    "building", "buildings", "wall", "walls",
}

# Calibrated focal length for the camera (pixels)
# Improved calibration for better distance accuracy
DEFAULT_FOCAL_LENGTH = 850  # Increased for better accuracy at close range

def estimate_distance(pixel_width, real_width, focal_length=DEFAULT_FOCAL_LENGTH):
    """Improved distance estimation with multi-point calibration.
    
    Accounts for lens distortion and perspective at different distances.
    """
    if pixel_width <= 0 or real_width <= 0:
        return float('inf')
    
    # Basic pinhole camera formula
    distance = (real_width * focal_length) / pixel_width
    
    # Adaptive correction for lens distortion at close range
    if distance < 0.15:
        distance = distance * 0.88  # Strong correction for very close (< 15cm)
    elif distance < 0.25:
        distance = distance * 0.92  # Moderate correction (15-25cm)
    elif distance < 0.35:
        distance = distance * 0.95  # Slight correction (25-35cm)
    elif distance < 0.5:
        distance = distance * 0.97  # Minimal correction (35-50cm)
    elif distance > 3:
        distance = distance * 1.01  # Distant objects slightly corrected
    
    # Allow detection of very close objects (0.05m minimum)
    return max(0.05, min(50.0, distance))

def classify_urgency(distance):
    """Classifies urgency with tighter thresholds for safety.
    
    0.05-0.2m: CRITICAL (immediate danger, < 20cm)
    0.2-0.35m: DANGER (near distance, < 35cm) 
    0.35-5m: WARNING (moderate distance, announce after instruction)
    >5m: SAFE (no alert needed)
    """
    if distance < 0.2:
        return "CRITICAL"  # Immediate danger, < 20cm
    elif distance < 0.35:
        return "DANGER"     # Near distance, < 35cm
    elif distance < 5.0:
        return "WARNING"    # Moderate distance, < 5m
    else:
        return "SAFE"       # > 5m, no immediate alert

