# backend/modules/context_memory.py

import sqlite3
import math # We need the math library for distance calculation
from backend.config import DB_PATH

# Helper function to calculate distance between two GPS coordinates
def haversine_distance(lat1, lon1, lat2, lon2):
    """Calculate the distance in meters between two GPS coordinates."""
    R = 6371000  # Radius of Earth in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class Memory:
    def remember_location(self, name, latitude, longitude):
        """Saves a new location to the database."""
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT OR REPLACE INTO locations (name, latitude, longitude) 
                VALUES (LOWER(?), ?, ?)
            ''', (name, latitude, longitude))
            conn.commit()
            conn.close()
            return {'status': 'success', 'message': f"I've remembered this place as {name}."}
        except sqlite3.Error as e:
            return {'status': 'error', 'message': f"Database error: {e}"}

    # --- NEW METHOD TO RECALL A LOCATION ---
    def recall_location(self, current_latitude, current_longitude, radius_meters=50):
        """
        Checks the database for any known locations within a given radius
        of the current coordinates.
        """
        try:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Get all locations from the database
            cursor.execute("SELECT name, latitude, longitude FROM locations")
            all_locations = cursor.fetchall()
            conn.close()

            # Check each location to see if it's nearby
            for name, saved_lat, saved_lon in all_locations:
                distance = haversine_distance(current_latitude, current_longitude, saved_lat, saved_lon)
                print(f"Distance to '{name}' is {distance:.2f} meters.") # Debug print
                
                # If we find a location within the radius, return its name
                if distance <= radius_meters:
                    return name.capitalize() # e.g., "home" -> "Home"
            
            # If no locations are found within the radius
            return None

        except sqlite3.Error as e:
            print(f"Database error in recall_location: {e}")
            return None