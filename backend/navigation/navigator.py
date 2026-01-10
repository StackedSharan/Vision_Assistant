import os
from .geo_router import GeoRouter

class Navigator:
    def __init__(self, context_manager):
        self.context = context_manager
        current_dir = os.path.dirname(os.path.abspath(__file__))
        backend_dir = os.path.dirname(current_dir)
        map_path = os.path.join(backend_dir, 'models', 'map.geojson')
        self.router = GeoRouter(map_path)
        
        self.active_path = []
        self.instructions = []
        self.current_step_idx = 0

    def start_navigation(self, destination_name, start_name=None):
        # Default to 'entrance' if no start landmark is provided and GPS is unknown
        if not start_name and not self.context.current_location:
            start_name = 'entrance'
            print("📍 Start location unknown; defaulting to 'entrance' for demonstration.")

        if start_name:
            start_coord = self.router.get_landmark_coords(start_name)
        elif self.context.current_location:
            start_coord = (self.context.current_location['lon'], self.context.current_location['lat'])
        else:
            return "Current location unknown. Cannot start navigation."

        path = self.router.find_path(start_coord, destination_name)
        
        if not path:
            return f"Could not find a path to {destination_name}."
            
        self.active_path = path
        self.instructions = self.router.get_instructions(path)
        self.current_step_idx = 0
        
        self.context.update_navigation(
            active=True, 
            destination=destination_name,
            next_step=self.instructions[0]['text'],
            distance=self.instructions[0]['distance']
        )
        return self.instructions[0]['text']

    def update_position(self, lat, lon):
        self.context.update_location(lat, lon)
        if not self.context.navigation_status['active']:
            return None
            
        # Check if we've reached the current step or need to reroute
        target_step = self.instructions[self.current_step_idx]
        target_coords = target_step['coords']
        
        dist_to_step = self.router._haversine_distance((lon, lat), tuple(target_coords))
        
        if dist_to_step < 3.0: # Within 3 meters of step
            self.current_step_idx += 1
            if self.current_step_idx >= len(self.instructions):
                self.context.update_navigation(active=False)
                return "You have arrived at your destination."
            
            next_instr = self.instructions[self.current_step_idx]
            self.context.update_navigation(
                next_step=next_instr['text'],
                distance=next_instr['distance']
            )
            return next_instr['text']
        
        # Update distance to user
        self.context.update_navigation(distance=dist_to_step)
        return None

    def get_next_step(self):
        if not self.context.navigation_status['active']:
            return "Navigation is not active."
        
        self.current_step_idx += 1
        if self.current_step_idx >= len(self.instructions):
            self.context.update_navigation(active=False)
            return "You have arrived at your destination."
        
        instr = self.instructions[self.current_step_idx]
        self.context.update_navigation(
            next_step=instr['text'],
            distance=instr['distance']
        )
        return instr['text']

    def get_prev_step(self):
        if not self.context.navigation_status['active']:
            return "Navigation is not active."
        
        if self.current_step_idx > 0:
            self.current_step_idx -= 1
        
        instr = self.instructions[self.current_step_idx]
        self.context.update_navigation(
            next_step=instr['text'],
            distance=instr['distance']
        )
        return instr['text']

    def stop_navigation(self):
        self.active_path = []
        self.instructions = []
        self.context.update_navigation(active=False)
        return "Navigation stopped."
