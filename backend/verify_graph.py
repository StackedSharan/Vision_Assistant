import os
import sys
from modules.navigator import Navigator

# Adjust path to find modules
sys.path.append(os.getcwd())

def test_graph():
    map_path = os.path.join(os.getcwd(), 'models', 'map.geojson')
    print(f"Testing map at: {map_path}")
    
    if not os.path.exists(map_path):
        print("❌ Map file not found!")
        return

    nav = Navigator(map_path)
    
    print(f"\n--- Graph Stats ---")
    print(f"Nodes: {nav.graph.number_of_nodes()}")
    print(f"Edges: {nav.graph.number_of_edges()}")
    
    print(f"\n--- Landmarks ---")
    for name, coords in nav.landmarks.items():
        print(f"  {name}: {coords}")
        if coords in nav.graph:
            print(f"    -> In graph? Yes. Degree: {nav.graph.degree[coords]}")
        else:
            print(f"    -> In graph? NO (This is bad if it's not snapped)")

    print(f"\n--- Path Test: Entrance -> Architecture ---")
    start = "entrance"
    end = "architecture"
    
    path = nav.find_shortest_path(start, end)
    
    if path:
        print("✅ Path FOUND!")
        print(f"Instructions: {len(path['instructions'])}")
    else:
        print("❌ Path NOT found.")

if __name__ == "__main__":
    test_graph()
