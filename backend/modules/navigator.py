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

    def find_shortest_path(self, start_name, end_name):
        start_name = start_name.lower()
        end_name = end_name.lower()

        if start_name not in self.landmarks:
            return None # Or return an error message
        if end_name not in self.landmarks:
            return None

        start_node = self.landmarks[start_name]
        end_node = self.landmarks[end_name]
        
        try:
            path_coords = nx.dijkstra_path(self.graph, source=start_node, target=end_node, weight='weight')
            
            instructions = []
            for i in range(len(path_coords) - 1):
                p1 = path_coords[i]
                p2 = path_coords[i+1]
                dist = self.graph[p1][p2]['weight']
                direction = self.get_path_bearing(p1, p2)
                
                node_data = self.graph.nodes[p2]
                if node_data.get('type') == 'landmark':
                    instructions.append(f"Walk {dist:.0f} meters {direction} to reach {node_data['name']}.")
                else:
                    instructions.append(f"Walk {dist:.0f} meters {direction}.")
            
            return instructions
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return None