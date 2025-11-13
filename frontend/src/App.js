import React, { useState, useRef, useEffect, useCallback } from 'react';
import io from 'socket.io-client';
import './App.css';

// IMPORTANT: Replace this with your BACKEND ngrok URL (from port 5000)
const SOCKET_URL = 'https://carmon-uncorroborant-nonmonistically.ngrok-free.dev'; 

function App() {
  const [mode, setMode] = useState('explorer');
  const [statusText, setStatusText] = useState('Tap to Start');
  const [isStarted, setIsStarted] = useState(false);
  
  const [navInstructions, setNavInstructions] = useState([]);
  const [currentNavStep, setCurrentNavStep] = useState(0);
  const [isListening, setIsListening] = useState(false);
  const [obstacleMessage, setObstacleMessage] = useState('');

  const videoRef = useRef(null);
  const socketRef = useRef(null);
  const requestRef = useRef(null);

  const speak = (text, interrupt = false) => {
    if (interrupt) window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.speak(utterance);
  };

  const parseNavigationCommand = useCallback((command) => {
    const locations = ['entrance', 'engineering block', 'architecture', 'ug block', 'canteen', 'parking', 'aiml block'];
    const fromLocation = locations.find(loc => command.includes(loc));
    const toLocation = locations.find(loc => command.replace(fromLocation, '').includes(loc));
    if (fromLocation && toLocation && socketRef.current) {
      socketRef.current.emit('get_navigation', { start: fromLocation, end: toLocation });
    } else {
      const defaultMessage = 'Could not understand locations. Please say "Go from [place] to [place]".';
      setStatusText(defaultMessage);
      speak(defaultMessage);
    }
  }, []);

  const handleVoiceCommand = useCallback(() => {
    if (isListening) return;

    // Create a brand new, fresh recognition engine for every single attempt.
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.lang = 'en-US';
    
    setIsListening(true);
    setStatusText('Listening...');
    try {
      recognition.onstart = () => console.log("--- 2. Speech recognition STARTED successfully. ---");
      recognition.onresult = (event) => {
        console.log("--- 4. Speech recognition got a result! ---");
        const command = event.results[0][0].transcript.toLowerCase();
        setStatusText(`Heard: "${command}". Finding route...`);
        parseNavigationCommand(command);
      };
      recognition.onend = () => {
        console.log("--- 5. Speech recognition ENDED. ---");
        setIsListening(false);
      };
      recognition.onerror = (event) => {
        console.error("--- 🚨 SPEECH RECOGNITION ERROR ---", event.error);
        if (event.error === 'no-speech') {
          const message = "I didn't hear you. Please tap the mic and speak immediately.";
          setStatusText(message);
          speak(message);
        } else {
          setStatusText(`Error listening: ${event.error}`);
        }
        setIsListening(false);
      };
      recognition.start();
    } catch (err) {
      console.error("--- 🚨 CRITICAL ERROR trying to start recognition ---", err);
      setStatusText(`Error: ${err.message}`);
      setIsListening(false);
    }
  }, [isListening, parseNavigationCommand]);

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
    socketRef.current = io(SOCKET_URL, { transports: ['websocket'] });
    socketRef.current.on('connect', () => console.log('✅ Socket connected!'));
    socketRef.current.on('scene_summary', (data) => { setStatusText(data.summary); speak(data.summary); });
    socketRef.current.on('navigation_response', (data) => {
      if (data.error) { speak(data.error); setStatusText(data.error); } 
      else {
        setNavInstructions(data.instructions);
        setCurrentNavStep(0);
        speak(`Route found. First step: ${data.instructions[0]}`);
        startObstacleDetectionLoop();
      }
    });
    socketRef.current.on('obstacle_alert', (data) => {
      if (data.message !== 'Path is clear.') { setObstacleMessage(data.message); speak(data.message, true); } 
      else { setObstacleMessage(''); }
    });
    socketRef.current.on('request_next_frame', () => { if (mode === 'navigation') startObstacleDetectionLoop(); });
    return () => {
      if (socketRef.current) socketRef.current.disconnect();
      if (requestRef.current) cancelAnimationFrame(requestRef.current);
    };
  }, [mode, startObstacleDetectionLoop]);

  const startApplication = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: true });
      if (videoRef.current) videoRef.current.srcObject = stream;
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      const oscillator = audioContext.createOscillator();
      oscillator.frequency.value = 0;
      oscillator.connect(audioContext.destination);
      oscillator.start(0);
      oscillator.stop(0.1);
      setIsStarted(true);
      setStatusText('Ready. Tap to explore or switch to Navigation.');
      speak('Vision Assistant is ready.');
    } catch (err) {
      console.error("🚨 PERMISSION ERROR:", err);
      setStatusText(`Error: Could not access camera or microphone. Error: ${err.message}`);
    }
  };

  const handleExplorerTap = () => {
    if(!socketRef.current) return;
    setStatusText('Analyzing...');
    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    canvas.getContext('2d').drawImage(videoRef.current, 0, 0);
    const imageData = canvas.toDataURL('image/jpeg');
    socketRef.current.emit('describe_scene', { image: imageData });
  };

  const stopObstacleDetectionLoop = () => {
    if (requestRef.current) { cancelAnimationFrame(requestRef.current); requestRef.current = null; }
  };

  const handleNextStep = () => {
    if (currentNavStep < navInstructions.length - 1) {
        const nextStep = currentNavStep + 1;
        setCurrentNavStep(nextStep);
        speak(`Next: ${navInstructions[nextStep]}`);
    } else {
        speak("You have arrived at your destination.");
        endNavigation();
    }
  };

  const endNavigation = () => {
    setNavInstructions([]);
    setCurrentNavStep(0);
    stopObstacleDetectionLoop();
    setMode('explorer');
    setStatusText('Navigation ended. Switched to Explorer mode.');
  };

  const handleScreenTap = () => {
    if (!isStarted) {
      startApplication();
      return;
    }
    if (mode === 'explorer') {
      handleExplorerTap();
    }
  };

  return (
    <div className="App" onClick={mode === 'explorer' ? handleScreenTap : null}>
      <video ref={videoRef} autoPlay playsInline muted className="video-feed" />
      {isStarted && (
        <div className="mode-switcher">
          <button onClick={() => { setMode('explorer'); stopObstacleDetectionLoop(); }} className={mode === 'explorer' ? 'active' : ''}>Explorer</button>
          <button onClick={() => { setMode('navigation'); setStatusText('Press the mic to give a command.'); }} className={mode === 'navigation' ? 'active' : ''}>Navigation</button>
        </div>
      )}
      <div className="overlay">
        {mode === 'explorer' && <p className="status-text">{statusText}</p>}
        {mode === 'navigation' && (
          <div className="navigation-ui">
            {navInstructions.length === 0 ? (
              <>
                <p className="status-text">{statusText}</p>
                <button 
                  className={`mic-button ${isListening ? 'listening' : ''}`} 
                  onClick={handleVoiceCommand}
                  disabled={isListening} 
                >
                  🎤
                </button>
              </>
            ) : (
              <div className="navigation-panel">
                <p className="nav-instruction-title">CURRENT STEP:</p>
                <p className="nav-instruction-text">{navInstructions[currentNavStep]}</p>
                <button className="nav-button" onClick={handleNextStep}>Next Step</button>
                <button className="nav-button" onClick={endNavigation}>End Navigation</button>
              </div>
            )}
          </div>
        )}
      </div>
      {mode === 'navigation' && obstacleMessage && (
        <div className="obstacle-banner">
          <p>{obstacleMessage}</p>
        </div>
      )}
      {!isStarted && <div className="start-button">Tap to Start</div>}
    </div>
  );
}

export default App;