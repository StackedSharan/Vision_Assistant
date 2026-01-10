"""
Context Manager - Maintains app state and user context
"""
import time
from datetime import datetime

class ContextManager:
    """Manages application state, navigation, and user context"""
    
    def __init__(self):
        # User Location
        self.current_location = None  # {'lat': float, 'lon': float}
        self.last_location_update = None
        
        # Navigation State
        self.navigation_status = {
            'active': False,
            'destination': None,
            'next_step': None,
            'current_step_index': 0,
            'total_steps': 0,
            'distance_remaining': 0,
            'time_remaining': 0
        }
        
        # Detections (obstacles, people, etc.)
        self.recent_detections = []
        self.detection_history = []
        
        # Session Info
        self.session_start = datetime.now()
        self.last_activity = time.time()
        
    def update_location(self, lat, lon):
        """Update current user location"""
        self.current_location = {'lat': lat, 'lon': lon}
        self.last_location_update = time.time()
        print(f"📍 Location updated: {lat:.4f}, {lon:.4f}")
        
    def update_navigation(self, active=False, destination=None, next_step=None, 
                         step_index=0, total_steps=0, distance=0, time_est=0):
        """Update navigation state"""
        self.navigation_status['active'] = active
        self.navigation_status['destination'] = destination
        self.navigation_status['next_step'] = next_step
        self.navigation_status['current_step_index'] = step_index
        self.navigation_status['total_steps'] = total_steps
        self.navigation_status['distance_remaining'] = distance
        self.navigation_status['time_remaining'] = time_est
        
        if active:
            print(f"🧭 Navigation started to {destination}")
        else:
            print(f"⛔ Navigation stopped")
        
    def update_detections(self, detections):
        """Update detected obstacles/objects"""
        self.recent_detections = detections
        self.last_activity = time.time()
        
        # Add to history (keep last 100)
        self.detection_history.extend(detections)
        if len(self.detection_history) > 100:
            self.detection_history = self.detection_history[-100:]
    
    def get_critical_obstacles(self):
        """Get only critical obstacles from recent detections"""
        return [d for d in self.recent_detections if d.get('urgency') == 'CRITICAL']
    
    def get_nearby_obstacles(self, distance_threshold=3.0):
        """Get obstacles within threshold distance"""
        return [d for d in self.recent_detections 
                if d.get('distance', float('inf')) < distance_threshold]
    
    def get_summary_for_rag(self):
        """Get a text summary for RAG context"""
        summary = "Vision Assistant Status:\n"
        
        if self.current_location:
            summary += f"Current Location: Lat {self.current_location['lat']:.4f}, Lon {self.current_location['lon']:.4f}\n"
        
        if self.navigation_status['active']:
            summary += f"Navigating to: {self.navigation_status['destination']}\n"
            summary += f"Next step: {self.navigation_status['next_step']}\n"
            summary += f"Distance remaining: {self.navigation_status['distance_remaining']:.1f}m\n"
        
        if self.recent_detections:
            summary += f"Recent detections: {len(self.recent_detections)} objects detected\n"
            critical = self.get_critical_obstacles()
            if critical:
                summary += f"⚠️ CRITICAL: {len(critical)} critical obstacles\n"
        
        return summary
    
    def reset_navigation(self):
        """Reset navigation state"""
        self.navigation_status = {
            'active': False,
            'destination': None,
            'next_step': None,
            'current_step_index': 0,
            'total_steps': 0,
            'distance_remaining': 0,
            'time_remaining': 0
        }
        print("Navigation reset")
