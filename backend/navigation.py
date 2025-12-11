import json
import networkx as nx
import math
from typing import List, Tuple, Dict, Optional

class NavigationGraph:
    def __init__(self, geojson_path: str):
        self.geojson_path = geojson_path
        self.graph = nx.Graph()
        self.locations: Dict[str, Tuple[float, float]] = {}  # name -> (lon, lat)
        self._load_data()

    def _load_data(self):
        """Loads GeoJSON and builds the graph."""
        try:
            with open(self.geojson_path, 'r') as f:
                data = json.load(f)
        except FileNotFoundError:
            print(f"Error: File not found at {self.geojson_path}")
            return

        # First pass: Collect all points and build the graph structure
        for feature in data.get('features', []):
            geom_type = feature['geometry']['type']
            coords = feature['geometry']['coordinates']
            props = feature.get('properties', {})

            if geom_type == 'Point':
                name = props.get('name')
                if name:
                    # Store location (lon, lat)
                    self.locations[name] = tuple(coords)
                    # Add as node (will be connected if it's part of a path, 
                    # or we need to snap it to the nearest path node)
                    self.graph.add_node(tuple(coords), type='landmark', name=name)

            elif geom_type == 'LineString':
                # Add edges between consecutive points in the LineString
                for i in range(len(coords) - 1):
                    p1 = tuple(coords[i])
                    p2 = tuple(coords[i+1])
                    dist = self._haversine_distance(p1, p2)
                    self.graph.add_edge(p1, p2, weight=dist)

        # Snap named locations to the nearest graph node if they aren't already in the graph
        # (In this specific geojson, points might be exactly on the lines or separate)
        # For robustness, let's ensure all named locations are connected to the network
        self._connect_landmarks_to_network()

    def _connect_landmarks_to_network(self):
        """Connects isolated landmark nodes to the nearest node in the path network."""
        path_nodes = [n for n in self.graph.nodes if self.graph.nodes[n].get('type') != 'landmark']
        if not path_nodes:
            # If no path nodes (only points), we can't connect. 
            # But the geojson has LineStrings, so this should be fine.
            # Actually, let's treat all nodes with edges as path nodes.
            path_nodes = [n for n in self.graph.nodes if self.graph.degree(n) > 0]
        
        if not path_nodes:
            return

        for name, coord in self.locations.items():
            if self.graph.degree(coord) == 0:
                # Find nearest node in the main network
                nearest_node = min(path_nodes, key=lambda n: self._haversine_distance(coord, n))
                dist = self._haversine_distance(coord, nearest_node)
                self.graph.add_edge(coord, nearest_node, weight=dist)

    def _haversine_distance(self, coord1: Tuple[float, float], coord2: Tuple[float, float]) -> float:
        """Calculates distance in meters between two (lon, lat) tuples."""
        lon1, lat1 = coord1
        lon2, lat2 = coord2
        R = 6371000  # Earth radius in meters

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2)**2 + \
            math.cos(phi1) * math.cos(phi2) * \
            math.sin(delta_lambda / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

        return R * c

    # Inside your Navigator class in navigator.py

    # Inside your Navigator class in navigator.py

# Inside your Navigator class in navigator.py

    def find_shortest_path(self, start_name, end_name):
        start_name = start_name.lower()
        end_name = end_name.lower()

        if start_name not in self.landmarks or end_name not in self.landmarks:
            print(f"❌ NAVIGATOR ERROR: Start or end landmark not found in map data.")
            print(f"    Available landmarks are: {list(self.landmarks.keys())}")
            print(f"    Received start: '{start_name}', end: '{end_name}'")
            return None

        start_node = self.landmarks[start_name]
        end_node = self.landmarks[end_name]
        
        print(f"--- NAVIGATOR: Finding path from '{start_name}' to '{end_name}' ---")
        
        try:
            # Check if a path is even possible before trying to calculate it
            if not nx.has_path(self.graph, source=start_node, target=end_node):
                print("❌ NAVIGATOR ERROR: NetworkX reports NO PATH exists between these two points.")
                print("    This is a 'coordinate snapping' issue in your map.geojson file.")
                return None

            path_coords = nx.dijkstra_path(self.graph, source=start_node, target=end_node, weight='weight')
            
            instructions = []
            for i in range(len(path_coords) - 1):
                p1 = path_coords[i]
                p2 = path_coords[i+1]
                dist = self.graph[p1][p2]['weight']
                
                instruction_text = f"Walk {dist:.0f} meters forward."
                
                node_data = self.graph.nodes[p2]
                if node_data.get('type') == 'landmark':
                    instruction_text = f"Walk {dist:.0f} meters to reach {node_data['name']}."

                # --- THIS IS THE CRITICAL FIX ---
                # Tuples like (12.34, 56.78) cannot be sent as JSON.
                # We MUST convert them to lists like [12.34, 56.78].
                instructions.append({
                    "text": instruction_text,
                    "coords": list(p2) # Convert tuple to list
                })
            
            print("✅ NAVIGATOR: Path found successfully! Sending instructions to frontend.")
            return instructions
            
        except nx.NodeNotFound as e:
            print(f"❌ NAVIGATOR ERROR: Node not found in graph. {e}")
            return None
        except Exception as e:
            print(f"❌ NAVIGATOR: An unexpected error occurred in pathfinding: {e}")
            return None


    def calculate_bearing(self, start_coord: Tuple[float, float], end_coord: Tuple[float, float]) -> float:
        """Calculates the bearing from start to end in degrees."""
        lon1, lat1 = start_coord
        lon2, lat2 = end_coord

        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_lambda = math.radians(lon2 - lon1)

        y = math.sin(delta_lambda) * math.cos(phi2)
        x = math.cos(phi1) * math.sin(phi2) - \
            math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
        
        theta = math.atan2(y, x)
        bearing = (math.degrees(theta) + 360) % 360
        return bearing

    def find_nearest_node(self, coord: Tuple[float, float]) -> Tuple[float, float]:
        """Finds the nearest graph node to the given coordinate."""
        if not self.graph.nodes:
            return None
        
        nearest_node = min(self.graph.nodes, key=lambda n: self._haversine_distance(coord, n))
        return nearest_node

    def get_directions(self, path: List[Tuple[float, float]]) -> List[str]:
        """Generates text instructions from a path."""
        if not path or len(path) < 2:
            return ["You have arrived."]

        instructions = []
        for i in range(len(path) - 1):
            p1 = path[i]
            p2 = path[i+1]
            bearing = self.calculate_bearing(p1, p2)
            dist = self._haversine_distance(p1, p2)
            
            direction_str = f"Head bearing {int(bearing)}°"
            
            if i > 0:
                prev_p = path[i-1]
                prev_bearing = self.calculate_bearing(prev_p, p1)
                turn = (bearing - prev_bearing + 360) % 360
                
                if 337.5 <= turn or turn < 22.5:
                    turn_desc = "Go straight"
                elif 22.5 <= turn < 67.5:
                    turn_desc = "Turn slight right"
                elif 67.5 <= turn < 112.5:
                    turn_desc = "Turn right"
                elif 112.5 <= turn < 157.5:
                    turn_desc = "Turn sharp right"
                elif 202.5 <= turn < 247.5:
                    turn_desc = "Turn sharp left"
                elif 247.5 <= turn < 292.5:
                    turn_desc = "Turn left"
                elif 292.5 <= turn < 337.5:
                    turn_desc = "Turn slight left"
                else:
                    turn_desc = "U-turn"
                
                direction_str = f"{turn_desc}"

            instructions.append(f"{direction_str} for {int(dist)} meters")

        return instructions

if __name__ == "__main__":
    # Example usage
    nav = NavigationGraph("backend/models/map.geojson")
    print("Locations:", list(nav.locations.keys()))
    
    # Test path
    start = "Entrance"
    end = "Canteen"
    path = nav.get_shortest_path(start, end)
    
    if path:
        print(f"\nPath from {start} to {end}:")
        for p in path:
            print(p)
        
        print("\nInstructions:")
        directions = nav.get_directions(path)
        for d in directions:
            print(d)
