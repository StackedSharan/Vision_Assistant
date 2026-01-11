"""
Navigation module for college campus routing
Provides step-by-step directions to various locations
"""

class Navigator:
    """Handles navigation guidance for college campus"""
    
    # Pre-defined routes for different locations
    ROUTES = {
        'entrance': [
            'Welcome to the college. You are at the main entrance.',
            'Head walk straight towards the parking area for about 50 meters',
            'Turn right at the corner',
            'You have reached your destination'
        ],
        'parking': [
            'You are heading to the parking area.',
            'Walk straight for about 30 meters',
            'Turn left at the traffic light',
            'The parking area is on your right',
            'You have reached the parking area'
        ],
        'canteen': [
            'You are heading to the canteen.',
            'Walk straight for about 40 meters',
            'Turn left at the corner near the building',
            'Continue walking for about 25 meters',
            'The canteen entrance is on your left',
            'You have reached the canteen'
        ],
        'engineering': [
            'You are heading to the Engineering building.',
            'Walk straight ahead for about 60 meters',
            'Turn right at the main plaza',
            'Continue for about 50 meters',
            'The Engineering building is on your right',
            'You have reached the Engineering building'
        ],
        'architecture': [
            'You are heading to the Architecture building.',
            'Walk straight for about 45 meters',
            'Turn left near the garden',
            'Continue for about 35 meters',
            'The Architecture building entrance is ahead',
            'You have reached the Architecture building'
        ],
        'aiml': [
            'You are heading to the AIML block.',
            'Walk straight for about 55 meters',
            'Turn right at the intersection',
            'Continue for about 40 meters',
            'The AIML block is on your left',
            'You have reached the AIML block'
        ],
        'ugpg': [
            'You are heading to the UG/PG building.',
            'Walk straight for about 50 meters',
            'Turn left at the corner',
            'Continue for about 45 meters',
            'The UG/PG building is on your right',
            'You have reached the UG/PG building'
        ],
        'mainbuilding': [
            'You are heading to the main building.',
            'Walk straight for about 70 meters',
            'The main building will come into view',
            'Continue straight for about 30 meters',
            'The main building entrance is ahead',
            'You have reached the main building'
        ],
    }
    
    def __init__(self, context_manager=None):
        """Initialize navigator with context"""
        self.context = context_manager
        self.current_route = None
        self.current_step = 0
        self.current_destination = None
    
    def start_navigation(self, destination):
        """Start navigation to a destination"""
        destination = destination.lower().strip()
        
        # Check if destination exists in our routes
        if destination not in self.ROUTES:
            # Try to find similar location
            for loc in self.ROUTES.keys():
                if destination in loc or loc in destination:
                    destination = loc
                    break
            else:
                raise ValueError(f'Destination "{destination}" not found')
        
        # Start the route
        self.current_destination = destination
        self.current_route = self.ROUTES[destination]
        self.current_step = 0
        
        # Return first instruction (after initial announcement)
        return self.current_route[0]
    
    def get_next_step(self):
        """Get the next step in navigation"""
        if self.current_route is None:
            raise ValueError('Navigation not started')
        
        # Move to next step
        self.current_step += 1
        
        # Check if we've reached the end
        if self.current_step >= len(self.current_route):
            self.current_step = len(self.current_route) - 1
            return self.current_route[-1]
        
        return self.current_route[self.current_step]
    
    def get_prev_step(self):
        """Get the previous step in navigation"""
        if self.current_route is None:
            raise ValueError('Navigation not started')
        
        # Move to previous step
        self.current_step -= 1
        
        # Check if we've gone before the beginning
        if self.current_step < 0:
            self.current_step = 0
            return self.current_route[0]
        
        return self.current_route[self.current_step]
    
    def stop_navigation(self):
        """Stop navigation"""
        self.current_route = None
        self.current_step = 0
        self.current_destination = None
    
    def get_current_step(self):
        """Get current step"""
        if self.current_route is None:
            return None
        return self.current_route[self.current_step]
    
    def is_at_destination(self):
        """Check if at the final step"""
        if self.current_route is None:
            return False
        return self.current_step >= len(self.current_route) - 1
