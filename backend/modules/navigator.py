import geojson
import networkx as nx
from geopy.distance import geodesic

class Navigator:
    def __init__(self, map_path):
        self.graph = nx.Graph()
        self.landmarks = {}
        print(f"🗺️ Initializing Navigator with map: {map_path}")
        self._load_map(map_path)

    def _load_map(self, map_path):
        try:
            with open(map_path, 'r') as f:
                data = geojson.load(f)
        except Exception as e:
            print(f"❌ ERROR loading map: {e}")
            return

        # 1. Load Landmarks (Points)
        for feature in data['features']:
            if feature['geometry']['type'] == 'Point':
                properties = feature.get('properties', {})
                name = properties.get('name', '').lower().strip()
                if name:
                    coords = tuple(feature['geometry']['coordinates'])
                    self.landmarks[name] = coords
                    # Add landmark as a node
                    self.graph.add_node(coords, type='landmark', name=name)
        
        print(f"📍 Loaded {len(self.landmarks)} landmarks: {list(self.landmarks.keys())}")

        # 2. Load Paths (LineStrings)
        edge_count = 0
        for feature in data['features']:
            if feature['geometry']['type'] == 'LineString':
                path_coords = feature['geometry']['coordinates']
                for i in range(len(path_coords) - 1):
                    start_node = tuple(path_coords[i])
                    end_node = tuple(path_coords[i+1])
                    
                    if start_node not in self.graph: self.graph.add_node(start_node)
                    if end_node not in self.graph: self.graph.add_node(end_node)
                        
                    # Calculate distance (GeoJSON is Lon,Lat; geodesic needs Lat,Lon)
                    distance = geodesic(start_node[::-1], end_node[::-1]).meters
                    self.graph.add_edge(start_node, end_node, weight=distance)
                    edge_count += 1
        
        print(f"🔗 Graph built: {self.graph.number_of_nodes()} nodes, {self.graph.number_of_edges()} edges.")

    def get_nearest_connected_node(self, target_coords):
        """Finds the nearest node in the graph that has edges (neighbors)."""
        min_dist = float('inf')
        nearest_node = None
        
        # Optimization: Only check nodes that have edges
        connected_nodes = [n for n in self.graph.nodes if self.graph.degree[n] > 0]
        
        if not connected_nodes:
            print("⚠️ Graph has no connected nodes!")
            return None, 0

        for node in connected_nodes:
            # Skip the target node itself if it's isolated (distance 0)
            if node == target_coords:
                continue

            dist = geodesic(target_coords[::-1], node[::-1]).meters
            if dist < min_dist:
                min_dist = dist
                nearest_node = node
        
        return nearest_node, min_dist

    def find_shortest_path(self, start_name, end_name):
        start_name = start_name.lower().strip()
        end_name = end_name.lower().strip()

        print(f"🔍 Finding path: '{start_name}' -> '{end_name}'")

        if start_name not in self.landmarks:
            print(f"❌ Start landmark '{start_name}' not found.")
            return None
        if end_name not in self.landmarks:
            print(f"❌ End landmark '{end_name}' not found.")
            return None

        start_node = self.landmarks[start_name]
        end_node = self.landmarks[end_name]
        
        # Check connectivity and snap if necessary
        if self.graph.degree[start_node] == 0:
            print(f"⚠️ Start '{start_name}' is isolated. Snapping...")
            nearest, dist = self.get_nearest_connected_node(start_node)
            if nearest:
                print(f"   ✅ Snapped start to {nearest} ({dist:.1f}m)")
                # Add temporary edge to connect landmark to graph
                self.graph.add_edge(start_node, nearest, weight=dist)
            else:
                print("   ❌ Could not snap start node.")
                return None

        if self.graph.degree[end_node] == 0:
            print(f"⚠️ End '{end_name}' is isolated. Snapping...")
            nearest, dist = self.get_nearest_connected_node(end_node)
            if nearest:
                print(f"   ✅ Snapped end to {nearest} ({dist:.1f}m)")
                # Add temporary edge to connect landmark to graph
                self.graph.add_edge(end_node, nearest, weight=dist)
            else:
                print("   ❌ Could not snap end node.")
                return None
        
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

                # include numeric distance to help compute ETA
                instructions.append({ "text": instruction_text, "coords": list(p2), "distance_m": float(dist) })

            # Swap (lon, lat) to (lat, lon) for Leaflet
            full_path_lat_lon = [[coord[1], coord[0]] for coord in path_coords]

            print(f"✅ Path found with {len(instructions)} steps.")
            return {
                "instructions": instructions,
                "full_path": full_path_lat_lon
            }
            
        except nx.NetworkXNoPath:
            print("❌ No path exists between these nodes (graph disconnected).")
            return None
        except Exception as e:
            print(f"❌ PATHFINDING ERROR: {e}")
            return None