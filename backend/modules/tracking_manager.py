"""
Tracking Manager - Handles object tracking state machine
Manages: detection, selection, tracking, pausing, and cooldown phases
"""
import time
from enum import Enum

class TrackingState(Enum):
    IDLE = "idle"  # Not tracking
    SELECTING = "selecting"  # Waiting for user to select object
    TRACKING = "tracking"  # Currently tracking selected object
    PAUSED = "paused"  # Tracking paused, waiting for resume/stop
    COOLDOWN = "cooldown"  # Cooldown period (object not found)
    HOLD = "hold"  # Holding on object for 5 seconds

class TrackingManager:
    """Manages object tracking state and instructions"""
    
    def __init__(self):
        self.state = TrackingState.IDLE
        self.target_object = None
        self.last_detection = None
        self.last_instruction_time = 0
        self.instruction_interval = 5  # seconds
        self.cooldown_start_time = 0
        self.cooldown_duration = 10  # seconds
        self.pause_start_time = 0
        self.hold_start_time = 0
        self.hold_duration = 5  # seconds
        self.search_start_time = 0
        self.search_timeout = 10  # seconds
        self.last_pause_announcement = 0
        self.pause_announcement_interval = 3  # seconds
        
    def start_tracking(self, target_object):
        """Start tracking a specific object"""
        self.state = TrackingState.TRACKING
        self.target_object = target_object.lower()
        self.search_start_time = time.time()
        self.last_instruction_time = time.time()
        return f"Starting to locate {target_object}"
    
    def update_detection(self, detection):
        """Update with current detection"""
        self.last_detection = detection
        self.last_instruction_time = time.time()
        
        if self.state == TrackingState.COOLDOWN:
            self.state = TrackingState.TRACKING
            self.cooldown_start_time = 0
    
    def object_not_found(self):
        """Handle when object not found during search"""
        if self.state == TrackingState.TRACKING:
            elapsed = time.time() - self.search_start_time
            if elapsed >= self.search_timeout:
                self.state = TrackingState.COOLDOWN
                self.cooldown_start_time = time.time()
                return f"No {self.target_object} found"
        return None
    
    def pause(self):
        """Pause tracking"""
        if self.state == TrackingState.TRACKING:
            self.state = TrackingState.PAUSED
            self.pause_start_time = time.time()
            self.last_pause_announcement = time.time()
            return "Tracking paused"
        return None
    
    def resume(self):
        """Resume tracking"""
        if self.state == TrackingState.PAUSED:
            self.state = TrackingState.TRACKING
            self.last_instruction_time = time.time()
            return f"Resuming tracking {self.target_object}"
        return None
    
    def stop(self):
        """Stop tracking completely"""
        self.state = TrackingState.IDLE
        self.target_object = None
        self.last_detection = None
        return "Tracking stopped"
    
    def hold(self):
        """Hold on current object for 5 seconds"""
        self.state = TrackingState.HOLD
        self.hold_start_time = time.time()
        return f"Holding on {self.target_object} for 5 seconds"
    
    def check_hold_complete(self):
        """Check if 5-second hold is complete"""
        if self.state == TrackingState.HOLD:
            elapsed = time.time() - self.hold_start_time
            if elapsed >= self.hold_duration:
                self.state = TrackingState.TRACKING
                self.last_instruction_time = time.time()
                return True
        return False
    
    def should_announce_pause(self):
        """Check if should announce pause (every 3 seconds)"""
        if self.state == TrackingState.PAUSED:
            elapsed = time.time() - self.last_pause_announcement
            if elapsed >= self.pause_announcement_interval:
                self.last_pause_announcement = time.time()
                return True
        return False
    
    def should_give_instruction(self):
        """Check if should give instruction (every 5 seconds)"""
        if self.state == TrackingState.TRACKING:
            elapsed = time.time() - self.last_instruction_time
            if elapsed >= self.instruction_interval:
                self.last_instruction_time = time.time()
                return True
        return False
    
    def should_check_timeout(self):
        """Check if search timeout reached"""
        if self.state == TrackingState.TRACKING and self.last_detection is None:
            elapsed = time.time() - self.search_start_time
            if elapsed >= self.search_timeout:
                return True
        return False
    
    def is_in_cooldown(self):
        """Check if in cooldown phase"""
        if self.state == TrackingState.COOLDOWN:
            elapsed = time.time() - self.cooldown_start_time
            if elapsed >= self.cooldown_duration:
                self.state = TrackingState.TRACKING
                self.search_start_time = time.time()
                return False
            return True
        return False
    
    def get_status(self):
        """Get current tracking status"""
        return {
            'state': self.state.value,
            'target': self.target_object,
            'last_detection': self.last_detection,
            'time_elapsed': time.time() - self.search_start_time if self.target_object else 0
        }


def generate_step_instructions(distance):
    """Convert distance to step-based instructions"""
    if distance is None or distance > 50:
        return "Move around to find the object"
    
    # Estimate steps (assuming ~0.7m per step)
    steps = max(1, int(distance / 0.7))
    
    if distance < 0.2:
        return "Destination reached! Object is within your reach"
    elif distance < 0.5:
        return f"Very close! Walk {steps} small step"
    elif distance < 1.0:
        return f"Close! Walk {steps} steps"
    elif distance < 2.0:
        return f"Walk {steps} steps straight"
    else:
        return f"Walk {steps} steps forward"


def get_directional_instruction(position_x):
    """Convert position_x to directional instruction"""
    if position_x is None:
        return "Find the object in your field of view"
    
    # position_x: 0 = left, 0.5 = center, 1 = right
    if position_x < 0.35:
        return "Move left to center the object"
    elif position_x > 0.65:
        return "Move right to center the object"
    else:
        return "Keep the object centered, move straight"
