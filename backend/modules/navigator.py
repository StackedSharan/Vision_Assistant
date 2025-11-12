# backend/modules/navigator.py (SUPER DEBUGGING VERSION)

import json
import networkx as nx
from geopy.distance import geodesic
import math

class Navigator:
    def __init__(self, map_path):
        print("\n--- Initializing Navigator ---")
        self.graph, self.node_locations = self._build_graph_from_geojson(map_path)
        print("--------------------------------------------------")
        print("Navigator initialized. Graph build process complete.")
        print(f"Final Graph has {self.graph.number_of_nodes()} nodes and {self.graph.number_of_edges()} edges.")
        print(f"Loaded landmark names: {list(self.graph.nodes())}")
        print("--------------------------------------------------\n")

    def _build_graph_from_geojson(self, file_path):
        print("DEBUG: Starting to build graph from GeoJSON...")
        graph = nx.Graph()
        node_locations = {}

        with open(file_path) as f:
            data = json.load(f)

        # First pass: Add all nodes (Points)
        print("DEBUG (Pass 1): Finding all landmarks (Points)...")
        for feature in data['features']:
            if feature['geometry']['type'] == 'Point':
                node_id = feature['properties']['name']
                coords = feature['geometry']['coordinates']
                node_locations[node_id] = (coords[1], coords[0])  # (lat, lon)
                graph.add_node(node_id, pos=coords)
                print(f"  > Found node '{node_id}' at coordinates {coords}")

        # Second pass: Add all edges (LineStrings)
        print("\nDEBUG (Pass 2): Finding all paths (LineStrings) and creating edges...")
        for feature in data['features']:
            if feature['geometry']['type'] == 'LineString':
                points = feature['geometry']['coordinates']
                start_coord = tuple(points[0])
                end_coord = tuple(points[1])
                print(f"  > Found a path from coords {start_coord} to {end_coord}")

                start_node, end_node = None, None
                for node, attrs in graph.nodes(data=True):
                    if attrs['pos'] == list(start_coord): start_node = node
                    if attrs['pos'] == list(end_coord): end_node = node
                
                if start_node and end_node:
                    # If we found matching nodes for both ends of the line...
                    start_latlon = node_locations[start_node]
                    end_latlon = node_locations[end_node]
                    distance = geodesic(start_latlon, end_latlon).meters
                    graph.add_edge(start_node, end_node, weight=distance)
                    print(f"    ✅ SUCCESS: Created edge between '{start_node}' and '{end_node}'")
                else:
                    # This is the critical error message!
                    print(f"    ❌ FAILED to create edge. Could not find matching nodes for this path.")
                    if not start_node: print(f"      - No existing landmark found at start coordinate {start_coord}")
                    if not end_node: print(f"      - No existing landmark found at end coordinate {end_coord}")

        return graph, node_locations
    
    # ... (the rest of the file remains the same) ...
    def find_shortest_path(self, start_node, end_node):
        try:
            path_nodes = nx.dijkstra_path(self.graph, source=start_node, target=end_node, weight='weight')
            instructions = []
            # ... (rest of the function)
            for i in range(len(path_nodes) - 1):
                current_node_name = path_nodes[i]
                next_node_name = path_nodes[i+1]
                lat1, lon1 = self.node_locations[current_node_name]
                lat2, lon2 = self.node_locations[next_node_name]
                distance = self.graph[current_node_name][next_node_name]['weight']
                bearing = self._calculate_bearing(math.radians(lat1), math.radians(lon1), math.radians(lat2), math.radians(lon2))
                direction = self._get_compass_direction(bearing)
                instruction = f"Walk {direction} for {round(distance)} meters towards {next_node_name.replace('_', ' ')}."
                instructions.append(instruction)
            return instructions
        except (nx.NodeNotFound, nx.NetworkXNoPath):
            return None

    def _calculate_bearing(self, lat1, lon1, lat2, lon2):
        d_lon = lon2 - lon1
        y = math.sin(d_lon) * math.cos(lat2)
        x = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lon)
        brng = math.atan2(y, x)
        brng = math.degrees(brng)
        return (brng + 360) % 360

    def _get_compass_direction(self, bearing):
        dirs = ["North", "Northeast", "East", "Southeast", "South", "Southwest", "West", "Northwest"]
        index = round(bearing / 45) % 8
        return dirs[index]