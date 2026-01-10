import React, { useState, useRef, useEffect, useCallback } from 'react';
import io from 'socket.io-client';
import '../App.css';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default marker icon
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
    iconRetinaUrl: require('leaflet/dist/images/marker-icon-2x.png'),
    iconUrl: require('leaflet/dist/images/marker-icon.png'),
    shadowUrl: require('leaflet/dist/images/marker-shadow.png'),
});

// Person SVG Icon
const personIcon = new L.Icon({
    iconUrl: 'data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0iIzQyODVGNCIgd2lkdGg9IjQ4cHgiIGhlaWdodD0iNDhweCI+PHBhdGggZD0iTTEyIDEyYzIuMjEgMCA0LTEuNzkgNC00cy0xLjc5LTQtNC00LTQgMS43OS00IDQgMS43OSA0IDQgNHptMCAyYy0yLjY3IDAtOCAxLjM0LTggNHYyaDE2di0yYzAtMi42Ni01LjMzLTQtOC00eiIvPjwvc3ZnPg==',
    iconSize: [30, 30],
    iconAnchor: [15, 30],
    popupAnchor: [0, -30]
});

const SOCKET_URL = 'http://localhost:5000';

function MapUpdater({ center, routeCoords, isActive }) {
    const map = useMap();
    useEffect(() => {
        if (routeCoords && routeCoords.length > 0) {
            const bounds = L.latLngBounds(routeCoords);
            map.fitBounds(bounds, { padding: [50, 50] });
        } else if (center) {
            // Zoom 19 normally, 21 if active/navigating
            map.setView(center, isActive ? 21 : 19);
        }
    }, [center, routeCoords, map, isActive]);
    return null;
}

function Dashboard() {
    const [statusText, setStatusText] = useState('Where do you want to go?');
    const [navInstructions, setNavInstructions] = useState([]);
    const [routeCoords, setRouteCoords] = useState([]);
    const [currentNavStep, setCurrentNavStep] = useState(0);
    const [isListening, setIsListening] = useState(false);

    // Obstacle state
    const [obstacleAlert, setObstacleAlert] = useState(null); // { message, urgency }

    const [isConnected, setIsConnected] = useState(false);

    // UI States
    const [isMapBlurred, setIsMapBlurred] = useState(true);
    const [voiceState, setVoiceState] = useState('LISTENING_FOR_COMMAND');

    // Fixed Start at Entrance
    const [userLocation, setUserLocation] = useState({ lat: 13.1217, lng: 77.6206 });

    const videoRef = useRef(null);
    const socketRef = useRef(null);
    const requestRef = useRef(null);
    const voiceStateRef = useRef(voiceState);

    const recognitionRef = useRef(null);
    const loopTimerRef = useRef(null);

    // Swipe state
    const touchStartRef = useRef(null);
    const touchEndRef = useRef(null);
    const minSwipeDistance = 50;

    const handleVoiceInput = useCallback((text) => {
        const state = voiceStateRef.current;
        setStatusText(`Heard: "${text}"`);
        if (navigator.vibrate) navigator.vibrate(50); // Haptic confirm

        // Stop the loop if we hear *anything* substantial
        if (loopTimerRef.current) clearTimeout(loopTimerRef.current);

        if (state === 'LISTENING_FOR_COMMAND' || state === 'IDLE') {
            const dest = text.replace(/^(go to|navigate to|take me to|i want to go to)\s+/, '').replace(/[.,?]/g, '');

            if (dest.length > 2) {
                setVoiceState('NAVIGATING');
                speak(`Navigating to ${dest}.`);

                // Unblur map and start process
                setIsMapBlurred(false);

                if (socketRef.current) {
                    socketRef.current.emit('get_navigation', { start: 'Entrance', end: dest });
                }
            } else {
                // If heard something too short/noise, restart loop delay
                // But don't speak immediately to avoid cutting off user
                loopTimerRef.current = setTimeout(() => {
                    const currentState = voiceStateRef.current;
                    if (currentState === 'LISTENING_FOR_COMMAND') {
                        speak("Where do you want to go?");
                    }
                }, 8000); // Relaxed to 8s
            }
        }
    }, [speak]); // Stable dependency

    // --- Voice Logic ---
    const startContinuousListening = useCallback(() => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) return;

        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onresult = (event) => {
            const lastResultIdx = event.results.length - 1;
            const transcript = event.results[lastResultIdx][0].transcript.toLowerCase().trim();
            console.log(`🎤 Heard: "${transcript}"`);
            handleVoiceInput(transcript);
        };

        recognition.onend = () => {
            // Auto-restart to keep loop alive
            try { recognition.start(); } catch (e) { }
        };

        recognitionRef.current = recognition;
        try { recognition.start(); } catch (e) { }
    }, [handleVoiceInput]); // Depend on stable handleVoiceInput

    useEffect(() => { voiceStateRef.current = voiceState; }, [voiceState]);

    // Enhanced speak function
    const speak = useCallback((text, interrupt = false, onEnd = null) => {
        if (interrupt) window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        if (onEnd) utterance.onend = onEnd;
        window.speechSynthesis.speak(utterance);
    }, []);

    // Voice Loop Logic
    useEffect(() => {
        if (voiceState === 'LISTENING_FOR_COMMAND') {
            const loopPrompt = () => {
                speak("Where do you want to go?");
                loopTimerRef.current = setTimeout(loopPrompt, 8000); // 8s
            };
            // Initial prompt only if we just entered this state (debounced slightly?)
            // We rely on the initial useEffect call or state change
            // To avoid double speak on mount, check a ref? 
            // Simplified: Just start the loop.
            // But we must clear existing manually to be safe.
            if (loopTimerRef.current) clearTimeout(loopTimerRef.current);
            loopTimerRef.current = setTimeout(loopPrompt, 1000); // Wait 1s before first prompt 
        }
        return () => {
            if (loopTimerRef.current) clearTimeout(loopTimerRef.current);
        }
    }, [voiceState, speak]);


    // Initialization
    useEffect(() => {
        // Start Camera
        const startCamera = async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: true });
                if (videoRef.current) videoRef.current.srcObject = stream;
            } catch (err) {
                console.error("Camera permission denied", err);
            }
        };
        startCamera();

        // Start listening
        startContinuousListening();

        // Socket
        socketRef.current = io(SOCKET_URL, { transports: ['websocket'] });
        socketRef.current.on('connect', () => setIsConnected(true));
        socketRef.current.on('disconnect', () => setIsConnected(false));

        socketRef.current.on('navigation_response', (data) => {
            if (data.instructions && data.instructions.length > 0) {
                setNavInstructions(data.instructions);
                setRouteCoords(data.route_coords || []);
                setCurrentNavStep(0);
                speak(`Route found. ${data.instructions[0].text}`);
            } else {
                speak("Sorry, I couldn't find that place. Please say it again.");
                // Go back to listening loop
                setVoiceState('LISTENING_FOR_COMMAND');
                setIsMapBlurred(true);
            }
        });

        socketRef.current.on('obstacle_alert', (data) => {
            // Only alert if we are navigating
            if (voiceStateRef.current !== 'NAVIGATING') return;

            if (data.message && data.message !== 'Path is clear.') {
                // Show High-Vis Overlay
                setObstacleAlert({ message: data.message, urgency: data.urgency });

                // Double Verbal Warning
                speak(`Warning. ${data.message}. Warning. ${data.message}.`, true);

                // Haptic
                if (navigator.vibrate) navigator.vibrate([200, 100, 200]);

                // Clear visual alert after 3 seconds
                setTimeout(() => setObstacleAlert(null), 3000);
            }
        });

    }, [startContinuousListening, speak]);

    // Obstacle Detection Loop
    const lastCaptureTime = useRef(0);
    const captureAndSendForObstacles = useCallback(() => {
        if (!videoRef.current || !socketRef.current) return;

        // CRITICAL FIX: Only capture if we are actively navigating (instructions exist)
        // This prevents "person ahead" warnings while choosing destination
        if (navInstructions.length === 0) {
            requestRef.current = requestAnimationFrame(captureAndSendForObstacles);
            return;
        }

        const now = Date.now();
        if (now - lastCaptureTime.current < 1000) { // Check every 1s
            requestRef.current = requestAnimationFrame(captureAndSendForObstacles);
            return;
        }
        lastCaptureTime.current = now;

        const canvas = document.createElement('canvas');
        canvas.width = videoRef.current.videoWidth;
        canvas.height = videoRef.current.videoHeight;
        canvas.getContext('2d').drawImage(videoRef.current, 0, 0);
        const imageData = canvas.toDataURL('image/jpeg', 0.5);
        socketRef.current.emit('process_frame_for_obstacles', { image_data: imageData });
        requestRef.current = requestAnimationFrame(captureAndSendForObstacles);
    }, [navInstructions]); // Dependency on navInstructions

    useEffect(() => {
        // Run detection always, but it will skip logic if no instructions
        requestRef.current = requestAnimationFrame(captureAndSendForObstacles);
        return () => { if (requestRef.current) cancelAnimationFrame(requestRef.current); };
    }, [captureAndSendForObstacles]);


    // Gestures
    const onTouchStart = (e) => {
        touchStartRef.current = e.targetTouches[0].clientX;
    };
    const onTouchEnd = (e) => {
        touchEndRef.current = e.changedTouches[0].clientX;
        if (!touchStartRef.current || !touchEndRef.current) return;

        const distance = touchStartRef.current - touchEndRef.current;
        if (distance > minSwipeDistance) {
            // Left Swipe -> Chatbot
            console.log("Left Swipe -> Chatbot");
            speak("Chatbot feature coming soon.");
        } else if (distance < -minSwipeDistance) {
            // Right Swipe -> Next Instruction
            handleNextStep();
        }
    };

    const handleNextStep = () => {
        if (navInstructions.length === 0) return;
        const next = currentNavStep + 1;
        if (next < navInstructions.length) {
            setCurrentNavStep(next);
            speak(navInstructions[next].text, true);
        } else {
            speak("You have arrived.", true);
            setNavInstructions([]);
            setRouteCoords([]);
            setIsMapBlurred(true);
            setVoiceState('LISTENING_FOR_COMMAND');
        }
    };

    return (
        <div className="dashboard-container dark-mode"
            onTouchStart={onTouchStart}
            onTouchEnd={onTouchEnd}
        >
            {/* Obstacle Overlay */}
            {obstacleAlert && (
                <div className="obstacle-warning-overlay">
                    <div className="warning-icon">!</div>
                    <div className="warning-text">{obstacleAlert.message}</div>
                </div>
            )}

            <div className="connection-status" style={{ position: 'absolute', top: '10px', right: '10px', zIndex: 1000, background: isConnected ? 'green' : 'red', padding: '5px', borderRadius: '5px', color: 'white', fontSize: '12px' }}>
                {isConnected ? 'Online' : 'Offline'}
            </div>

            <video ref={videoRef} autoPlay playsInline muted className="hidden-video" />

            {/* Blinking Prompt (only when blurred) */}
            {isMapBlurred && (
                <div className="blinking-prompt">
                    Where do you want to go?
                </div>
            )}

            <div className={`map-wrapper ${isMapBlurred ? 'map-blur' : 'map-clear'}`}>
                <MapContainer center={[userLocation.lat, userLocation.lng]} zoom={19} scrollWheelZoom={true} style={{ height: '100%', width: '100%' }}>
                    <TileLayer
                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
                        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                    />
                    <Marker position={[userLocation.lat, userLocation.lng]} icon={personIcon}>
                        <Popup>You are here</Popup>
                    </Marker>

                    {routeCoords.length > 0 && (
                        <>
                            <Polyline
                                positions={routeCoords}
                                pathOptions={{ color: '#4285F4', weight: 6, opacity: 0.8 }}
                            />
                            <Marker position={routeCoords[routeCoords.length - 1]}>
                                <Popup>Destination</Popup>
                            </Marker>
                        </>
                    )}

                    <MapUpdater center={[userLocation.lat, userLocation.lng]} routeCoords={routeCoords} isActive={!isMapBlurred} />
                </MapContainer>
            </div>

            {/* Instruction Overlay (only when navigating) */}
            {!isMapBlurred && navInstructions.length > 0 && (
                <div className="bottom-sheet">
                    <div className="sheet-handle"></div>
                    <div className="sheet-content">
                        <h3>Navigation Active</h3>
                        <div className="nav-step-display">
                            <span className="direction-icon">⬆️</span>
                            <span className="instruction-text">{navInstructions[currentNavStep].text}</span>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}

export default Dashboard;
