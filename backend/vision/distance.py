# backend/vision/distance.py

# Define the approximate real-world widths of objects we care about (in meters)
KNOWN_WIDTHS = {
    "person": 0.5,
    "car": 1.8,
    "bicycle": 0.6,
    "motorcycle": 0.8,
    "bus": 2.5,
    "truck": 2.6,
    "dog": 0.6,
    "cat": 0.3,
    "tree": 1.0,
    "potted plant": 0.5,
    "backpack": 0.4,
    "handbag": 0.3,
}

# List of relevant obstacle classes to alert on
ALERT_CLASSES = {
    # People and animals
    "person", "dog", "cat", "bird", "horse", "cow", "sheep",
    # Vehicles
    "car", "motorcycle", "bus", "truck", "bicycle", "scooter",
    # Obstacles and barriers
    "tree", "potted plant", "chair", "bench", "table", "lamppost",
    "traffic light", "fire hydrant", "parking meter", "pole",
    "building", "wall", "fence", "gate", "door", "window",
    # Miscellaneous obstacles
    "backpack", "handbag", "suitcase", "skateboard", "sports ball",
    "kite", "baseball bat", "baseball glove", "bottle", "cup",
}

# Calibrated focal length for the camera (pixels)
# This usually needs calibration per device, 600 is a common default.
DEFAULT_FOCAL_LENGTH = 600 

def estimate_distance(pixel_width, real_width, focal_length=DEFAULT_FOCAL_LENGTH):
    """Calculates the distance to an object using the pinhole camera model."""
    if pixel_width <= 0:
        return float('inf')
    distance = (real_width * focal_length) / pixel_width
    # Clamp to reasonable values (0.5m to 50m)
    return max(0.5, min(50.0, distance))

def classify_urgency(distance):
    """Classifies urgency based on distance with precise thresholds."""
    if distance < 0.8:
        return "CRITICAL"  # Immediate danger, < 80cm
    elif distance < 1.5:
        return "DANGER"     # Very close, < 1.5m
    elif distance < 3.0:
        return "WARNING"    # Close, < 3m
    elif distance < 5.0:
        return "CAUTION"    # Medium distance, < 5m
    else:
        return "SAFE"       # > 5m, no immediate alert needed

