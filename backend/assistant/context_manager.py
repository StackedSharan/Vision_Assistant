import time

class ContextManager:
    def __init__(self):
        self.current_location = None
        self.last_detections = []
        self.last_hazards = []
        self.navigation_status = {
            "active": False,
            "destination": None,
            "next_step": None,
            "distance_to_step": None
        }
        self.history = []

    def update_location(self, lat, lon):
        self.current_location = {"lat": lat, "lon": lon}

    def update_detections(self, detections):
        self.last_detections = detections
        # We could also prune or summarize detections here

    def update_navigation(self, active=None, destination=None, next_step=None, distance=None):
        if active is not None: self.navigation_status["active"] = active
        if destination is not None: self.navigation_status["destination"] = destination
        if next_step is not None: self.navigation_status["next_step"] = next_step
        if distance is not None: self.navigation_status["distance_to_step"] = distance

    def get_summary_for_rag(self):
        """Generates a text summary of the current system context for the LLM/RAG."""
        summary = f"Current position: {self.current_location}\n"
        
        if self.last_detections:
            objs = [f"{d['name']} ({d.get('distance', 'unknown')}m away)" for d in self.last_detections]
            summary += f"Detections in view: {', '.join(objs)}\n"
        else:
            summary += "No significant objects detected in front.\n"
            
        if self.navigation_status["active"]:
            summary += f"Navigating to {self.navigation_status['destination']}. "
            summary += f"Next step: {self.navigation_status['next_step']} in {self.navigation_status['distance_to_step']} meters.\n"
            
        return summary

    def add_to_history(self, role, text):
        self.history.append({"role": role, "text": text, "timestamp": time.time()})
        if len(self.history) > 20:
            self.history.pop(0)
