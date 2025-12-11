import React, { useState, useRef, useEffect, useCallback } from 'react';
import io from 'socket.io-client';
import './App.css';

// CRITICAL: Replace this with your BACKEND ngrok URL
const SOCKET_URL = 'https://carmon-uncorroborant-nonmonistically.ngrok-free.dev'; 

function App() {
  const [mode, setMode] = useState('explorer');
  const [isStarted, setIsStarted] = useState(false);
  const [statusText, setStatusText] = useState('Tap to Start');
  
  const [navInstructions, setNavInstructions] = useState([]);
  const [currentNavStep, setCurrentNavStep] = useState(0);
  const [isListening, setIsListening] = useState(false);
  const [obstacleMessage, setObstacleMessage] = useState('');

  const videoRef = useRef(null);
  const socketRef = useRef(null);
  const requestRef = useRef(null);

  const speak = (text, interrupt = false) => {
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.speak(utterance);
  };

  const stopObstacleDetectionLoop = () => {
    if (requestRef.current) { cancelAnimationFrame(requestRef.current); requestRef.current = null; }
  };

  const endNavigation = () => {
    setNavInstructions([]);
    setCurrentNavStep(0);
    stopObstacleDetectionLoop();
    setMode('explorer');
    setStatusText('Navigation ended. Switched to Explorer mode.');
    speak('Navigation ended.');
  };

  const handleNextStep = () => {
    if (currentNavStep < navInstructions.length - 1) {
        const nextStep = currentNavStep + 1;
        setCurrentNavStep(nextStep);
        speak(`Next: ${navInstructions[nextStep]}`);
    } else {
        endNavigation();
        speak("You have arrived at your destination.");
    }
  };

  const parseNavigationCommand = useCallback((command) => {
    const locations = ['entrance', 'engineering block', 'architecture', 'ug block', 'canteen', 'parking', 'aiml block'];
    const fromLocation = locations.find(loc => command.includes(loc));
    const toLocation = locations.find(loc => command.replace(fromLocation, '').includes(loc));
    if (fromLocation && toLocation && socketRef.current) {
      setStatusText(`Finding route...`);
      socketRef.current.emit('get_navigation', { start: fromLocation, end: toLocation });
    } else {
      speak('Could not understand locations. Please try again.');
    }
  }, []);

  const handleVoiceCommand = useCallback(() => {
    if (isListening) return;
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech recognition not supported.');
      return;
    }
    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.lang = 'en-US';
    
    setIsListening(true);
    setStatusText('Listening...');
    try {
      recognition.onresult = (event) => parseNavigationCommand(event.results[0][0].transcript.toLowerCase());
      recognition.onend = () => setIsListening(false);
      recognition.onerror = () => {
        speak('I did not hear that. Please try again.');
        setIsListening(false);
      };
      recognition.start();
    } catch (err) {
      setIsListening(false);
    }
  }, [isListening, parseNavigationCommand]);

  const captureAndSendForObstacles = useCallback(() => {
    if (!videoRef.current || !socketRef.current) return;
    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    canvas.getContext('2d').drawImage(videoRef.current, 0, 0);
    const imageData = canvas.toDataURL('image/jpeg', 0.5);
    socketRef.current.emit('process_frame_for_obstacles', { image_data: imageData });
  }, []);

  const startObstacleDetectionLoop = useCallback(() => {
    requestRef.current = requestAnimationFrame(captureAndSendForObstacles);
  }, [captureAndSendForObstacles]);

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

  const startApplication = async () => {
    if (isStarted) return;
    try {
      const audioContext = new (window.AudioContext || window.webkitAudioContext)();
      if (audioContext.state === 'suspended') await audioContext.resume();
      const silentUtterance = new SpeechSynthesisUtterance(' ');
      silentUtterance.volume = 0;
      window.speechSynthesis.speak(silentUtterance);

      const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: true });
      if (videoRef.current) videoRef.current.srcObject = stream;
      
      setIsStarted(true);
      setStatusText('Ready. Tap to explore or switch to Navigation.');
      speak('Vision Assistant is ready.');
    } catch (err) {
      alert(`Error: Permissions were denied. Please allow camera and microphone access in your browser settings and refresh.`);
    }
  };
  
  const handleScreenTap = () => {
    if (mode === 'explorer') handleExplorerTap();
  };

  useEffect(() => {
    if (!isStarted) return;

    socketRef.current = io(SOCKET_URL, { transports: ['websocket'] });
    socketRef.current.on('connect', () => console.log('✅ Socket connected!'));
    socketRef.current.on('scene_summary', (data) => { setStatusText(data.summary); speak(data.summary); });
    socketRef.current.on('navigation_response', (data) => {
      if (data.instructions) {
        setNavInstructions(data.instructions);
        setCurrentNavStep(0);
        speak(`Route found. First step: ${data.instructions[0]}`);
        startObstacleDetectionLoop(); // Start continuous check
      } else {
        speak("Sorry, a route could not be found.");
      }
    });
    socketRef.current.on('obstacle_alert', (data) => {
        if (data.message !== 'Path is clear.') { setObstacleMessage(data.message); speak(data.message, true); } 
        else { setObstacleMessage(''); }
    });
    socketRef.current.on('request_next_frame', () => { if (mode === 'navigator') startObstacleDetectionLoop(); });
    
    return () => {
      if (socketRef.current) socketRef.current.disconnect();
    };
  }, [isStarted, mode, startObstacleDetectionLoop]);

  return (
    <div className="App" onClick={isStarted ? handleScreenTap : null}>
      <video ref={videoRef} autoPlay playsInline muted className="video-feed" />
      {!isStarted && <div className="start-button" onClick={startApplication}>Tap to Start</div>}
      
      {isStarted && (
        <>
          <div className="mode-switcher">
            <button onClick={() => { setMode('explorer'); stopObstacleDetectionLoop(); }} className={mode === 'explorer' ? 'active' : ''}>Explorer</button>
            <button onClick={() => { setMode('navigation'); setStatusText('Press the mic for a command.'); }} className={mode === 'navigation' ? 'active' : ''}>Navigation</button>
          </div>
          <div className="overlay">
            {mode === 'explorer' && <p className="status-text">{statusText}</p>}
            {mode === 'navigation' && (
              <div className="navigation-ui">
                {navInstructions.length === 0 ? (
                  <>
                    <p className="status-text">{statusText}</p>
                    <button className={`mic-button ${isListening ? 'listening' : ''}`} onClick={handleVoiceCommand} disabled={isListening}>🎤</button>
                  </>
                ) : (
                  <div className="navigation-panel">
                    <p className="nav-instruction-title">CURRENT STEP</p>
                    <p className="nav-instruction-text">{navInstructions[currentNavStep]}</p>
                    <button className="nav-button" onClick={handleNextStep}>Next Step</button>
                    <button className="nav-button" onClick={endNavigation}>End Navigation</button>
                  </div>
                )}
              </div>
            )}
          </div>
          {mode === 'navigation' && obstacleMessage && (
            <div className="obstacle-banner"><p>{obstacleMessage}</p></div>
          )}
        </>
      )}
    </div>
  );
}

export default App;