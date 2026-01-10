"""
Clean API routes for Vision Assistant
Handles: landing, location query, navigation, obstacle detection
"""
from flask import request, jsonify
from navigation.navigator import Navigator
from vision.detector import ObjectDetector
from audio.tts import TTSEngine
import json

def register_routes(app, socketio, context_manager):
    """Register all API endpoints"""
    
    navigator = Navigator(context_manager)
    detector = ObjectDetector(mode='yolo')
    
    @app.route('/api/locations', methods=['GET'])
    def get_locations():
        """Return list of available destinations"""
        locations = [
            'entrance', 'parking', 'ugpg', 'architecture',
            'engineering', 'canteen', 'aiml', 'mainbuilding'
        ]
        return jsonify({'locations': locations})
    
    @app.route('/api/start-navigation', methods=['POST'])
    def start_navigation():
        """Start navigation to a destination"""
        data = request.json
        destination = data.get('destination', '').lower().strip()
        
        if not destination:
            return jsonify({'error': 'Destination required'}), 400
        
        try:
            instruction = navigator.start_navigation(destination)
            return jsonify({
                'success': True,
                'instruction': instruction,
                'destination': destination
            })
        except Exception as e:
            print(f"Navigation error: {e}")
            return jsonify({'error': str(e)}), 400
    
    @app.route('/api/next-step', methods=['GET'])
    def next_step():
        """Get next navigation instruction"""
        try:
            instruction = navigator.get_next_step()
            return jsonify({'instruction': instruction})
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    @app.route('/api/prev-step', methods=['GET'])
    def prev_step():
        """Get previous navigation instruction"""
        try:
            instruction = navigator.get_prev_step()
            return jsonify({'instruction': instruction})
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    @app.route('/api/stop-navigation', methods=['POST'])
    def stop_nav():
        """Stop navigation"""
        try:
            msg = navigator.stop_navigation()
            return jsonify({'message': msg})
        except Exception as e:
            return jsonify({'error': str(e)}), 400
    
    @app.route('/api/detect-obstacles', methods=['POST'])
    def detect_obstacles():
        """Process image frame for obstacles"""
        data = request.json
        image_data = data.get('image')  # base64 encoded
        
        if not image_data:
            return jsonify({'error': 'Image required'}), 400
        
        try:
            detections = detector.detect(image_data)
            return jsonify({'detections': detections})
        except Exception as e:
            print(f"Detection error: {e}")
            return jsonify({'error': str(e)}), 400
    
    @app.route('/api/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        return jsonify({'status': 'ok'})
    
    return app
