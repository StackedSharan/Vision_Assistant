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
    const [statusText, setStatusText] = useState('Initializing...');
    const [detections, setDetections] = useState([]);
    const [isListening, setIsListening] = useState(false);
    const [isConnected, setIsConnected] = useState(false);
    const [systemState, setSystemState] = useState('idle');
    const [navStatus, setNavStatus] = useState({ active: false, next_step: '', distance_to_step: 0 });
    const [sessionStarted, setSessionStarted] = useState(false);
    const [isGreeting, setIsGreeting] = useState(false);

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

    const handleNextStep = useCallback(() => {
        if (socketRef.current) socketRef.current.emit('voice_command', { text: 'next step' });
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
        const container = containerRef.current;
        if (!container) return;

        container.addEventListener('touchstart', onTouchStart, { passive: true });
        container.addEventListener('touchmove', onTouchMove, { passive: false });
        container.addEventListener('touchend', onTouchEnd, { passive: false });

        return () => {
            container.removeEventListener('touchstart', onTouchStart);
            container.removeEventListener('touchmove', onTouchMove);
            container.removeEventListener('touchend', onTouchEnd);
        };
    }, [onTouchStart, onTouchMove, onTouchEnd]);

    // Continuous Voice Automation
    const startVoiceAutomation = useCallback(() => {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        if (!SpeechRecognition) return;

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

        return () => { clearInterval(captureInterval); if (socketRef.current) socketRef.current.disconnect(); };
    }, [sessionStarted, speak, playAlertSound]);

    return (
        <div
            ref={containerRef}
            className={`dashboard-container ${!sessionStarted ? 'not-started' : ''}`}
            onClick={handleStartSession}
        >
            <video ref={videoRef} autoPlay playsInline muted className="camera-view" />

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
        </div>
    );
}

export default Dashboard;
