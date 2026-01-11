"""Vision module for object detection and distance estimation"""
from .detector import ObjectDetector
from .distance import estimate_distance, classify_urgency, KNOWN_WIDTHS, ALERT_CLASSES

__all__ = [
    'ObjectDetector',
    'estimate_distance',
    'classify_urgency',
    'KNOWN_WIDTHS',
    'ALERT_CLASSES'
]
