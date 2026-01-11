"""
Clean API routes for Vision Assistant
Handles: landing, location query, navigation, obstacle detection, object tracking
"""
from flask import request, jsonify
from navigation.navigator import Navigator
from vision.detector import ObjectDetector
from modules.tracking_manager import TrackingManager, generate_step_instructions, get_directional_instruction
from audio.tts import TTSEngine
import json

# Global tracking manager instance
tracking_manager = TrackingManager()

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
            return jsonify({'error': 'Image required', 'detections': []}), 400
        
        try:
            detections = detector.detect(image_data)
            
            # Log detection summary
            if detections:
                critical = [d for d in detections if d.get('urgency') == 'CRITICAL']
                danger = [d for d in detections if d.get('urgency') == 'DANGER']
                warning = [d for d in detections if d.get('urgency') == 'WARNING']
                
                if critical:
                    names = [d['name'] for d in critical]
                    dists = [f"{d['distance']}m" if d.get('distance') else '?' for d in critical]
                    print(f"🚨 CRITICAL: {', '.join([f'{n}({d})' for n, d in zip(names, dists)])}")
                if danger:
                    names = [d['name'] for d in danger]
                    print(f"⚠️ DANGER: {', '.join(names)}")
                if warning:
                    names = [d['name'] for d in warning]
                    print(f"⚠ WARNING: {', '.join(names)}")
            
            return jsonify({'detections': detections, 'count': len(detections)})
        except Exception as e:
            print(f"❌ Detection error: {e}")
            return jsonify({'error': str(e), 'detections': []}), 400
    
    @app.route('/api/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        return jsonify({'status': 'ok'})
    
    # ===== Object Tracking Endpoints =====
    
    @app.route('/api/detect-all', methods=['POST'])
    def detect_all_objects():
        """Detect all objects in frame (for selection)"""
        data = request.json
        image_data = data.get('image')
        
        if not image_data:
            return jsonify({'error': 'Image required', 'objects': []}), 400
        
        try:
            detections = detector.detect(image_data)
            
            # Return unique object names for user to select from
            object_names = list(set([d['name'] for d in detections]))
            
            return jsonify({
                'objects': object_names,
                'detections': detections,
                'message': f"I see: {', '.join(object_names[:5])}" if object_names else "No objects detected"
            })
        except Exception as e:
            print(f"❌ Detection error: {e}")
            return jsonify({'error': str(e), 'objects': []}), 400
    
    @app.route('/api/start-tracking', methods=['POST'])
    def start_tracking():
        """Start tracking a specific object"""
        data = request.json
        target_object = data.get('target', '').lower().strip()
        
        if not target_object:
            return jsonify({'error': 'Target object required'}), 400
        
        message = tracking_manager.start_tracking(target_object)
        return jsonify({
            'success': True,
            'message': message,
            'target': target_object,
            'status': tracking_manager.get_status()
        })
    
    @app.route('/api/track-update', methods=['POST'])
    def track_update():
        """Update tracking with new frame"""
        data = request.json
        image_data = data.get('image')
        
        if not image_data or not tracking_manager.target_object:
            return jsonify({'error': 'Image and active tracking required'}), 400
        
        try:
            detections = detector.detect(image_data)
            
            # Find matching target object
            matching = [d for d in detections if tracking_manager.target_object in d['name'].lower()]
            
            response = {
                'status': tracking_manager.get_status(),
                'detection': None,
                'instruction': None,
                'directional': None,
                'announcement': None
            }
            
            if matching:
                detection = matching[0]  # Get closest match
                tracking_manager.update_detection(detection)
                response['detection'] = detection
                
                # Generate instructions if time elapsed
                if tracking_manager.should_give_instruction():
                    step_inst = generate_step_instructions(detection.get('distance'))
                    dir_inst = get_directional_instruction(detection.get('position_x'))
                    response['instruction'] = step_inst
                    response['directional'] = dir_inst
                    response['announcement'] = f"{step_inst}. {dir_inst}"
                
                # Check if reached destination
                if detection.get('distance', 999) < 0.2:
                    response['announcement'] = "Destination reached! Object is within your reach"
            else:
                # Object not found in this frame
                timeout_msg = tracking_manager.object_not_found()
                if timeout_msg:
                    response['announcement'] = timeout_msg
                elif tracking_manager.should_check_timeout():
                    response['announcement'] = f"No {tracking_manager.target_object} found after 10 seconds"
            
            # Handle pause state
            if tracking_manager.should_announce_pause():
                response['announcement'] = "Tracking paused"
            
            return jsonify(response)
        except Exception as e:
            print(f"❌ Tracking error: {e}")
            return jsonify({'error': str(e)}), 400
    
    @app.route('/api/pause-tracking', methods=['POST'])
    def pause_tracking():
        """Pause object tracking"""
        message = tracking_manager.pause()
        if message:
            return jsonify({'success': True, 'message': message, 'status': tracking_manager.get_status()})
        return jsonify({'error': 'Not currently tracking'}), 400
    
    @app.route('/api/resume-tracking', methods=['POST'])
    def resume_tracking():
        """Resume object tracking"""
        message = tracking_manager.resume()
        if message:
            return jsonify({'success': True, 'message': message, 'status': tracking_manager.get_status()})
        return jsonify({'error': 'Tracking not paused'}), 400
    
    @app.route('/api/stop-tracking', methods=['POST'])
    def stop_tracking():
        """Stop object tracking completely"""
        message = tracking_manager.stop()
        return jsonify({'success': True, 'message': message})
    
    @app.route('/api/hold-object', methods=['POST'])
    def hold_object():
        """Hold on object for 5 seconds"""
        message = tracking_manager.hold()
        return jsonify({'success': True, 'message': message, 'status': tracking_manager.get_status()})
    
    @app.route('/api/tracking-status', methods=['GET'])
    def get_tracking_status():
        """Get current tracking status"""
        return jsonify(tracking_manager.get_status())
    
    return app
