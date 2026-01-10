import geojson
import networkx as nx
from geopy.distance import geodesic
import math

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

    def get_nearest_landmark(self, coords):
        """Finds the nearest landmark to the given GPS coordinates (lat, lon)."""
        if not self.landmarks:
            return None, float('inf')
            
        min_dist = float('inf')
        nearest_name = None
        
        # coords is (lat, lon), landmark coords are (lon, lat) usually in GeoJSON
        # But self.landmarks values are stored as (lon, lat) from the file load
        
        for name, lm_coords in self.landmarks.items():
            # geodesic expects (lat, lon)
            # lm_coords is (lon, lat)
            dist = geodesic(coords, lm_coords[::-1]).meters
            if dist < min_dist:
                min_dist = dist
                nearest_name = name
                
        return nearest_name, min_dist

    def calculate_bearing(self, pointA, pointB):
        """Calculates the bearing between two points (lat, lon)."""
        lat1 = math.radians(pointA[0])
        lat2 = math.radians(pointB[0])
        diffLong = math.radians(pointB[1] - pointA[1])

        x = math.sin(diffLong) * math.cos(lat2)
        y = math.cos(lat1) * math.sin(lat2) - (math.sin(lat1) * math.cos(lat2) * math.cos(diffLong))

        initial_bearing = math.atan2(x, y)
        initial_bearing = math.degrees(initial_bearing)
        compass_bearing = (initial_bearing + 360) % 360
        return compass_bearing

    def get_turn_direction(self, bearing1, bearing2):
        """Determines turn direction based on change in bearing."""
        diff = bearing2 - bearing1
        # Normalize to -180 to +180
        if diff > 180: diff -= 360
        if diff < -180: diff += 360
        
        if -45 <= diff <= 45:
            return "continue straight"
        elif 45 < diff < 135:
            return "turn right"
        elif -135 < diff < -45:
            return "turn left"
        else:
            return "make a sharp turn"

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
                self.graph.add_edge(start_node, nearest, weight=dist)
            else:
                print("   ❌ Could not snap start node.")
                return None

        if self.graph.degree[end_node] == 0:
            print(f"⚠️ End '{end_name}' is isolated. Snapping...")
            nearest, dist = self.get_nearest_connected_node(end_node)
            if nearest:
                print(f"   ✅ Snapped end to {nearest} ({dist:.1f}m)")
                self.graph.add_edge(end_node, nearest, weight=dist)
            else:
                print("   ❌ Could not snap end node.")
                return None
        
        try:
            path_coords = nx.dijkstra_path(self.graph, source=start_node, target=end_node, weight='weight')
            
            # 1. Pre-calculate segments with bearings
            segments = []
            for i in range(len(path_coords) - 1):
                p1, p2 = path_coords[i], path_coords[i+1]
                dist = self.graph[p1][p2]['weight']
                # p1, p2 are (lon, lat), calculate_bearing needs (lat, lon)
                bearing = self.calculate_bearing(p1[::-1], p2[::-1])
                segments.append({
                    'distance': dist,
                    'bearing': bearing,
                    'end_node': p2,
                    'start_node': p1
                })

<<<<<<< HEAD
                # include numeric distance to help compute ETA
                instructions.append({ "text": instruction_text, "coords": list(p2), "distance_m": float(dist) })
=======
            # 2. Aggregate instructions
            instructions = []
            current_steps = 0
            
            for i in range(len(segments)):
                seg = segments[i]
                # 1 meter approx 1.3 steps
                current_steps += seg['distance'] * 1.3
                
                # Determine next action
                if i == len(segments) - 1:
                    # Last segment
                    instructions.append({
                        "text": f"After {int(current_steps)} steps, you will reach your destination.",
                        "coords": list(seg['end_node']),
                        "distance_m": seg['distance'] # Keep last segment distance or total? Just segment for now.
                    })
                else:
                    next_seg = segments[i+1]
                    turn = self.get_turn_direction(seg['bearing'], next_seg['bearing'])
                    
                    if turn == "continue straight":
                        # Continue accumulating steps
                        pass
                    else:
                        # Turn detected
                        # Check if there is a landmark at this turn
                        node_data = self.graph.nodes[seg['end_node']]
                        landmark_name = node_data.get('name')
                        at_text = f" at {landmark_name}" if landmark_name else ""
                        
                        instructions.append({
                            "text": f"After {int(current_steps)} steps, {turn}{at_text}.",
                            "coords": list(seg['end_node']),
                            "distance_m": 0 # Placeholder, maybe aggregate?
                        })
                        current_steps = 0 # Reset for next segment
>>>>>>> bdc5b15c50262411885aea250c797832ada78e59

            # Swap (lon, lat) to (lat, lon) for Leaflet
            full_path_lat_lon = [[coord[1], coord[0]] for coord in path_coords]

            print(f"✅ Path found with {len(instructions)} aggregated steps.")
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