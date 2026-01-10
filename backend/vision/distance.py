# backend/vision/distance.py

# Define the approximate real-world widths of objects we care about (in meters)
KNOWN_WIDTHS = {
    "person": 0.5,
    "car": 1.8,
    "bicycle": 0.6,
    "motorcycle": 0.8,
    "bus": 2.5,
    "truck": 2.6,
    "door": 0.9,
    "stairs": 1.2
}

# Calibrated focal length for the camera (pixels)
# This usually needs calibration per device, 600 is a common default.
DEFAULT_FOCAL_LENGTH = 600 

def estimate_distance(pixel_width, real_width, focal_length=DEFAULT_FOCAL_LENGTH):
    """Calculates the distance to an object using the pinhole camera model."""
    if pixel_width <= 0:
        return float('inf')
    return (real_width * focal_length) / pixel_width

def classify_urgency(distance):
    """Classifies urgency based on distance."""
    if distance < 1.5:
        return "CRITICAL"
    elif distance < 3.0:
        return "WARNING"
    else:
        return "IGNORE"
