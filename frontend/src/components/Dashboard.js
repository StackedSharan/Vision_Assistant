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
    iconSize: [40, 40],
    iconAnchor: [20, 40],
    popupAnchor: [0, -40]
});

// CRITICAL: Replace this with your BACKEND ngrok URL
// For local testing, use http://localhost:5000
const SOCKET_URL = 'http://localhost:5000';

// Helper to update map view
function MapUpdater({ center, routeCoords }) {
    const map = useMap();
    useEffect(() => {
        if (routeCoords && routeCoords.length > 0) {
            // Create a bounds object from the route coordinates
            const bounds = L.latLngBounds(routeCoords);
            map.fitBounds(bounds, { padding: [50, 50] });
        } else if (center) {
            map.setView(center, map.getZoom());
        }
    }, [center, routeCoords, map]);
    return null;
}

function Dashboard() {
    const [mode, setMode] = useState('navigation');
    const [statusText, setStatusText] = useState('Initializing...');
    const [navInstructions, setNavInstructions] = useState([]);
    const [routeCoords, setRouteCoords] = useState([]);
    const [currentNavStep, setCurrentNavStep] = useState(0);
    const [isListening, setIsListening] = useState(false);
    const [obstacleMessage, setObstacleMessage] = useState('');
    const [isConnected, setIsConnected] = useState(false);
    const [isSimulating, setIsSimulating] = useState(false);
    const [hasStarted, setHasStarted] = useState(true); // Auto-start in Demo Mode (transitioned from Landing)

    // Voice State Machine: 'IDLE', 'LISTENING_FOR_WAKE', 'LISTENING_FOR_COMMAND', 'CONFIRMING_DESTINATION', 'NAVIGATING'
    const [voiceState, setVoiceState] = useState('IDLE');
    const [pendingDestination, setPendingDestination] = useState(null);

    // Map state
    const [userLocation, setUserLocation] = useState({ lat: 12.9716, lng: 77.5946 });

    const videoRef = useRef(null);
    const socketRef = useRef(null);
    const requestRef = useRef(null);
    const hasWelcomed = useRef(false);
    const lastMsgRef = useRef('');
    const msgCountRef = useRef(0);

    // Enhanced speak function
    const speak = useCallback((text, interrupt = false, onEnd = null) => {
        if (interrupt) window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        if (onEnd) utterance.onend = onEnd;
        window.speechSynthesis.speak(utterance);
    }, []);

    // --- Voice Logic ---
    const recognitionRef = useRef(null);

    const startContinuousListening = useCallback(() => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) return;

        const recognition = new SpeechRecognition();
        recognition.continuous = true; // Keep listening
        recognition.interimResults = false;
        recognition.lang = 'en-US';

        recognition.onresult = (event) => {
            const lastResultIdx = event.results.length - 1;
            const transcript = event.results[lastResultIdx][0].transcript.toLowerCase().trim();
            console.log(`🎤 Heard: "${transcript}" | State: ${voiceState}`);

            handleVoiceInput(transcript);
        };

        recognition.onend = () => {
            // Auto-restart if supposed to be listening
            if (hasStarted) {
                console.log("🔄 Restarting speech recognition...");
                try { recognition.start(); } catch (e) { }
            }
        };

        recognition.onerror = (e) => {
            console.warn("Speech error:", e.error);
        };

        recognitionRef.current = recognition;
        try { recognition.start(); } catch (e) { }
    }, [hasStarted, voiceState]); // Dependencies will be handled via refs in a real implementation to avoid restart loops, but for now this is simple.

    // We need a ref for voiceState to access it inside the callback without re-binding
    const voiceStateRef = useRef(voiceState);
    useEffect(() => { voiceStateRef.current = voiceState; }, [voiceState]);

    const handleVoiceCommand = () => {
        if (!isListening) {
            startContinuousListening();
        } else {
            // Maybe stop listening?
            // recognitionRef.current.stop(); 
        }
    };

    const handleVoiceInput = (text) => {
        const state = voiceStateRef.current;
        setStatusText(`Heard: "${text}"`);

        // Global Commands
        if (text.includes('stop') || text.includes('pause')) {
            speak("Navigation paused.");
            setVoiceState('IDLE');
            return;
        }
        if (text.includes('help')) {
            speak("I am your blind navigation assistant. Say 'Vision' to wake me up, then tell me where you want to go.");
            return;
        }
        if (text.includes('emergency') || text.includes('help me')) {
            speak("Emergency mode activated. Alert sent. Stay calm.");
            if (socketRef.current) {
                socketRef.current.emit('emergency_alert', { location: { lat: userLocation.lat, lng: userLocation.lng } });
            }
            return;
        }

        // State Machine
        switch (state) {
            case 'IDLE':
            case 'LISTENING_FOR_WAKE':
                if (text.includes('hey assist') || text.includes('vision') || text.includes('start navigation')) {
                    speak("Yes, I'm listening. Where would you like to go?");
                    setVoiceState('LISTENING_FOR_COMMAND');
                }
                break;

            case 'LISTENING_FOR_COMMAND':
                // Assume text is destination
                const dest = text.replace(/^(go to|navigate to|take me to)\s+/, '').replace(/[.,?]/g, '');
                setPendingDestination(dest);
                speak(`You want to go to ${dest}. Say 'Yes' to confirm or 'Change' to pick a new destination.`);
                setVoiceState('CONFIRMING_DESTINATION');
                break;

            case 'CONFIRMING_DESTINATION':
                if (text.includes('yes') || text.includes('correct') || text.includes('confirm')) {
                    speak(`Starting navigation to ${pendingDestination}.`);
                    setVoiceState('NAVIGATING');
                    if (socketRef.current) {
                        socketRef.current.emit('get_navigation', { start: 'current', end: pendingDestination });
                    }
                } else if (text.includes('change') || text.includes('no')) {
                    speak("Okay, where would you like to go?");
                    setVoiceState('LISTENING_FOR_COMMAND');
                }
                break;

            case 'NAVIGATING':
                // Mostly silent, waiting for "Stop" or "Vision" to interrupt
                if (text.includes('vision')) {
                    speak("Navigation paused. What would you like to ask?");
                    // Could switch to a CHAT mode here
                }
                break;

            default:
                break;
        }
    };

    // Initialize App
    const initializeApp = () => {
        setHasStarted(true);
        setVoiceState('LISTENING_FOR_WAKE');

        // Auto-ask destination on load (Demo Mode)
        setTimeout(() => {
            speak("Where do you want to go?", false, () => {
                startContinuousListening();
                setVoiceState('LISTENING_FOR_COMMAND');
            });
        }, 1000);

        // 3. Start Camera
        const startCamera = async () => {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: true });
                if (videoRef.current) videoRef.current.srcObject = stream;
            } catch (err) {
                console.error("Camera permission denied", err);
                speak("Camera access denied. Obstacle detection will not work.");
            }
        };
        startCamera();

        // 4. GPS
        const watchId = navigator.geolocation.watchPosition(
            (position) => {
                const { latitude, longitude } = position.coords;
                setUserLocation({ lat: latitude, lng: longitude });
                if (socketRef.current) socketRef.current.emit('location_update', { latitude, longitude });
            },
            (error) => {
                console.error("GPS Error:", error);
                speak("GPS signal unavailable. Switching to indoor navigation mode.");
            },
            { enableHighAccuracy: true, maximumAge: 10000, timeout: 5000 }
        );
    };

    useEffect(() => {
        // Socket Connection
        socketRef.current = io(SOCKET_URL, { transports: ['websocket'] });

        socketRef.current.on('connect', () => {
            console.log('✅ Socket connected!');
            setIsConnected(true);
        });

        socketRef.current.on('disconnect', () => {
            console.log('❌ Socket disconnected!');
            setIsConnected(false);
            speak("Disconnected from server.");
        });

        socketRef.current.on('navigation_response', (data) => {
            console.log("Received navigation response:", data);
            if (data.instructions && data.instructions.length > 0) {
                setNavInstructions(data.instructions);
                if (data.route_coords) setRouteCoords(data.route_coords);
                setCurrentNavStep(0);

                // Speak first instruction
                speak(`Route found. ${data.instructions[0].text}`);
            } else {
                speak("Sorry, a route could not be found.");
            }
        });

        socketRef.current.on('obstacle_alert', (data) => {
            // Handle haptic feedback if vibrate_pattern is provided
            if (data.vibrate_pattern && navigator.vibrate) {
                navigator.vibrate(data.vibrate_pattern);
            }

            if (data.message !== 'Path is clear.') {
                setObstacleMessage(data.message);

                // Repetition Logic: Only speak the same message up to 2 times
                if (data.message === lastMsgRef.current) {
                    if (msgCountRef.current < 2) {
                        speak(data.message, true);
                        msgCountRef.current += 1;
                    }
                } else {
                    // New message, reset counter
                    lastMsgRef.current = data.message;
                    msgCountRef.current = 1;
                    speak(data.message, true);
                }
            } else {
                setObstacleMessage('');
                lastMsgRef.current = '';
                msgCountRef.current = 0;
            }
        });

    }, []); // Empty dependency array to run only once on mount


    // Obstacle Detection Loop (Throttled)
    const lastCaptureTime = useRef(0);

    const captureAndSendForObstacles = useCallback(() => {
        if (!videoRef.current || !socketRef.current) return;

        const now = Date.now();
        if (now - lastCaptureTime.current < 2000) { // Run every 2 seconds
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
    }, []);

    useEffect(() => {
        // Only start obstacle detection if a route is active (user has set a destination)
        if (navInstructions.length > 0) {
            requestRef.current = requestAnimationFrame(captureAndSendForObstacles);
        }
        return () => {
            if (requestRef.current) cancelAnimationFrame(requestRef.current);
        };
    }, [captureAndSendForObstacles, navInstructions]);

    // Periodic Analysis (Every 1 minute)
    useEffect(() => {
        const interval = setInterval(() => {
            if (videoRef.current && socketRef.current) {
                console.log("⏰ Periodic surroundings check...");
                const canvas = document.createElement('canvas');
                canvas.width = videoRef.current.videoWidth;
                canvas.height = videoRef.current.videoHeight;
                canvas.getContext('2d').drawImage(videoRef.current, 0, 0);
                const imageData = canvas.toDataURL('image/jpeg', 0.8);
                socketRef.current.emit('analyze_surroundings', { image_data: imageData });
            }
        }, 60000); // 60000ms = 1 minute

        return () => clearInterval(interval);
    }, []);

    // Long Press Logic
    const longPressTimer = useRef(null);

    const handleTouchStart = () => {
        longPressTimer.current = setTimeout(() => {
            // Trigger ChatBox
            window.dispatchEvent(new CustomEvent('activate-chat'));
            // Provide haptic feedback
            if (navigator.vibrate) navigator.vibrate(50);
        }, 800); // 800ms long press
    };

    const handleTouchEnd = () => {
        if (longPressTimer.current) {
            clearTimeout(longPressTimer.current);
        }
    };


    // Helper for distance (Haversine)
    const getDistanceFromLatLonInMeters = (lat1, lon1, lat2, lon2) => {
        var R = 6371; // Radius of the earth in km
        var dLat = (lat2 - lat1) * (Math.PI / 180);
        var dLon = (lon2 - lon1) * (Math.PI / 180);
        var a =
            Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(lat1 * (Math.PI / 180)) * Math.cos(lat2 * (Math.PI / 180)) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
        var c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
        var d = R * c * 1000; // Distance in meters
        return d;
    };

    // Simulation Logic
    useEffect(() => {
        let simTimer;
        if (isSimulating && routeCoords.length > 0) {
            let simIndex = 0;
            // Find closest point on route to start simulation from, or just start from beginning
            // For simplicity, we'll just iterate through the route coords
            simTimer = setInterval(() => {
                if (simIndex < routeCoords.length) {
                    const point = routeCoords[simIndex];
                    setUserLocation({ lat: point[0], lng: point[1] }); // Leaflet uses [lat, lng]
                    simIndex++;
                } else {
                    setIsSimulating(false);
                    clearInterval(simTimer);
                }
            }, 1000); // Move every 1 second
        }
        return () => clearInterval(simTimer);
    }, [isSimulating, routeCoords]);

    // Check for step progression
    useEffect(() => {
        if (navInstructions.length > 0 && currentNavStep < navInstructions.length) {
            const target = navInstructions[currentNavStep].coords; // [lon, lat] from backend
            // Backend sends [lon, lat], so target[1] is lat, target[0] is lon
            const dist = getDistanceFromLatLonInMeters(userLocation.lat, userLocation.lng, target[1], target[0]);

            console.log(`Distance to next waypoint: ${dist.toFixed(1)}m`);

            if (dist < 15) { // 15 meters threshold
                const nextStep = currentNavStep + 1;
                if (nextStep < navInstructions.length) {
                    setCurrentNavStep(nextStep);
                    speak(navInstructions[nextStep].text, true);
                } else {
                    speak("You have arrived at your destination.", true);
                    setNavInstructions([]);
                    setRouteCoords([]);
                    setCurrentNavStep(0);
                    setIsSimulating(false);
                }
            }
        }
    }, [userLocation, navInstructions, currentNavStep, speak]);

    return (
        <div
            className="dashboard-container"
            onTouchStart={handleTouchStart}
            onTouchEnd={handleTouchEnd}
            onMouseDown={handleTouchStart} // For mouse testing
            onMouseUp={handleTouchEnd}
            onMouseLeave={handleTouchEnd}
        >
            {/* Overlay removed for Demo Mode - handled by LandingPage */
                !hasStarted && (
                    <div style={{ display: 'none' }} onClick={initializeApp}></div>
                )}
            <div className="connection-status" style={{ position: 'absolute', top: '10px', right: '10px', zIndex: 1000, background: isConnected ? 'green' : 'red', padding: '5px', borderRadius: '5px', color: 'white', fontSize: '12px' }}>
                {isConnected ? 'Online' : 'Offline'}
            </div>
            <video ref={videoRef} autoPlay playsInline muted className="hidden-video" />

            <div className="search-bar-container">
                <div className="search-bar">
                    <span className="search-icon">🔍</span>
                    <input type="text" placeholder="Search here" className="search-input" disabled />
                    <span className={`mic-icon ${isListening ? 'listening' : ''}`} onClick={handleVoiceCommand}>
                        {isListening ? '🔴' : '🎤'}
                    </span>
                </div>
                <button
                    onClick={() => {
                        console.log("Testing route: Entrance -> Architecture");
                        socketRef.current.emit('get_navigation', { start: 'entrance', end: 'architecture' });
                    }}
                    style={{ marginTop: '10px', padding: '5px 10px', background: '#4285F4', color: 'white', border: 'none', borderRadius: '5px' }}
                >
                    Test Route
                </button>
            </div>

            <div className="map-wrapper">
                <MapContainer center={[userLocation.lat, userLocation.lng]} zoom={19} scrollWheelZoom={true} style={{ height: '100%', width: '100%' }}>
                    <TileLayer
                        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
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
                            {/* Start Point Marker */}
                            <Marker position={routeCoords[0]}>
                                <Popup>Start: Entrance</Popup>
                            </Marker>
                            {/* End Point Marker */}
                            <Marker position={routeCoords[routeCoords.length - 1]}>
                                <Popup>Destination</Popup>
                            </Marker>
                        </>
                    )}

                    <MapUpdater
                        center={[userLocation.lat, userLocation.lng]}
                        routeCoords={routeCoords}
                    />
                </MapContainer>
            </div>

            <div className="bottom-sheet">
                <div className="sheet-handle"></div>
                <div className="sheet-content">
                    <h3>{navInstructions.length > 0 ? "Navigation Active" : "Where to?"}</h3>
                    <p className="status-text">{statusText}</p>
                    {obstacleMessage && <div className="obstacle-alert">{obstacleMessage}</div>}

                    {navInstructions.length > 0 && (
                        <div className="nav-step-display">
                            <span className="direction-icon">⬆️</span>
                            <span className="instruction-text">{navInstructions[currentNavStep].text}</span>
                            <div className="step-indicator">Step {currentNavStep + 1} of {navInstructions.length}</div>
                            <button
                                onClick={() => {
                                    const next = currentNavStep + 1;
                                    if (next < navInstructions.length) {
                                        setCurrentNavStep(next);
                                        speak(navInstructions[next].text, true);
                                    } else {
                                        speak("You have arrived.", true);
                                    }
                                }}
                                style={{ marginTop: '10px', padding: '8px', background: '#eee', border: 'none', borderRadius: '5px', width: '100%' }}
                            >
                                Next Step (Test) ➡️
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </div >
    );
}

export default Dashboard;
