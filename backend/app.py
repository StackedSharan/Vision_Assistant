# backend/app.py (Final, Clean Version)

from flask import Flask, jsonify
import cv2

# Import our custom modules
from modules.object_detection import ObjectDetector
from modules.voice_assistant import VoiceAssistant

# --- Initialization ---
app = Flask(__name__)

print("Loading AI Models...")
detector = ObjectDetector()
assistant = VoiceAssistant()
print("Models loaded successfully.")
# --- End of Initialization ---

@app.route('/')
def index():
    return "Flask Server is Running! The main interactive endpoint is /api/assistant"

def format_detections_for_speech(detections):
    if not detections:
        return "I don't see anything noteworthy."
    detection_counts = {}
    for item in detections:
        obj_name = item.split(' ')[0]
        detection_counts[obj_name] = detection_counts.get(obj_name, 0) + 1
    parts = []
    for obj, count in detection_counts.items():
        if count > 1:
            parts.append(f"{count} {obj}s")
        else:
            parts.append(f"a {obj}")
    if len(parts) > 1:
        speech_text = "I see " + ", ".join(parts[:-1]) + " and " + parts[-1] + "."
    else:
        speech_text = "I see " + parts[0] + "."
    return speech_text

@app.route('/api/assistant', methods=['GET'])
def interactive_assistant():
    """Listens for a command and responds intelligently."""
    print("=========================================")
    print("Request received for /api/assistant")
    
    try:
        assistant.speak("How can I help you?")
        command = assistant.listen()
        
        if command and "what's around me" in command.lower():
            assistant.speak("Okay, looking around now.")
            
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                err_msg = "Sorry, I am having trouble accessing the camera."
                assistant.speak(err_msg)
                return jsonify({'error': 'Could not open camera.'}), 500
            ret, frame = cap.read()
            cap.release()
            if not ret:
                err_msg = "Sorry, I could not capture an image."
                assistant.speak(err_msg)
                return jsonify({'error': 'Failed to capture frame.'}), 500
                
            detections = detector.detect(frame)
            speech_response = format_detections_for_speech(detections)
            assistant.speak(speech_response)
            
            return jsonify({'command_received': command, 'response': speech_response})
            
        else:
            response_text = "Sorry, I did not understand that command. Please ask, 'what's around me?'"
            assistant.speak(response_text)
            return jsonify({'command_received': command, 'response': response_text})

    except Exception as e:
        print(f"An error occurred in the assistant loop: {e}")
        error_message = "I have run into an unexpected error. Please try again."
        assistant.speak(error_message)
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)