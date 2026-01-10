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
        
        // Color based on urgency level
        let colorClass = 'safe';
        let urgencyLabel = 'Safe';
        if (det.urgency === 'CRITICAL') {
          colorClass = 'critical';
          urgencyLabel = '⚠️ CRITICAL';
        } else if (det.urgency === 'DANGER') {
          colorClass = 'danger';
          urgencyLabel = '🚨 DANGER';
        } else if (det.urgency === 'WARNING') {
          colorClass = 'warning';
          urgencyLabel = '⚠️ WARNING';
        } else if (det.urgency === 'CAUTION') {
          colorClass = 'caution';
          urgencyLabel = '⚠ CAUTION';
        }

        return (
          <div
            key={idx}
            className={`detection-marker ${colorClass}`}
            style={{
              left: `${xPos}%`,
              top: '50%',
              opacity: det.urgency !== 'SAFE' ? 1 : 0.5,
            }}
          >
            <div className="marker-pulse" />
            <div className="marker-content">
              <span className="marker-label">{det.name}</span>
              {distance !== null && (
                <span className="marker-distance">{distance.toFixed(1)}m</span>
              )}
              <span className="marker-urgency">{urgencyLabel}</span>
            </div>
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

  // Define callbacks BEFORE effects that use them
  
  // Text-to-speech
  const speak = useCallback((text) => {
    if (!window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;
    window.speechSynthesis.speak(utterance);
  }, []);

  // Play alert sound based on distance and urgency
  const playAlertSound = useCallback((detections) => {
    if (!detections.length) return;
    if (!window.AudioContext && !window.webkitAudioContext) return;

    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    
    // Find most urgent detection
    const urgencyOrder = { 'CRITICAL': 0, 'DANGER': 1, 'WARNING': 2, 'CAUTION': 3 };
    const mostUrgent = detections.reduce((prev, curr) => {
      const prevScore = urgencyOrder[prev.urgency] || 999;
      const currScore = urgencyOrder[curr.urgency] || 999;
      return currScore < prevScore ? curr : prev;
    });

    const distance = mostUrgent.distance || 5;
    const urgency = mostUrgent.urgency;

    const oscillator = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    oscillator.connect(gain);
    gain.connect(audioCtx.destination);

    let frequency, duration, volume;
    
    if (urgency === 'CRITICAL') {
      // Very fast urgent beeping
      frequency = 1000;
      duration = 0.15;
      volume = 0.5;
    } else if (urgency === 'DANGER') {
      frequency = 800;
      duration = 0.2;
      volume = 0.4;
    } else if (urgency === 'WARNING') {
      frequency = 600;
      duration = 0.25;
      volume = 0.3;
    } else if (urgency === 'CAUTION') {
      frequency = 400;
      duration = 0.3;
      volume = 0.2;
    } else {
      return;
    }

    oscillator.frequency.setValueAtTime(frequency, audioCtx.currentTime);
    gain.gain.setValueAtTime(volume, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + duration);

    oscillator.start(audioCtx.currentTime);
    oscillator.stop(audioCtx.currentTime + duration);

    // Announce distance if critical
    if (urgency === 'CRITICAL' || urgency === 'DANGER') {
      setTimeout(() => {
        speak(`${mostUrgent.name} at ${distance.toFixed(1)} meters`);
      }, 300);
    }
  }, [speak]);

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

  // Capture and send frames for object detection
  useEffect(() => {
    if (!isConnected) return;

    const captureAndDetect = async () => {
      try {
        if (!videoRef.current || videoRef.current.readyState !== videoRef.current.HAVE_ENOUGH_DATA) {
          return;
        }

        // Create canvas and draw current frame
        const canvas = document.createElement('canvas');
        canvas.width = videoRef.current.videoWidth;
        canvas.height = videoRef.current.videoHeight;
        const ctx = canvas.getContext('2d');
        ctx.drawImage(videoRef.current, 0, 0);

        // Convert to base64 and send
        const imageData = canvas.toDataURL('image/jpeg', 0.7);

        const response = await fetch(`${SOCKET_URL}/api/detect-obstacles`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image: imageData }),
        });

        if (response.ok) {
          const data = await response.json();
          if (data.detections && Array.isArray(data.detections)) {
            setDetections(data.detections);

            // Play alert only for CRITICAL, DANGER, WARNING, CAUTION items
            const alertDetections = data.detections.filter(
              (d) => ['CRITICAL', 'DANGER', 'WARNING', 'CAUTION'].includes(d.urgency)
            );
            
            if (alertDetections.length > 0) {
              playAlertSound(alertDetections);
            }
          }
        }
      } catch (err) {
        console.error('Detection error:', err);
      }
    };

    // Capture frames every 500ms (2 FPS for detection)
    const interval = setInterval(captureAndDetect, 500);
    return () => clearInterval(interval);
  }, [isConnected, playAlertSound]);

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
