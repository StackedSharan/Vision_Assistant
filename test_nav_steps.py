import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from modules.navigator import Navigator

def test_navigation():
    # Initialize navigator
    map_path = os.path.join(os.getcwd(), 'backend', 'models', 'map.geojson')
    nav = Navigator(map_path)
    
    # Test multiple routes
    routes = [
        ('entrance', 'architecture'),
        ('entrance', 'canteen'),
        ('architecture', 'aiml block')
    ]
    
    for start, end in routes:
        print(f"\n--- Testing Route: {start} -> {end} ---")
        if start not in nav.landmarks or end not in nav.landmarks:
             print(f"Skipping {start}->{end} (landmarks not found)")
             continue
             
        result = nav.find_shortest_path(start, end)
        
        if result:
            print("✅ Instructions:")
            for step in result['instructions']:
                print(f" - {step['text']}")
        else:
            print("❌ No route found.")

if __name__ == "__main__":
    test_navigation()
