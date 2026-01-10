import json
import networkx as nx
import math
from typing import List, Tuple, Dict, Optional

class GeoRouter:
    def __init__(self, geojson_path: str):
        self.geojson_path = geojson_path
        self.graph = nx.Graph()
        self.landmarks: Dict[str, Tuple[float, float]] = {}  # name -> (lon, lat)
        self.load_data()

    def load_data(self):
        """Loads GeoJSON and builds the navigation graph."""
        try:
            with open(self.geojson_path, 'r') as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error loading map data: {e}")
            return

        for feature in data.get('features', []):
            geom = feature['geometry']
            props = feature.get('properties', {})
            coords = geom['coordinates']

            if geom['type'] == 'Point':
                name = props.get('name')
                if name:
                    name_lower = name.lower()
                    self.landmarks[name_lower] = tuple(coords)
                    self.graph.add_node(tuple(coords), type='landmark', name=name)

            elif geom['type'] == 'LineString':
                for i in range(len(coords) - 1):
                    p1 = tuple(coords[i])
                    p2 = tuple(coords[i+1])
                    dist = self._haversine_distance(p1, p2)
                    self.graph.add_edge(p1, p2, weight=dist)

        self._connect_landmarks()

    def _connect_landmarks(self):
        """Ensures landmarks are connected to the path network."""
        path_nodes = [n for n in self.graph.nodes if self.graph.degree(n) > 0]
        if not path_nodes: return

        for name, coord in self.landmarks.items():
            if coord not in self.graph or self.graph.degree(coord) == 0:
                nearest = min(path_nodes, key=lambda n: self._haversine_distance(coord, n))
                dist = self._haversine_distance(coord, nearest)
                self.graph.add_edge(coord, nearest, weight=dist)

    def _haversine_distance(self, c1, c2):
        lon1, lat1 = c1
        lon2, lat2 = c2
        r = 6371000  # meters
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
        a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
        return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1-a))

    def calculate_bearing(self, p1, p2):
        lon1, lat1 = p1
        lon2, lat2 = p2
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dl = math.radians(lon2 - lon1)
        y = math.sin(dl) * math.cos(phi2)
        x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dl)
        return (math.degrees(math.atan2(y, x)) + 360) % 360

    def find_path(self, start_coord, destination_name):
        dest_name = destination_name.lower()
        if dest_name not in self.landmarks:
            return None

        dest_node = self.landmarks[dest_name]
        start_node = min(self.graph.nodes, key=lambda n: self._haversine_distance(start_coord, n))

        try:
            path = nx.dijkstra_path(self.graph, start_node, dest_node, weight='weight')
            return path
        except nx.NetworkXNoPath:
            return None

    def get_landmark_coords(self, name: str) -> Optional[Tuple[float, float]]:
        return self.landmarks.get(name.lower())

    def get_instructions(self, path):
        if not path or len(path) < 2:
            return []

        instructions = []
        for i in range(len(path) - 1):
            p1, p2 = path[i], path[i+1]
            dist = self._haversine_distance(p1, p2)
            bearing = self.calculate_bearing(p1, p2)
            
            # Base instruction
            instr = {"distance": dist, "bearing": bearing, "coords": list(p2)}
            
            # Add text hint
            if i == 0:
                instr["text"] = f"Head towards bearing {int(bearing)} degrees for {int(dist)} meters."
            else:
                prev_p = path[i-1]
                prev_bearing = self.calculate_bearing(prev_p, p1)
                diff = (bearing - prev_bearing + 360) % 360
                
                if diff < 20 or diff > 340: turn = "Go straight"
                elif 20 <= diff < 70: turn = "Turn slightly right"
                elif 70 <= diff < 110: turn = "Turn right"
                elif 110 <= diff < 160: turn = "Turn sharp right"
                elif 160 <= diff < 200: turn = "Make a U-turn"
                elif 200 <= diff < 250: turn = "Turn sharp left"
                elif 250 <= diff < 290: turn = "Turn left"
                else: turn = "Turn slightly left"
                
                instr["text"] = f"{turn} and walk {int(dist)} meters."

            instructions.append(instr)
        return instructions
