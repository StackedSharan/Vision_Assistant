"""Simple audio cue helpers.

Provides a function to compute stereo pan (-1 left .. +1 right) and volume (0..1)
from object position (normalized 0..1 across image) and distance (meters).
"""
import math

def compute_pan_volume(position_x: float, distance: float, max_hearable_distance: float = 8.0):
    """Return (pan, volume).

    - position_x: normalized 0 (left) .. 1 (right)
    - distance: distance in meters (smaller = louder)
    - pan: -1 (left) .. +1 (right)
    - volume: 0..1
    """
    # clamp
    pos = max(0.0, min(1.0, float(position_x)))
    pan = (pos - 0.5) * 2.0

    # volume inversely proportional to distance; clamp between 0.05 and 1.0
    if distance <= 0:
        dist = 0.01
    else:
        dist = distance

    raw = max(0.0, 1.0 - (dist / max_hearable_distance))
    # boost close objects
    volume = min(1.0, max(0.05, raw))

    # apply gentle curve for perceptual loudness
    volume = math.sqrt(volume)

    return round(pan, 3), round(volume, 3)
