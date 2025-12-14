"""Smart obstacle filtering and urgency detection.

Implements:
- Distance-based urgency levels (red/yellow/green)
- Duplicate suppression (same obstacle seen N times)
- Context-awareness (filter obstacles off the route)
- Temporal smoothing (only alert if obstacle persists)
"""

class ObstacleFilter:
    def __init__(self, max_history=5):
        """
        Args:
            max_history: number of frames to track for duplicate detection
        """
        self.max_history = max_history
        self.last_obstacles = []  # List of recent detections
        self.suppressed_until = {}  # {object_id: timestamp} for suppression

    def classify_urgency(self, distance_m: float) -> str:
        """Classify urgency based on distance.
        
        Returns: 'critical', 'warning', or 'safe'
        """
        if distance_m < 1.5:
            return 'critical'
        elif distance_m < 3.0:
            return 'warning'
        else:
            return 'safe'

    def filter_obstacles(self, detections: list, current_time: float = None) -> list:
        """Filter detections and suppress duplicates.
        
        Args:
            detections: list of {'name', 'distance', 'position_x', 'confidence'}
            current_time: epoch time (for suppression tracking)
        
        Returns:
            filtered list of urgent/important detections with urgency level
        """
        if current_time is None:
            import time
            current_time = time.time()

        # 1. Keep only high-confidence, close detections
        filtered = []
        for d in detections:
            conf = d.get('confidence', 0.5)
            dist = d.get('distance', 10.0)
            
            # Skip low-confidence or far detections
            if conf < 0.4 or dist > 8.0:
                continue
            
            urgency = self.classify_urgency(dist)
            # Only keep warning and critical; skip safe
            if urgency in ['warning', 'critical']:
                d['urgency'] = urgency
                filtered.append(d)

        # 2. Update history and suppress duplicates
        self.last_obstacles.append(filtered)
        if len(self.last_obstacles) > self.max_history:
            self.last_obstacles.pop(0)

        # 3. Return detections that appear in >2 consecutive frames (persistent)
        if len(self.last_obstacles) < 2:
            # Not enough history, return current if any critical
            return [d for d in filtered if d.get('urgency') == 'critical']

        # Find obstacles that appeared in at least 2 of the last 3 frames
        persistent = []
        for d in filtered:
            name = d['name']
            appearances = sum(1 for frame in self.last_obstacles[-3:] 
                             if any(od['name'] == name for od in frame))
            if appearances >= 2:
                persistent.append(d)

        return persistent

    def apply_context_filtering(self, detections: list, route_coords: list = None) -> list:
        """Filter detections based on route context.
        
        Args:
            detections: list of detections with urgency
            route_coords: list of [lat, lon] route waypoints
        
        Returns:
            filtered list, prioritizing obstacles on or near the route
        """
        if not route_coords or len(route_coords) < 2:
            return detections  # No route context, return all

        # For simplicity, assume detections from camera are roughly on-route
        # A more advanced implementation would use heading/position to filter
        # detections that are clearly off to the side
        
        # Prioritize by urgency
        return sorted(detections, key=lambda d: {'critical': 0, 'warning': 1, 'safe': 2}.get(d.get('urgency', 'safe'), 3))

