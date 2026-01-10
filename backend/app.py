"""
Vision Assistant - Backend Server
Smart navigation and obstacle detection for blind users
"""
import os
import sys
from flask import Flask
from flask_socketio import SocketIO, emit
from flask_cors import CORS
import threading
import time
import cv2
import base64
import numpy as np

# Import our clean modules
from assistant.context_manager import ContextManager
from api_routes import register_routes

# Initialize Flask
app = Flask(__name__, static_folder='../frontend/build', static_url_path='')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")

# Initialize context manager
context = ContextManager()

# Register API routes
app = register_routes(app, socketio, context)

# ===== SocketIO Events =====

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print("✅ Client connected")
    emit('connected', {'data': 'Connected to Vision Assistant'})

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print("🔌 Client disconnected")

@socketio.on('frame')
def handle_frame(data):
    """Handle incoming video frame for obstacle detection"""
    try:
        # Extract base64 image
        image_data = data.get('image')
        if not image_data:
            return
        
        # Decode image (frame already processed, just acknowledge)
        encoded_data = image_data.split(',')[1] if ',' in image_data else image_data
        img_array = np.frombuffer(base64.b64decode(encoded_data), np.uint8)
        img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if img is not None:
            # Here we could process the frame for obstacles
            # For now, just emit acknowledgment
            emit('frame_received', {'status': 'ok'})
    except Exception as e:
        print(f"Frame error: {e}")

@socketio.on('voice_command')
def handle_voice_command(data):
    """Handle voice commands from frontend"""
    command = data.get('command', '').lower()
    print(f"📢 Voice command: {command}")
    
    # Handle different commands
    if 'location' in command or 'go to' in command:
        emit('waiting_for_destination', {'message': 'Please tell me where you want to go'})
    elif 'next' in command:
        emit('next_step', {'message': 'Getting next instruction'})
    elif 'previous' in command:
        emit('prev_step', {'message': 'Getting previous instruction'})
    elif 'stop' in command:
        emit('navigation_stopped', {'message': 'Navigation stopped'})

# ===== Serve Frontend =====

@app.route('/')
def serve():
    """Serve the React frontend"""
    return app.send_static_file('index.html')

@app.errorhandler(404)
def not_found(e):
    """Serve index.html for all unknown routes (React routing)"""
    return app.send_static_file('index.html')

# ===== Main =====

if __name__ == '__main__':
    PORT = int(os.environ.get('PORT', 5000))
    DEBUG = os.environ.get('FLASK_ENV') == 'development'
    
    print(f"""
    ╔════════════════════════════════════════╗
    ║  Vision Assistant - Starting Server    ║
    ║  Port: {PORT:<32}║
    ║  Debug: {str(DEBUG):<32}║
    ╚════════════════════════════════════════╝
    """)
    
    socketio.run(app, host='0.0.0.0', port=PORT, debug=DEBUG, allow_unsafe_werkzeug=True)