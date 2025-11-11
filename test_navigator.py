# test_navigator.py

import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__))))

from backend.modules.navigator import Navigator

print("--- Testing Navigator Initialization ---")
try:
    nav = Navigator()
    print("\n--- Navigator Initialized Successfully ---")

    # --- DEFINE YOUR START AND END POINTS ---
    # Use the exact 'name' strings you defined in your geojson file.
    start_point = "Entrance"
    end_point = "Canteen"
    # --- END OF DEFINITION ---


    print(f"\n--- Calculating route from '{start_point}' to '{end_point}' ---")
    
    # Call the new get_route function
    result = nav.get_route(start_point, end_point)
    
    # Print the results
    if result['status'] == 'success':
        print("Route found successfully!")
        for i, step in enumerate(result['route']):
            print(f"Step {i+1}: {step['instruction']}")
    else:

        print(f"Error finding route: {result['message']}")


except Exception as e:
    print(f"\n--- An error occurred ---")
    print(e)