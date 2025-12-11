import React, { useState, useRef, useEffect, useCallback } from 'react';
import io from 'socket.io-client';
import '../App.css';
import MapComponent from './MapComponent';
import { useNavigate } from 'react-router-dom';

// IMPORTANT: Replace this with your BACKEND ngrok URL (from port 5000)
const SOCKET_URL = 'https://carmon-uncorroborant-nonmonistically.ngrok-free.dev';

const Dashboard = () => {
    const [statusText, setStatusText] = useState('Where to?');
    const [isListening, setIsListening] = useState(false);
    const [navInstructions, setNavInstructions] = useState([]);
    const [currentNavStep, setCurrentNavStep] = useState(0);
    const [routeCoords, setRouteCoords] = useState(null);
    const [currentLocation, setCurrentLocation] = useState(null);
    const [obstacleMessage, setObstacleMessage] = useState('');

    const videoRef = useRef(null);
    const socketRef = useRef(null);
    const requestRef = useRef(null);
    const hasSpokenWelcome = useRef(false); // Fix for infinite loop
    const navigate = useNavigate();

    const speak = useCallback((text, interrupt = false) => {
        if (interrupt) window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        window.speechSynthesis.speak(utterance);
    }, []);

    // Initial Voice Prompt - Only once
    useEffect(() => {
        if (!hasSpokenWelcome.current) {
            const timer = setTimeout(() => {
                speak("Please tell me, where do you want to go?");
                hasSpokenWelcome.current = true;
            }, 1000);
            return () => clearTimeout(timer);
        }
    }, [speak]);

    const parseNavigationCommand = useCallback((command) => {
        const locations = ['entrance', 'engineering block', 'architecture', 'ug block', 'canteen', 'parking', 'aiml block'];

        // Logic to handle "Take me to X" or "Go from X to Y"
        let fromLocation = locations.find(loc => command.includes(`from ${loc}`));
        let toLocation = locations.find(loc => command.includes(`to ${loc}`));

        // If "from" is missing but "to" is present (e.g. "Take me to Canteen")
        if (!fromLocation && !toLocation) {
            const found = locations.filter(loc => command.includes(loc));
            if (found.length >= 2) {
                fromLocation = found[0];
                toLocation = found[1];
            } else if (found.length === 1) {
                toLocation = found[0];
                // Use GPS if available, else default to Entrance
                if (currentLocation) {
                    fromLocation = currentLocation; // Send [lat, lon]
                } else {
                    fromLocation = "entrance";
                }
            }
        } else if (!fromLocation && toLocation) {
            // "Take me to X"
            if (currentLocation) {
                fromLocation = currentLocation; // Send [lat, lon]
            } else {
                fromLocation = "entrance";
            }
        }

        if (fromLocation && toLocation && socketRef.current) {
            // Clean up strings if they are strings
            if (typeof fromLocation === 'string') fromLocation = fromLocation.replace('from ', '').trim();
            if (typeof toLocation === 'string') toLocation = toLocation.replace('to ', '').trim();

            if (fromLocation === toLocation) {
                speak(`You are already at ${toLocation}.`);
                return;
            }

            socketRef.current.emit('get_navigation', { start: fromLocation, end: toLocation });

            const startText = typeof fromLocation === 'string' ? fromLocation : 'Current Location';
            setStatusText(`Routing: ${startText} to ${toLocation}`);
            speak(`Calculating route from ${startText} to ${toLocation}`);
        } else {
            const defaultMessage = 'Try "Go from Entrance to Canteen"';
            setStatusText(defaultMessage);
            speak("I didn't catch the locations. Please say something like, Go from Entrance to Canteen.");
        }
    }, [speak, currentLocation]);

    const handleVoiceCommand = useCallback(() => {
        if (isListening) return;

        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        recognition.continuous = false;
        recognition.lang = 'en-US';

        setIsListening(true);
        setStatusText('Listening...');

        recognition.onresult = (event) => {
            const command = event.results[0][0].transcript.toLowerCase();
            setStatusText(command);
            parseNavigationCommand(command);
        };

        recognition.onend = () => setIsListening(false);
        recognition.onerror = (e) => {
            console.error(e);
            setIsListening(false);
            setStatusText('Tap mic to try again');
        };

        recognition.start();
    }, [isListening, parseNavigationCommand]);

    // Obstacle detection logic
    const captureAndSendForObstacles = useCallback(() => {
        if (!videoRef.current || videoRef.current.paused || videoRef.current.ended || !socketRef.current) return;
        const canvas = document.createElement('canvas');
        canvas.width = videoRef.current.videoWidth;
        canvas.height = videoRef.current.videoHeight;
        canvas.getContext('2d').drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
        const imageData = canvas.toDataURL('image/jpeg', 0.5);
        socketRef.current.emit('process_frame_for_obstacles', { image_data: imageData });
    }, []);

    const startObstacleDetectionLoop = useCallback(() => {
        requestRef.current = requestAnimationFrame(captureAndSendForObstacles);
    }, [captureAndSendForObstacles]);

    useEffect(() => {
        // Geolocation Tracking
        if (navigator.geolocation) {
            const watchId = navigator.geolocation.watchPosition(
                (position) => {
                    const { latitude, longitude } = position.coords;
                    // Update current location [lon, lat] for GeoJSON compatibility
                    setCurrentLocation([longitude, latitude]);
                },
                (error) => {
                    console.error("Geolocation error:", error);
                },
                { enableHighAccuracy: true, maximumAge: 10000, timeout: 5000 }
            );
            return () => navigator.geolocation.clearWatch(watchId);
        }
    }, []);

    useEffect(() => {
        socketRef.current = io(SOCKET_URL, { transports: ['websocket'] });

        socketRef.current.on('navigation_response', (data) => {
            if (data.error) {
                speak(data.error);
                setStatusText(data.error);
            } else {
                setNavInstructions(data.instructions);
                if (data.path) {
                    setRouteCoords(data.path);
                    // Don't overwrite current location if we are tracking GPS
                    // But maybe snap to start of path?
                    // For now, let GPS drive current location
                }
                setCurrentNavStep(0);
                speak(`Starting route. ${data.instructions[0]}`);
                startObstacleDetectionLoop();
            }
        });

        socketRef.current.on('obstacle_alert', (data) => {
            if (data.message !== 'Path is clear.') {
                setObstacleMessage(data.message);
                speak(data.message, true);
            } else {
                setObstacleMessage('');
            }
        });

        socketRef.current.on('request_next_frame', () => {
            if (navInstructions.length > 0) startObstacleDetectionLoop();
        });

        navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
            .then(stream => {
                if (videoRef.current) videoRef.current.srcObject = stream;
            })
            .catch(err => console.error("Camera error:", err));

        return () => {
            if (socketRef.current) socketRef.current.disconnect();
            if (requestRef.current) cancelAnimationFrame(requestRef.current);
        };
    }, [startObstacleDetectionLoop, navInstructions.length, speak]);

    const handleNextStep = () => {
        if (currentNavStep < navInstructions.length - 1) {
            const nextStep = currentNavStep + 1;
            setCurrentNavStep(nextStep);
            speak(navInstructions[nextStep]);
            if (routeCoords && routeCoords.length > nextStep) {
                const progressIndex = Math.floor((nextStep / navInstructions.length) * routeCoords.length);
                setCurrentLocation(routeCoords[progressIndex]);
            }
        } else {
            speak("You have arrived.");
            setNavInstructions([]);
            setRouteCoords(null);
            setObstacleMessage('');
            setStatusText('Where to?');
        }
    };

    return (
        <div className="App" onClick={() => {
            // If clicking anywhere on dashboard, maybe trigger voice command if not active?
            // User asked: "When the blind person clicks anywhere on the screen it should take to the dashboard" (already there)
            // "It should ask for a single time command... and listen"
            // Let's make clicking anywhere trigger listening if not already listening
            if (!isListening) handleVoiceCommand();
        }}>
            <video ref={videoRef} autoPlay playsInline muted style={{ display: 'none' }} />

            <div className="search-bar-container">
                <div className="search-box">
                    <span className="menu-icon" onClick={(e) => {
                        e.stopPropagation(); // Prevent triggering voice command
                        navigate('/'); // Go back to landing
                    }}>⬅</span>
                    <input
                        type="text"
                        className="search-input"
                        placeholder={statusText}
                        readOnly
                    />
                    <div
                        className={`mic-icon ${isListening ? 'listening' : ''}`}
                        onClick={(e) => {
                            e.stopPropagation();
                            handleVoiceCommand();
                        }}
                    >
                        🎤
                    </div>
                </div>
            </div>

            <div className="map-container">
                <MapComponent
                    routeCoords={routeCoords}
                    currentLocation={currentLocation}
                />
            </div>

            {obstacleMessage && (
                <div className="obstacle-alert">
                    ⚠️ {obstacleMessage}
                </div>
            )}

            <div className="fab" onClick={(e) => {
                e.stopPropagation();
                if (currentLocation) console.log("Recenter");
            }}>
                📍
            </div>

            {navInstructions.length > 0 && (
                <div className="bottom-card" onClick={(e) => e.stopPropagation()}>
                    <div className="route-info">
                        <div className="time-dist">
                            <span className="time">12 min</span>
                            <span className="dist">(1.2 km)</span>
                        </div>
                        <p className="instruction-text">
                            {navInstructions[currentNavStep]}
                        </p>
                    </div>
                    <div className="action-buttons">
                        <button className="btn-secondary" onClick={() => {
                            setNavInstructions([]);
                            setRouteCoords(null);
                            setStatusText('Where to?');
                        }}>Exit</button>
                        <button className="btn-primary" onClick={handleNextStep}>Next Step</button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Dashboard;
