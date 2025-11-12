# test_navigation_api.py
import requests
import json

SERVER_URL = "http://localhost:5001/api/start_navigation"

def run_test():
    """Sends a navigation request to the server and prints the result."""
    
    # --- Define the start and end points for the test ---
    # Use the exact names from your map.geojson file
    start_location = "Entrance"
    end_location = "Canteen"
    # ---

    print(f"--- Testing Navigation API: Requesting route from '{start_location}' to '{end_location}' ---")
    
    payload = {
        'start': start_location,
        'end': end_location
    }
    
    try:
        # Make the POST request to our new endpoint
        response = requests.post(SERVER_URL, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            
            print("\n--- SUCCESS! Server responded with the following data: ---")
            # Use json.dumps for pretty-printing the response
            print(json.dumps(data, indent=2))
            
            if data.get('status') == 'success':
                print("\n--- Test complete. Check if you heard the first instruction spoken by the server. ---")
            else:
                print("\n--- The server responded with an error message. Check the message above. ---")

        else:
            print(f"\n--- Error: Server responded with status code {response.status_code} ---")
            print(f"Server's response text: {response.text}")

    except requests.exceptions.ConnectionError:
        print(f"\n--- CONNECTION ERROR: Failed to connect to {SERVER_URL} ---")
        print("Is the backend server (python backend/app.py) running?")
    except Exception as e:
        print(f"\n--- An unexpected error occurred: {e} ---")

if __name__ == '__main__':
    run_test()