# backend/modules/navigator.py (FINAL VERSION)

import geojson
import networkx as nx
from geopy.distance import geodesic
from backend.config import PROJECT_ROOT
import os
import math # Needed for calculating angles

MAP_FILE_PATH = os.path.join(PROJECT_ROOT, 'backend', 'models', 'map.geojson')

class Navigator:
    def __init__(self):
        """Initializes the Navigator by loading the map and building the graph."""
        if not os.path.exists(MAP_FILE_PATH):
            raise FileNotFoundError(f"Map file not found at: {MAP_FILE_PATH}")

        self.graph = nx.Graph()
        self.node_data = {}

        print("Initializing Navigator: Loading map and building graph...")
        self._load_map()
        print(f"Navigator initialized. Graph has {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges.")

    def _load_map(self):
        """Parses the GeoJSON file and populates the graph."""
        with open(MAP_FILE_PATH) as f:
            data = geojson.load(f)

        for feature in data['features']:
            if feature['geometry']['type'] == 'Point':
                properties = feature['properties']
                coords = feature['geometry']['coordinates']
                node_id = properties.get('name')
                if not node_id:
                    continue
                self.node_data[node_id] = {'name': node_id, 'coords': (coords[1], coords[0])}
                self.graph.add_node(node_id)

        for feature in data['features']:
            if feature['geometry']['type'] == 'LineString':
                path_coords = feature['geometry']['coordinates']
                start_node_id = self._find_closest_node((path_coords[0][1], path_coords[0][0]))
                end_node_id = self._find_closest_node((path_coords[-1][1], path_coords[-1][0]))
                if start_node_id and end_node_id and start_node_id != end_node_id:
                    start_coords = self.node_data[start_node_id]['coords']
                    end_coords = self.node_data[end_node_id]['coords']
                    distance = geodesic(start_coords, end_coords).meters
                    self.graph.add_edge(start_node_id, end_node_id, weight=distance)

    def _find_closest_node(self, coords, search_radius_m=20):
        """Finds the ID of the closest named node."""
        for node_id, data in self.node_data.items():
            if geodesic(coords, data['coords']).meters < search_radius_m:
                return node_id
        return None

    def _calculate_bearing(self, pointA, pointB):
        """Calculates the bearing (direction) between two points."""
        lat1, lon1 = math.radians(pointA[0]), math.radians(pointA[1])
        lat2, lon2 = math.radians(pointB[0]), math.radians(pointB[1])
        dLon = lon2 - lon1
        x = math.sin(dLon) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(dLon)
        bearing = math.atan2(x, y)
        bearing = math.degrees(bearing)
        bearing = (bearing + 360) % 360
        return bearing

    def _bearing_to_direction(self, bearing):
        """Converts a numerical bearing to a compass direction."""
        if 22.5 <= bearing < 67.5: return "North-East"
        if 67.5 <= bearing < 112.5: return "East"
        if 112.5 <= bearing < 157.5: return "South-East"
        if 157.5 <= bearing < 202.5: return "South"
        if 202.5 <= bearing < 247.5: return "South-West"
        if 247.5 <= bearing < 292.5: return "West"
        if 292.5 <= bearing < 337.5: return "North-West"
        return "North"

    # --- THIS IS THE NEW, FINAL FUNCTION ---
    def get_route(self, start_node_id, end_node_id):
        """
        Calculates the shortest path between two nodes and returns a list
        of human-readable turn-by-turn directions.
        """
        try:
            # 1. Use Dijkstra's algorithm to find the shortest path of node IDs
            path = nx.dijkstra_path(self.graph, source=start_node_id, target=end_node_id, weight='weight')
            
            directions = []
            
            # 2. Go through the path and generate directions for each segment
            for i in range(len(path) - 1):
                current_node_id = path[i]
                next_node_id = path[i+1]
                
                # Get data for the current and next nodes
                current_node_data = self.node_data[current_node_id]
                next_node_data = self.node_data[next_node_id]
                
                # Get the distance of this path segment
                distance = self.graph[current_node_id][next_node_id]['weight']
                
                # Calculate the direction
                bearing = self._calculate_bearing(current_node_data['coords'], next_node_data['coords'])
                direction = self._bearing_to_direction(bearing)
                
                # Create the instruction
                instruction = (f"From {current_node_id}, walk {direction} for about "
                               f"{int(round(distance, -1))} meters to reach {next_node_id}.")
                directions.append({"instruction": instruction})

            # Add a final instruction for arrival
            directions.append({"instruction": f"You have arrived at {end_node_id}."})
            
            return {'status': 'success', 'route': directions}

        except nx.NetworkXNoPath:
            return {'status': 'error', 'message': f"No path found between {start_node_id} and {end_node_id}."}
        except KeyError as e:
            return {'status': 'error', 'message': f"Location not found: {e}. Please check the names."}