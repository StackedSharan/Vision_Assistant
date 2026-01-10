import React, { useState, useRef, useEffect, useCallback } from 'react';
import io from 'socket.io-client';
import '../App.css';

const SOCKET_URL = 'http://localhost:5000';

const DetectionRipple = ({ detection, index }) => {
    const left = (detection.position_x || 0.5) * 100;
    const distance = detection.distance || 5;
    const scale = Math.max(0.4, 2.5 - distance / 2);
    const opacity = Math.max(0.1, 0.8 - distance / 6);

    return (
        <div
            className={`detection-ripple ${detection.urgency === 'CRITICAL' ? 'critical' : ''}`}
            style={{
                left: `${left}%`,
                top: '50%',
                width: `${100 * scale}px`,
                height: `${100 * scale}px`,
                borderColor: detection.urgency === 'CRITICAL' ? 'var(--critical-red)' : 'var(--neon-blue)',
                opacity: opacity,
                boxShadow: detection.urgency === 'CRITICAL' ? '0 0 30px var(--critical-red)' : 'none'
            }}
        />
    );
};

function Dashboard() {
<<<<<<< HEAD
    const [statusText, setStatusText] = useState('Initializing...');
    const [detections, setDetections] = useState([]);
=======
    const [mode, setMode] = useState('navigation');
    const [statusText, setStatusText] = useState('Initializing...');
    const [navInstructions, setNavInstructions] = useState([]);
    const [routeCoords, setRouteCoords] = useState([]);
    const [currentNavStep, setCurrentNavStep] = useState(0);
>>>>>>> bdc5b15c50262411885aea250c797832ada78e59
    const [isListening, setIsListening] = useState(false);
    const [isConnected, setIsConnected] = useState(false);
<<<<<<< HEAD
    const [systemState, setSystemState] = useState('idle');
    const [navStatus, setNavStatus] = useState({ active: false, next_step: '', distance_to_step: 0 });
    const [sessionStarted, setSessionStarted] = useState(false);
    const [isGreeting, setIsGreeting] = useState(false);
=======
    const [isSimulating, setIsSimulating] = useState(false);
    const [hasStarted, setHasStarted] = useState(true); // Auto-start in Demo Mode (transitioned from Landing)

    // Voice State Machine: 'IDLE', 'LISTENING_FOR_WAKE', 'LISTENING_FOR_COMMAND', 'CONFIRMING_DESTINATION', 'NAVIGATING'
    const [voiceState, setVoiceState] = useState('IDLE');
    const [pendingDestination, setPendingDestination] = useState(null);

    // Map state
    const [userLocation, setUserLocation] = useState({ lat: 12.9716, lng: 77.5946 });
>>>>>>> bdc5b15c50262411885aea250c797832ada78e59

    const videoRef = useRef(null);
    const socketRef = useRef(null);
    const recognitionRef = useRef(null);
    const containerRef = useRef(null);
    const touchY = useRef(0);

    const playBeep = useCallback(() => {
        try {
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const masterGain = audioCtx.createGain();
            masterGain.gain.setValueAtTime(0.2, audioCtx.currentTime);
            masterGain.connect(audioCtx.destination);

            // Dual oscillator "Ping" sound
            const osc1 = audioCtx.createOscillator();
            const osc2 = audioCtx.createOscillator();

            osc1.type = 'sine';
            osc1.frequency.setValueAtTime(880, audioCtx.currentTime); // A5

            osc2.type = 'sine';
            osc2.frequency.setValueAtTime(1760, audioCtx.currentTime); // A6 (harmonics)

            const oscGain = audioCtx.createGain();
            oscGain.gain.setValueAtTime(0.5, audioCtx.currentTime);
            oscGain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + 0.3);

            osc1.connect(oscGain);
            osc2.connect(oscGain);
            oscGain.connect(masterGain);

            osc1.start();
            osc2.start();
            osc1.stop(audioCtx.currentTime + 0.3);
            osc2.stop(audioCtx.currentTime + 0.3);
        } catch (e) { }
    }, []);

    const playAlertSound = useCallback(() => {
        try {
            const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
            const oscillator = audioCtx.createOscillator();
            const gainNode = audioCtx.createGain();
            oscillator.type = 'square';
            oscillator.frequency.setValueAtTime(880, audioCtx.currentTime);
            gainNode.gain.setValueAtTime(0.1, audioCtx.currentTime);
            oscillator.connect(gainNode);
            gainNode.connect(audioCtx.destination);
            oscillator.start();
            oscillator.stop(audioCtx.currentTime + 0.1);
        } catch (e) { }
    }, []);

    const speak = useCallback((text, onEnd) => {
        if (!window.speechSynthesis) return;
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        if (onEnd) utterance.onend = onEnd;
        window.speechSynthesis.speak(utterance);
    }, []);

<<<<<<< HEAD
    const handleNextStep = useCallback(() => {
        if (socketRef.current) socketRef.current.emit('voice_command', { text: 'next step' });
=======
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
>>>>>>> bdc5b15c50262411885aea250c797832ada78e59
    }, []);

    const handlePrevStep = useCallback(() => {
        if (socketRef.current) socketRef.current.emit('voice_command', { text: 'repeat' });
    }, []);

    // Gesture Handlers
    const onTouchEnd = useCallback((e) => {
        const deltaY = touchY.current - e.changedTouches[0].clientY;
        const threshold = 50; // Increased sensitivity

        console.log(`☝️ Touch End DeltaY: ${deltaY}`);

        if (Math.abs(deltaY) > threshold) {
            // Success!
            if (deltaY > threshold) {
                console.log("⬆️ NEXT STEP triggered");
                setStatusText("Next Step...");
                handleNextStep();
            } else if (deltaY < -threshold) {
                console.log("⬇️ PREVIOUS STEP triggered");
                setStatusText("Previous Step...");
                handlePrevStep();
            }
        }
    }, [handleNextStep, handlePrevStep]);

    const onTouchStart = useCallback((e) => {
        touchY.current = e.touches[0].clientY;
        console.log(`👇 Touch Start Y: ${touchY.current}`);
    }, []);

    const onTouchMove = useCallback((e) => {
        if (e.cancelable) e.preventDefault();
    }, []);

    // Attach Non-Passive Listeners
    useEffect(() => {
<<<<<<< HEAD
        const container = containerRef.current;
        if (!container) return;

        container.addEventListener('touchstart', onTouchStart, { passive: true });
        container.addEventListener('touchmove', onTouchMove, { passive: false });
        container.addEventListener('touchend', onTouchEnd, { passive: false });

=======
        // Only start obstacle detection if a route is active (user has set a destination)
        if (navInstructions.length > 0) {
            requestRef.current = requestAnimationFrame(captureAndSendForObstacles);
        }
>>>>>>> bdc5b15c50262411885aea250c797832ada78e59
        return () => {
            container.removeEventListener('touchstart', onTouchStart);
            container.removeEventListener('touchmove', onTouchMove);
            container.removeEventListener('touchend', onTouchEnd);
        };
<<<<<<< HEAD
    }, [onTouchStart, onTouchMove, onTouchEnd]);
=======
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
>>>>>>> bdc5b15c50262411885aea250c797832ada78e59

    // Continuous Voice Automation
    const startVoiceAutomation = useCallback(() => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) return;

<<<<<<< HEAD
        if (recognitionRef.current) {
            try { recognitionRef.current.stop(); } catch (e) { }
        }

        const recognition = new SpeechRecognition();
        recognition.lang = 'en-US';
        recognition.continuous = true;
        recognition.interimResults = false;

        recognition.onstart = () => {
            setIsListening(true);
            setSystemState('listening');
            setStatusText("I am listening...");
        };

        recognition.onresult = (event) => {
            const command = event.results[event.results.length - 1][0].transcript.toLowerCase();
            setStatusText(`Received: "${command}"`);
            if (socketRef.current) socketRef.current.emit('voice_command', { text: command });
        };

        recognition.onend = () => {
            setIsListening(false);
            if (sessionStarted && !isGreeting) {
                setTimeout(() => {
                    try { recognition.start(); } catch (e) { }
                }, 100);
            }
        };

        recognition.start();
        recognitionRef.current = recognition;
    }, [sessionStarted, isGreeting]);

    const handleStartSession = useCallback(() => {
        if (!sessionStarted) {
            setSessionStarted(true);
            setIsGreeting(true);
            setStatusText("Activating...");

            // 1. Initial Greeting
            speak("PLEASE SPEAK YOUR DESTINATION AFTER THE BEEP", () => {
                // 2. Play Beep
                playBeep();
                // 3. Start Listening
                setIsGreeting(false);
                startVoiceAutomation();
            });

            // Initialization for Socket and Camera
            if (navigator.mediaDevices?.getUserMedia) {
                navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' } })
                    .then(stream => { if (videoRef.current) videoRef.current.srcObject = stream; })
                    .catch(err => setStatusText("Camera Error"));
            }
        }
    }, [sessionStarted, speak, playBeep, startVoiceAutomation]);

    // AUTO-START ON MOUNT (Accessible Flow)
    useEffect(() => {
        const timer = setTimeout(() => {
            handleStartSession();
        }, 800); // Give time for transition/socket
        return () => clearTimeout(timer);
    }, [handleStartSession]);

    useEffect(() => {
        socketRef.current = io(SOCKET_URL);
        socketRef.current.on('connect', () => setIsConnected(true));
        socketRef.current.on('speak', (data) => {
            speak(data.text);
            setStatusText(data.text);
        });
        socketRef.current.on('alert_sound', () => playAlertSound());
        socketRef.current.on('detections_update', (data) => {
            setDetections(data.detections || []);
            const hasCritical = data.detections?.some(d => d.urgency === 'CRITICAL');
            if (hasCritical) setSystemState('critical');
            else if (data.detections?.length > 0) setSystemState('scanning');
            else setSystemState('idle');
        });
        socketRef.current.on('navigation_status', (status) => {
            setNavStatus(status);
        });

        const captureInterval = setInterval(() => {
            if (sessionStarted && videoRef.current && socketRef.current?.connected) {
                const canvas = document.createElement('canvas');
                canvas.width = 300; canvas.height = 300;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(videoRef.current, 0, 0, 300, 300);
                socketRef.current.emit('process_frame', { image_data: canvas.toDataURL('image/jpeg', 0.5) });
            }
        }, 400);
=======
    const handleTouchStart = () => {
        longPressTimer.current = setTimeout(() => {
            // Trigger ChatBox
            window.dispatchEvent(new CustomEvent('activate-chat'));
            // Provide haptic feedback
            if (navigator.vibrate) navigator.vibrate(50);
        }, 800); // 800ms long press
    };
>>>>>>> bdc5b15c50262411885aea250c797832ada78e59

        return () => { clearInterval(captureInterval); if (socketRef.current) socketRef.current.disconnect(); };
    }, [sessionStarted, speak, playAlertSound]);

    return (
        <div
            ref={containerRef}
            className={`dashboard-container ${!sessionStarted ? 'not-started' : ''}`}
            onClick={handleStartSession}
        >
<<<<<<< HEAD
            <video ref={videoRef} autoPlay playsInline muted className="camera-view" />
=======
            {/* Overlay removed for Demo Mode - handled by LandingPage */
                !hasStarted && (
                    <div style={{ display: 'none' }} onClick={initializeApp}></div>
                )}
            <div className="connection-status" style={{ position: 'absolute', top: '10px', right: '10px', zIndex: 1000, background: isConnected ? 'green' : 'red', padding: '5px', borderRadius: '5px', color: 'white', fontSize: '12px' }}>
                {isConnected ? 'Online' : 'Offline'}
            </div>
            <video ref={videoRef} autoPlay playsInline muted className="hidden-video" />
>>>>>>> bdc5b15c50262411885aea250c797832ada78e59

            <div className={`state-halo ${systemState} ${isListening ? 'listening' : ''}`}></div>

            <div className="vision-hud">
                {!sessionStarted && (
                    <div className="start-overlay premium">
                        <div className="splash-content">
                            <div className="brain-pulse"></div>
                            <h1 className="splash-title">Vision Assistant</h1>
                            <p className="splash-hint">Tap to wake up</p>
                        </div>
                    </div>
                )}

                <div className="system-heartbeat">
                    <div className="heartbeat-inner"></div>
                </div>
                {detections.map((det, i) => (
                    <DetectionRipple key={i} detection={det} index={i} />
                ))}
            </div>

            {navStatus.active ? (
                <div className="navigation-card-premium">
                    <div className="nav-card-inner">
                        <div className="nav-icon">📍</div>
                        <div className="nav-card-text">{navStatus.next_step}</div>
                        <div className="nav-dist-badge">{Math.round(navStatus.distance_to_step)}m</div>
                    </div>
                    <div className="premium-nav-hint">Swipe Up for Next | Down for Repeat</div>
                </div>
            ) : (
                <div className="bottom-sheet premium">
                    <div className="status-label">{sessionStarted ? (isGreeting ? 'Greeting' : 'Always Listening') : 'Ready'}</div>
                    <div className="status-text">{statusText}</div>
                </div>
            )}

            <div className="connection-status-premium">
                <span className={`status-dot ${isConnected ? 'live' : 'off'}`}></span>
                {isConnected ? 'LIVE' : 'OFFLINE'}
            </div>
        </div >
    );
}

export default Dashboard;
