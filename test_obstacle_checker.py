# test_obstacle_checker.py (COMPLETE VERSION)
import requests
import base64
import os

SERVER_URL = "http://localhost:5001/api/check_obstacle"
TEST_IMAGE_PATH = "test_image.jpg" # Make sure this image contains a person or car

def run_test():
    """Reads an image, sends it to the server, and prints the result."""
    
    # --- 1. Check if the test image exists ---
    if not os.path.exists(TEST_IMAGE_PATH):
        print(f"--- ERROR: Test image not found at '{TEST_IMAGE_PATH}' ---")
        print("Please add a JPEG image containing a person or car to your main project folder.")
        return

    print("--- Testing Obstacle Checker API ---")
    
    # --- 2. Read the image and encode it into Base64 text ---
    with open(TEST_IMAGE_PATH, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    
    # --- 3. Prepare the JSON data payload ---
    payload = {'image': encoded_string}
    
    try:
        # --- 4. Make a simple POST request to our new endpoint ---
        print(f"Sending image to {SERVER_URL}...")
        response = requests.post(SERVER_URL, json=payload)
        
        # --- 5. Check the server's response ---
        if response.status_code == 200:
            data = response.json()
            obstacles = data.get('obstacles', [])
            
            if obstacles:
                print("\n!!!!!!!!!!!!!!!!!!!!!!")
                print("  SUCCESS!")
                print(f"  Server detected the following obstacles: {obstacles}")
                print("!!!!!!!!!!!!!!!!!!!!!!\n")
            else:
                print("\n--- Request was successful, but no significant obstacles were detected. ---")
                print("Is there a person, car, or bicycle in your test_image.jpg?")

        else:
            # If the server returned an error code (like 500)
            print(f"\n--- ERROR: Server responded with status code {response.status_code} ---")
            print(f"Server's response text: {response.text}")

    except requests.exceptions.ConnectionError:
        print(f"\n--- CONNECTION ERROR: Failed to connect to {SERVER_URL} ---")
        print("Is the backend server (python backend/app.py) running?")
    except Exception as e:
        print(f"\n--- An unexpected error occurred: {e} ---")

# --- Main execution block ---
if __name__ == '__main__':
    run_test()