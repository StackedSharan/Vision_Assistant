# test_position_api.py
import requests
import base64
import os

SERVER_URL = "http://localhost:5001/api/confirm_position"
TEST_IMAGE_PATH = "test_image.jpg" # Any image will work for this test

def run_test():
    if not os.path.exists(TEST_IMAGE_PATH):
        print(f"--- ERROR: Test image not found at '{TEST_IMAGE_PATH}' ---")
        return

    print("--- Testing Position Confirmation API ---")
    
    with open(TEST_IMAGE_PATH, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    
    payload = {'image': encoded_string}
    
    try:
        print(f"Sending image to {SERVER_URL}...")
        response = requests.post(SERVER_URL, json=payload)
        
        if response.status_code == 200:
            data = response.json()
            print("\n--- SUCCESS! Server responded: ---")
            print(data)
            
            if data.get('status') == 'confirmed':
                print(f"\nTest successful. The server confirmed the mock location: '{data.get('location')}'")
            else:
                print("\nTest failed. Server did not send a confirmation.")
        else:
            print(f"\n--- Error: Server responded with status code {response.status_code} ---")

    except requests.exceptions.ConnectionError:
        print(f"\n--- CONNECTION ERROR: Is the backend server running? ---")
    except Exception as e:
        print(f"\n--- An unexpected error occurred: {e} ---")

if __name__ == '__main__':
    run_test()