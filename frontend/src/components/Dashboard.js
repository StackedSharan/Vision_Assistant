import React, { useState, useRef, useEffect, useCallback } from 'react';
import io from 'socket.io-client';
import '../App.css';

const SOCKET_URL = 'http://localhost:5000';

const ObstacleVisualizer = ({ detections }) => {
  return (
    <div className="obstacle-visualizer">
      {detections.map((det, idx) => {
        const xPos = (det.position_x || 0.5) * 100;
        const distance = det.distance || 5;
        const isClose = distance < 2;

        return (
          <div
            key={idx}
            className={`detection-marker ${det.urgency === 'CRITICAL' ? 'critical' : 'warning'}`}
            style={{
              left: `${xPos}%`,
              top: '50%',
              opacity: isClose ? 1 : 0.7,
            }}
          >
            <div className="marker-pulse" />
            <span className="marker-label">{det.name}</span>
          </div>
        );
      })}
    </div>
  );
};

function Dashboard() {
  const [locations, setLocations] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [isNavigating, setIsNavigating] = useState(false);
  const [currentInstruction, setCurrentInstruction] = useState('Waiting for input...');
  const [detections, setDetections] = useState([]);
  const [isListening, setIsListening] = useState(false);
  const [isConnected, setIsConnected] = useState(false);

  const videoRef = useRef(null);
  const socketRef = useRef(null);
  const recognitionRef = useRef(null);

  // Initialize Socket.IO connection
  useEffect(() => {
    socketRef.current = io(SOCKET_URL);

    socketRef.current.on('connect', () => {
      console.log('✅ Connected to server');
      setIsConnected(true);
      speak('Connected to Vision Assistant');
    });

    socketRef.current.on('disconnect', () => {
      console.log('❌ Disconnected');
      setIsConnected(false);
    });

    socketRef.current.on('instruction_update', (data) => {
      setCurrentInstruction(data.instruction);
      speak(data.instruction);
    });

    socketRef.current.on('detections_update', (data) => {
      if (data.detections) {
        setDetections(data.detections);
      }
    });

    return () => {
      socketRef.current?.disconnect();
    };
  }, []);

  // Fetch available locations
  useEffect(() => {
    fetch(`${SOCKET_URL}/api/locations`)
      .then((res) => res.json())
      .then((data) => {
        setLocations(data.locations || []);
      })
      .catch((err) => console.error('Failed to fetch locations:', err));
  }, [isConnected]);

  // Start camera stream
  useEffect(() => {
    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment' },
          audio: false,
        });

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.play();
        }
      } catch (err) {
        console.error('Camera error:', err);
      }
    };

    startCamera();

    return () => {
      if (videoRef.current && videoRef.current.srcObject) {
        videoRef.current.srcObject.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  // Text-to-speech
  const speak = useCallback((text) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
  }, []);

  // Voice recognition
  const startListening = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      alert('Speech recognition not supported');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event) => {
      const transcript = event.results[0][0].transcript.toLowerCase().trim();
      console.log(`🎤 You said: ${transcript}`);

      const mentionedLocation = locations.find((loc) =>
        transcript.includes(loc.toLowerCase())
      );

      if (mentionedLocation) {
        handleStartNavigation(mentionedLocation);
      } else {
        speak('Location not recognized. Please try again.');
        setTimeout(startListening, 1000);
      }
    };

    recognition.onerror = (event) => {
      console.error('Speech error:', event.error);
      setIsListening(false);
    };

    recognition.onend = () => {
      setIsListening(false);
    };

    recognition.start();
    recognitionRef.current = recognition;
  }, [locations]);

  const handleStartNavigation = useCallback(
    (location) => {
      if (!socketRef.current) return;

      setSelectedLocation(location);
      setIsNavigating(true);
      speak(`Starting navigation to ${location}`);

      fetch(`${SOCKET_URL}/api/start-navigation`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ destination: location }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data.success) {
            setCurrentInstruction(data.instruction);
            speak(data.instruction);
          } else {
            speak('Navigation failed: ' + (data.error || 'Unknown error'));
            setIsNavigating(false);
          }
        })
        .catch((err) => {
          console.error('Navigation error:', err);
          setIsNavigating(false);
        });
    },
    []
  );

  const handleNextStep = useCallback(() => {
    if (!socketRef.current) return;

    fetch(`${SOCKET_URL}/api/next-step`)
      .then((res) => res.json())
      .then((data) => {
        setCurrentInstruction(data.instruction);
        speak(data.instruction);
      })
      .catch((err) => console.error('Next step error:', err));
  }, []);

  const handlePrevStep = useCallback(() => {
    if (!socketRef.current) return;

    fetch(`${SOCKET_URL}/api/prev-step`)
      .then((res) => res.json())
      .then((data) => {
        setCurrentInstruction(data.instruction);
        speak(data.instruction);
      })
      .catch((err) => console.error('Prev step error:', err));
  }, []);

  const handleStopNavigation = useCallback(() => {
    if (!socketRef.current) return;

    fetch(`${SOCKET_URL}/api/stop-navigation`, {
      method: 'POST',
    })
      .then((res) => res.json())
      .then((data) => {
        setIsNavigating(false);
        setSelectedLocation(null);
        setCurrentInstruction('Navigation stopped');
        speak('Navigation stopped');
      })
      .catch((err) => console.error('Stop navigation error:', err));
  }, []);

  return (
    <div className="dashboard">
      <video
        ref={videoRef}
        className="camera-feed"
        muted
        playsInline
      />
      <ObstacleVisualizer detections={detections} />

      <div className="instruction-panel">
        <div className="instruction-text">{currentInstruction}</div>

        {!isNavigating ? (
          <div className="location-buttons">
            <button
              className="primary-btn"
              onClick={startListening}
              disabled={isListening}
            >
              {isListening ? '🎤 Listening...' : '🎤 Ask where to go'}
            </button>
          </div>
        ) : (
          <div className="navigation-controls">
            <button className="control-btn" onClick={handlePrevStep} title="Previous step">
              ⬆ Prev
            </button>
            <button className="control-btn" onClick={handleNextStep} title="Next step">
              ⬇ Next
            </button>
            <button className="danger-btn" onClick={handleStopNavigation} title="Stop navigation">
              ⏹ Stop
            </button>
          </div>
        )}
      </div>

      <div className="status-bar">
        <span>{isConnected ? '✅ Connected' : '❌ Offline'}</span>
        {selectedLocation && <span>📍 {selectedLocation}</span>}
      </div>
    </div>
  );
}

export default Dashboard;
