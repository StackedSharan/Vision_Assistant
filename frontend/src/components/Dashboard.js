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
  const [currentInstruction, setCurrentInstruction] = useState('');
  const [detections, setDetections] = useState([]);
  const [isListening, setIsListening] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  
  // Mode selection (initial state)
  const [modeSelected, setModeSelected] = useState(false);
  const [currentMode, setCurrentMode] = useState(null); // 'object' or 'navigation'
  
  // Object detection & selection mode
  const [objectDetectionActive, setObjectDetectionActive] = useState(false);
  const [detectedObjectsList, setDetectedObjectsList] = useState([]);
  const [objectSelectionPending, setObjectSelectionPending] = useState(false);
  
  // Object tracking mode (new primary feature)
  const [trackingMode, setTrackingMode] = useState(false);
  const [trackingState, setTrackingState] = useState(null); // IDLE, SELECTING, TRACKING, PAUSED, COOLDOWN
  const [targetObject, setTargetObject] = useState(null);
  const [trackingInstruction, setTrackingInstruction] = useState('');
  const [lastTrackingUpdate, setLastTrackingUpdate] = useState(0);
  
  // Navigation with obstacle detection
  const [obstacleDetectionActive, setObstacleDetectionActive] = useState(false);
  const [lastAnnouncementTime, setLastAnnouncementTime] = useState(0);
  const [announcementCooldown, setAnnouncementCooldown] = useState(3000);

  const videoRef = useRef(null);
  const socketRef = useRef(null);
  const recognitionRef = useRef(null);
  const initializedRef = useRef(false);

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

  // Play alert sound based on distance and urgency with cooldown
  const playAlertSound = useCallback((detections) => {
    if (!detections.length) return;
    
    const now = Date.now();
    if (now - lastAnnouncementTime < announcementCooldown) {
      return; // Still in cooldown, don't announce
    }

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

    let frequency, duration, volume, cooldownMs;
    
    if (urgency === 'CRITICAL') {
      // Very close, 1 second cooldown
      frequency = 1000;
      duration = 0.15;
      volume = 0.5;
      cooldownMs = 1000;
    } else if (urgency === 'DANGER') {
      // Close, 2 second cooldown
      frequency = 800;
      duration = 0.2;
      volume = 0.4;
      cooldownMs = 2000;
    } else if (urgency === 'WARNING') {
      // Medium, 3 second cooldown
      frequency = 600;
      duration = 0.25;
      volume = 0.3;
      cooldownMs = 3000;
    } else if (urgency === 'CAUTION') {
      // Far, 4 second cooldown
      frequency = 400;
      duration = 0.3;
      volume = 0.2;
      cooldownMs = 4000;
    } else {
      return;
    }

    oscillator.frequency.setValueAtTime(frequency, audioCtx.currentTime);
    gain.gain.setValueAtTime(volume, audioCtx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + duration);

    oscillator.start(audioCtx.currentTime);
    oscillator.stop(audioCtx.currentTime + duration);

    // Update cooldown based on distance
    setAnnouncementCooldown(cooldownMs);
    setLastAnnouncementTime(now);

    // Announce distance
    if (urgency === 'CRITICAL' || urgency === 'DANGER') {
      setTimeout(() => {
        speak(`${mostUrgent.name} at ${distance.toFixed(1)} metres`);
      }, 300);
    }
  }, [lastAnnouncementTime, announcementCooldown, speak]);

  // Provide directional guidance for object tracking
  const provideDirectionalGuidance = useCallback((detection) => {
    if (!detection) return;

    const xPos = detection.position_x || 0.5; // 0=left, 0.5=center, 1=right
    const distance = detection.distance || 5;
    
    // Check if object is in destination range (0.2 metres)
    if (distance < 0.2) {
      speak('Destination achieved! Destination achieved!');
      return;
    }

    // Determine if object is centered (0.35 to 0.65 is center area)
    let direction = '';
    if (xPos < 0.35) {
      direction = 'Move right. Keep moving forward';
    } else if (xPos > 0.65) {
      direction = 'Move left. Keep moving forward';
    } else {
      direction = 'Keep going straight';
    }

    // Announce direction
    const now = Date.now();
    if (now - lastAnnouncementTime > 2000) { // 2 second guidance cooldown
      speak(direction);
      setLastAnnouncementTime(now);
    }
  }, [speak, lastAnnouncementTime]);

  // Handle object tracking updates
  const handleTrackingUpdate = useCallback((detection, status) => {
    if (!detection && status.state === 'tracking') {
      // Object not in current frame
      const elapsed = (Date.now() - lastTrackingUpdate) / 1000;
      if (elapsed < 10) {
        speak(`Searching for ${targetObject}...`);
      } else {
        speak(`No ${targetObject} found`);
        setTrackingState('cooldown');
      }
    } else if (detection) {
      // Object found
      const distance = detection.distance || 5;
      
      // Check if reached destination
      if (distance < 0.2) {
        speak('Destination reached! Object is within your reach');
        return;
      }

      // Generate instruction if time elapsed
      const now = Date.now();
      if (now - lastTrackingUpdate >= 5000) { // 5 second interval
        // Calculate steps (0.7m per step)
        const steps = Math.max(1, Math.round(distance / 0.7));
        let stepInstr = '';
        
        if (distance < 0.5) {
          stepInstr = `Very close! Walk ${steps} small step`;
        } else if (distance < 1.0) {
          stepInstr = `Close! Walk ${steps} steps`;
        } else if (distance < 2.0) {
          stepInstr = `Walk ${steps} steps straight`;
        } else {
          stepInstr = `Walk ${steps} steps forward`;
        }

        // Directional guidance
        const xPos = detection.position_x || 0.5;
        let dirInstr = '';
        if (xPos < 0.35) {
          dirInstr = 'Move left to center the object';
        } else if (xPos > 0.65) {
          dirInstr = 'Move right to center the object';
        } else {
          dirInstr = 'Keep the object centered, move straight';
        }

        const fullInstr = `${stepInstr}. ${dirInstr}`;
        setTrackingInstruction(fullInstr);
        speak(fullInstr);
        setLastTrackingUpdate(now);
      }
    }
  }, [targetObject, lastTrackingUpdate, speak]);

  // Initialize Socket.IO connection
  useEffect(() => {
    socketRef.current = io(SOCKET_URL);

    socketRef.current.on('connect', () => {
      console.log('✅ Connected to server');
      setIsConnected(true);
    });

    socketRef.current.on('disconnect', () => {
      console.log('❌ Disconnected');
      setIsConnected(false);
    });

    return () => {
      socketRef.current?.disconnect();
    };
  }, []);

  // Initialize speech recognition on component mount
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.error('Speech Recognition not supported in this browser');
      return;
    }

    // Create the recognition instance once
    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
      console.log('🎤 Microphone active - listening for commands...');
    };

    recognition.onresult = (event) => {
      // Get the latest result
      const resultIndex = event.results.length - 1;
      const transcript = event.results[resultIndex][0].transcript.toLowerCase().trim();
      console.log(`🎤 You said: "${transcript}" (confidence: ${event.results[resultIndex][0].confidence.toFixed(2)})`);

      // Ignore very short inputs
      if (transcript.length < 2) {
        console.log('Transcript too short, ignoring...');
        return;
      }

      // Use state from ref instead of closure
      const state = stateRef.current;

      // PHASE 1: Mode selection (initial)
      if (!state.modeSelected) {
        if (transcript.includes('locate') || transcript.includes('object')) {
          console.log('✅ Mode selected: Object Detection');
          setModeSelected(true);
          setCurrentMode('object');
          setObjectDetectionActive(true);
          setObjectSelectionPending(true);
          setCurrentInstruction('Scanning nearby objects...');
          speak('Scanning nearby objects. Tell me which one you want to reach.');
        } else if (transcript.includes('navigate') || transcript.includes('college') || transcript.includes('place') || transcript.includes('canteen')) {
          console.log('✅ Mode selected: Navigation');
          setModeSelected(true);
          setCurrentMode('navigation');
          setObstacleDetectionActive(true);
          setCurrentInstruction('Where would you like to go in your college?');
          speak('Where would you like to go in your college? You can say canteen, architecture, engineering, aiml, entrance, or any other location.');
        } else {
          console.log('❌ Unrecognized mode command. Asking again...');
          speak('I did not understand. Please say locate objects or navigate to college.');
        }
      }
      // PHASE 2: Object mode - user selecting which object to go to
      else if (state.objectSelectionPending && state.currentMode === 'object') {
        // User says "take me to [object]"
        if (transcript.includes('take me to') || transcript.includes('go to') || transcript.includes('to ')) {
          const objectName = transcript.replace('take me to', '').replace('go to', '').trim();
          if (objectName.length > 1) {
            console.log(`✅ Tracking object: ${objectName}`);
            setTrackingMode(true);
            setTargetObject(objectName);
            setTrackingState('tracking');
            setObjectSelectionPending(false);
            setCurrentInstruction(`Guiding you to ${objectName}. Follow the instructions.`);
            speak(`Starting to guide you to ${objectName}`);
            setLastTrackingUpdate(Date.now());
          }
        } else {
          console.log('❌ Unrecognized object command');
          speak('Please say take me to followed by object name');
        }
      }
      // PHASE 3: Navigation mode - user selecting college location
      else if (!state.isNavigating && state.currentMode === 'navigation') {
        const mentionedLocation = state.locations.find((loc) =>
          transcript.includes(loc.toLowerCase())
        );

        if (mentionedLocation) {
          console.log(`✅ Navigation to: ${mentionedLocation}`);
          setSelectedLocation(mentionedLocation);
          setIsNavigating(true);
          speak(`Starting navigation to ${mentionedLocation}`);
          setCurrentInstruction(`Starting navigation to ${mentionedLocation}`);

          fetch(`${SOCKET_URL}/api/start-navigation`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ destination: mentionedLocation }),
          })
            .then((res) => res.json())
            .then((data) => {
              if (data.success) {
                setCurrentInstruction(data.instruction);
                speak(data.instruction);
              }
            })
            .catch((err) => console.error('Navigation error:', err));
        } else {
          console.log('❌ Location not recognized:', transcript);
          speak('Location not recognized. Please try again.');
        }
      }
      // PHASE 4: During tracking - pause/resume/stop commands
      else if (state.trackingMode) {
        if (transcript.includes('stop') || transcript.includes('quit') || transcript.includes('exit')) {
          console.log('✅ Tracking stopped');
          setTrackingMode(false);
          setTrackingState(null);
          setTargetObject(null);
          setModeSelected(false);
          setCurrentMode(null);
          setCurrentInstruction('Tracking stopped. Say locate objects or navigate to college.');
          speak('Tracking stopped. Say locate objects or navigate to college.');
        } else if (transcript.includes('pause')) {
          console.log('✅ Tracking paused');
          setTrackingState('paused');
          setCurrentInstruction('Tracking paused. Say resume to continue.');
          speak('Tracking paused');
        } else if (transcript.includes('resume') || transcript.includes('continue')) {
          console.log('✅ Tracking resumed');
          setTrackingState('tracking');
          setCurrentInstruction(`Resuming tracking ${state.targetObject}`);
          speak(`Resuming tracking ${state.targetObject}`);
          setLastTrackingUpdate(Date.now());
        } else {
          console.log('❌ Unrecognized tracking command');
          speak('Say stop, pause, or resume to control tracking');
        }
      }
    };

    recognition.onerror = (event) => {
      console.error('❌ Speech recognition error:', event.error);
      setIsListening(false);
      
      // Auto-restart listening on common errors
      if (event.error === 'no-speech' || event.error === 'audio-capture') {
        console.log('🔄 Auto-restarting listening due to error...');
        setTimeout(() => {
          if (recognitionRef.current) {
            try {
              recognitionRef.current.start();
            } catch (err) {
              console.error('Error restarting recognition:', err);
            }
          }
        }, 500);
      }
    };

    recognition.onend = () => {
      console.log('Speech recognition ended. Auto-restarting...');
      setIsListening(false);
      
      // Auto-restart listening to maintain continuous listening
      try {
        if (recognitionRef.current && stateRef.current.modeSelected) {
          recognitionRef.current.start();
        }
      } catch (err) {
        console.error('Restart error:', err);
      }
    };

    // Store the recognition instance in the ref
    recognitionRef.current = recognition;

    // Cleanup: stop recognition when component unmounts
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (err) {
          console.error('Error stopping recognition:', err);
        }
      }
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
  }, []);

  // Start camera stream
  useEffect(() => {
    const startCamera = async () => {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: 'environment', width: { ideal: 1280 }, height: { ideal: 720 } },
          audio: false,
        });

        if (videoRef.current) {
          videoRef.current.srcObject = stream;
          videoRef.current.onloadedmetadata = () => {
            videoRef.current.play().catch(err => console.error('Play error:', err));
          };
        }
      } catch (err) {
        console.error('Camera error:', err);
        alert('Camera permission denied. Please allow camera access.');
      }
    };

    startCamera();

    return () => {
      if (videoRef.current && videoRef.current.srcObject) {
        videoRef.current.srcObject.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  // Ask for mode on connection
  useEffect(() => {
    if (isConnected && !modeSelected && !currentMode && !initializedRef.current) {
      initializedRef.current = true;
      setTimeout(() => {
        const modeQuestion = 'Welcome to Vision Assistant. Would you like to locate nearby objects in front of you, or would you like to go to a place in your college? Say locate objects or navigate to college.';
        speak(modeQuestion);
        setCurrentInstruction(modeQuestion);
      }, 500);
      
      // Start listening after welcome announcement
      setTimeout(() => {
        if (recognitionRef.current) {
          try {
            console.log('🎤 Starting listening after welcome announcement...');
            recognitionRef.current.start();
          } catch (err) {
            console.error('Error starting recognition:', err);
          }
        }
      }, 2500);
    }
  }, [isConnected, modeSelected, currentMode, speak]);

  // Capture and send frames for object detection
  useEffect(() => {
    if (!isConnected) return;
    // Only capture if in active mode (object detection OR navigation OR tracking)
    if (!objectDetectionActive && !obstacleDetectionActive && !trackingMode) return;

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

        // MODE 1: Object detection (list all visible objects)
        if (objectDetectionActive && !trackingMode && !objectSelectionPending) {
          const response = await fetch(`${SOCKET_URL}/api/detect-all`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData }),
          });

          if (response.ok) {
            const data = await response.json();
            if (data.objects && data.objects.length > 0) {
              setDetectedObjectsList(data.objects);
              setDetections(data.detections || []);
              
              // Announce what we see
              const now = Date.now();
              if (now - lastAnnouncementTime > 3000) {
                const objectsList = data.objects.slice(0, 3).join(', ');
                const announcement = `I see ${objectsList} in front of you`;
                speak(announcement);
                setCurrentInstruction(`I see: ${data.objects.slice(0, 5).join(', ')}`);
                setObjectSelectionPending(true);
                setLastAnnouncementTime(now);
              }
            }
          }
        }
        // MODE 2: Object tracking (guide to selected object)
        else if (trackingMode && targetObject && trackingState === 'tracking') {
          const response = await fetch(`${SOCKET_URL}/api/track-update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData }),
          });

          if (response.ok) {
            const data = await response.json();
            if (data.detection) {
              handleTrackingUpdate(data.detection, data.status);
            } else if (data.announcement) {
              speak(data.announcement);
            }
          }
        }
        // MODE 3: Navigation with obstacle detection
        else if (obstacleDetectionActive && isNavigating) {
          const response = await fetch(`${SOCKET_URL}/api/detect-obstacles`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData }),
          });

          if (response.ok) {
            const data = await response.json();
            if (data.detections && Array.isArray(data.detections)) {
              setDetections(data.detections);

              // Play alerts for obstacles during navigation
              const alertDetections = data.detections.filter(
                (d) => ['CRITICAL', 'DANGER', 'WARNING', 'CAUTION'].includes(d.urgency)
              );
              
              if (alertDetections.length > 0) {
                playAlertSound(alertDetections);
              }
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
  }, [isConnected, objectDetectionActive, obstacleDetectionActive, trackingMode, trackingState, targetObject, objectSelectionPending, isNavigating, lastAnnouncementTime, playAlertSound, handleTrackingUpdate, speak]);

  // Refs to access current state in speech recognition handlers without dependencies
  const stateRef = useRef({
    modeSelected: false,
    currentMode: null,
    objectSelectionPending: false,
    trackingMode: false,
    isNavigating: false,
    locations: [],
    targetObject: null,
  });

  // Keep state ref in sync
  useEffect(() => {
    stateRef.current = {
      modeSelected,
      currentMode,
      objectSelectionPending,
      trackingMode,
      isNavigating,
      locations,
      targetObject,
    };
  }, [modeSelected, currentMode, objectSelectionPending, trackingMode, isNavigating, locations, targetObject]);

  // Voice recognition - simple callback to start listening
  const startListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        console.log('🎤 Starting speech recognition...');
        recognitionRef.current.start();
      } catch (err) {
        // Recognition may already be running, ignore error
        console.error('Error starting recognition:', err);
      }
    } else {
      console.error('Speech recognition not initialized');
    }
  }, []);

  // Handle mode selection - Object location
  const handleSelectObjectMode = useCallback(() => {
    setModeSelected(true);
    setCurrentMode('object');
    setObjectDetectionActive(true);
    setCurrentInstruction('Scanning nearby objects...');
    speak('Scanning nearby objects. Tell me which one you want to reach.');
    // Start listening immediately for object selection
    if (recognitionRef.current) {
      try {
        recognitionRef.current.start();
      } catch (err) {
        console.error('Error starting recognition:', err);
      }
    }
  }, [speak]);

  // Handle mode selection - College navigation
  const handleSelectNavigationMode = useCallback(() => {
    setModeSelected(true);
    setCurrentMode('navigation');
    setObstacleDetectionActive(true);
    setCurrentInstruction('Where would you like to go in your college?');
    speak('Where would you like to go in your college? You can say canteen, architecture, engineering, aiml, entrance, or any other location.');
    // Start listening immediately for location selection
    if (recognitionRef.current) {
      try {
        recognitionRef.current.start();
      } catch (err) {
        console.error('Error starting recognition:', err);
      }
    }
  }, [speak]);

  // Stop tracking and return to mode selection
  const stopTracking = useCallback(() => {
    setTrackingMode(false);
    setTargetObject(null);
    setTrackingState(null);
    setModeSelected(false);
    setCurrentMode(null);
    setObjectDetectionActive(false);
    setObstacleDetectionActive(false);
    setCurrentInstruction('');
    speak('Tracking stopped. Starting over.');
    setTimeout(() => {
      const modeQuestion = 'Would you like to locate nearby objects or navigate to a place in your college?';
      speak(modeQuestion);
      setCurrentInstruction(modeQuestion);
    }, 1000);
  }, [speak]);

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
    [speak]
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
  }, [speak]);

  const handlePrevStep = useCallback(() => {
    if (!socketRef.current) return;

    fetch(`${SOCKET_URL}/api/prev-step`)
      .then((res) => res.json())
      .then((data) => {
        setCurrentInstruction(data.instruction);
        speak(data.instruction);
      })
      .catch((err) => console.error('Prev step error:', err));
  }, [speak]);

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
  }, [speak]);

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

        {!modeSelected ? (
          <div className="mode-selection">
            <p style={{fontSize: '0.9rem', marginBottom: '15px', color: '#00c6ff'}}>
              Listening for your choice...
            </p>
            <button
              className="primary-btn"
              onClick={handleSelectObjectMode}
              disabled={isListening}
            >
              {isListening ? '🎤 Listening...' : '🎯 Locate Nearby Objects'}
            </button>
            <button
              className="primary-btn nav-btn"
              onClick={handleSelectNavigationMode}
              disabled={isListening}
            >
              {isListening ? '🎤 Listening...' : '📍 Navigate to College'}
            </button>
          </div>
        ) : currentMode === 'object' && !trackingMode ? (
          <div className="object-list-panel">
            <p style={{color: '#00ff88', marginBottom: '10px'}}>Detected Objects:</p>
            <div className="objects-display">
              {detectedObjectsList.map((obj, idx) => (
                <div key={idx} className="object-chip">
                  {obj}
                </div>
              ))}
            </div>
            <p style={{fontSize: '0.85rem', color: '#ffaa00', marginTop: '15px'}}>
              Say "take me to" followed by an object name
            </p>
          </div>
        ) : trackingMode ? (
          <div className="tracking-controls">
            <div className="tracking-status">
              {trackingState === 'paused' ? (
                <span style={{color: '#ff9800'}}>⏸ Tracking Paused - Say "resume" to continue</span>
              ) : (
                <span style={{color: '#00ff88'}}>🎯 Guiding to: <strong>{targetObject}</strong></span>
              )}
            </div>
            <div className="tracking-instruction">{trackingInstruction}</div>
            <button 
              className="danger-btn" 
              onClick={stopTracking}
              title="Stop tracking and return to menu"
            >
              ⏹ Stop
            </button>
          </div>
        ) : isNavigating ? (
          <div className="navigation-controls">
            <button className="control-btn" onClick={handlePrevStep} title="Previous step">
              ⬆ Prev
            </button>
            <button className="control-btn" onClick={handleNextStep} title="Next step">
              ⬇ Next
            </button>
            <button className="danger-btn" onClick={handleStopNavigation} title="Stop navigation">
              ⏹ Stop Navigation
            </button>
          </div>
        ) : null}
      </div>

      <div className="status-bar">
        <span>{isConnected ? '✅ Connected' : '❌ Offline'}</span>
        {selectedLocation && <span>📍 {selectedLocation}</span>}
      </div>
    </div>
  );
}

export default Dashboard;
