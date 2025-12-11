import geojson
import networkx as nx
from geopy.distance import geodesic

class Navigator:
    def __init__(self, map_path):
        self.graph = nx.Graph()
        self.landmarks = {}
        self._load_map(map_path)

    def _load_map(self, map_path):
        try:
            with open(map_path, 'r') as f:
                data = geojson.load(f)
        except Exception as e:
            print(f"❌ ERROR loading map: {e}")
            return

        for feature in data['features']:
            if feature['geometry']['type'] == 'Point':
                properties = feature.get('properties', {})
                name = properties.get('name', '').lower()
                if name:
                    coords = tuple(feature['geometry']['coordinates'])
                    self.landmarks[name] = coords
                    self.graph.add_node(coords, type='landmark', name=name)
        
        for feature in data['features']:
            if feature['geometry']['type'] == 'LineString':
                path_coords = feature['geometry']['coordinates']
                for i in range(len(path_coords) - 1):
                    start_node = tuple(path_coords[i])
                    end_node = tuple(path_coords[i+1])
                    
                    if start_node not in self.graph: self.graph.add_node(start_node)
                    if end_node not in self.graph: self.graph.add_node(end_node)
                        
                    distance = geodesic(start_node[::-1], end_node[::-1]).meters
                    self.graph.add_edge(start_node, end_node, weight=distance)
    
    def get_path_bearing(self, p1, p2):
        # This is a placeholder for a more advanced function.
        # For now, we will just use directions like "forward".
        return "forward"

    # Inside your Navigator class

    # Inside your Navigator class in navigator.py

    def find_shortest_path(self, start_name, end_name):
        start_name = start_name.lower().strip()
        end_name = end_name.lower().strip()

        if start_name not in self.landmarks or end_name not in self.landmarks:
            return None

        start_node = self.landmarks[start_name]
        end_node = self.landmarks[end_name]
        
        try:
            path_coords = nx.dijkstra_path(self.graph, source=start_node, target=end_node, weight='weight')
            
            instructions = []
            for i in range(len(path_coords) - 1):
                p1, p2 = path_coords[i], path_coords[i+1]
                dist = self.graph[p1][p2]['weight']
                
                instruction_text = f"Walk {dist:.0f} meters forward."
                node_data = self.graph.nodes[p2]
                if node_data.get('type') == 'landmark':
                    instruction_text = f"Walk {dist:.0f} meters to reach {node_data['name']}."

                instructions.append({ "text": instruction_text, "coords": list(p2) })

            # CRITICAL NEW FEATURE: Return instructions AND the full path for the map
            # We must swap (lon, lat) from geojson to (lat, lon) for the Leaflet map library
            full_path_lat_lon = [[coord[1], coord[0]] for coord in path_coords]

            return {
                "instructions": instructions,
                "full_path": full_path_lat_lon
            }
            
        except Exception as e:
            print(f"PATHFINDING ERROR: {e}")
            return None