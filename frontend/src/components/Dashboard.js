import React, { useState, useRef, useEffect, useCallback } from 'react';
import io from 'socket.io-client';
import '../App.css';

const SOCKET_URL = 'http://localhost:5000';

// Navigation Instruction Popup Component
const NavigationPopup = ({ instruction, onNext, onPrev, isShowing }) => {
  const touchStartRef = useRef(0);
  const mouseDownRef = useRef(false);

  // Handle touch events (mobile/tablet)
  const handleTouchStart = (e) => {
    touchStartRef.current = e.touches[0].clientY;
    console.log('📍 Touch started at Y:', touchStartRef.current);
  };

  const handleTouchEnd = (e) => {
    const swipeEnd = e.changedTouches[0].clientY;
    const swipeDiff = touchStartRef.current - swipeEnd;
    
    console.log(`📊 Touch swipe - Start: ${touchStartRef.current}, End: ${swipeEnd}, Diff: ${swipeDiff}`);

    if (Math.abs(swipeDiff) > 50) {
      if (swipeDiff > 0) {
        // Swiped up (upward movement) - next instruction
        console.log('✅ ⬆ TOUCH SWIPED UP - NEXT INSTRUCTION');
        onNext();
      } else {
        // Swiped down (downward movement) - previous instruction
        console.log('✅ ⬇ TOUCH SWIPED DOWN - PREVIOUS INSTRUCTION');
        onPrev();
      }
    } else {
      console.log('⚠️ Touch swipe too small, ignoring (', Math.abs(swipeDiff), '< 50)');
    }
  };

  // Handle mouse events (desktop/trackpad)
  const handleMouseDown = (e) => {
    mouseDownRef.current = true;
    touchStartRef.current = e.clientY;
    console.log('🖱️ Mouse drag started at Y:', touchStartRef.current);
  };

  const handleMouseMove = (e) => {
    // Only process if mouse is down
    if (!mouseDownRef.current) return;
  };

  const handleMouseUp = (e) => {
    if (!mouseDownRef.current) return;
    mouseDownRef.current = false;

    const swipeEnd = e.clientY;
    const swipeDiff = touchStartRef.current - swipeEnd;
    
    console.log(`📊 Mouse drag - Start: ${touchStartRef.current}, End: ${swipeEnd}, Diff: ${swipeDiff}`);

    if (Math.abs(swipeDiff) > 50) {
      if (swipeDiff > 0) {
        // Dragged up (upward movement) - next instruction
        console.log('✅ ⬆ MOUSE DRAGGED UP - NEXT INSTRUCTION');
        onNext();
      } else {
        // Dragged down (downward movement) - previous instruction
        console.log('✅ ⬇ MOUSE DRAGGED DOWN - PREVIOUS INSTRUCTION');
        onPrev();
      }
    } else {
      console.log('⚠️ Mouse drag too small, ignoring (', Math.abs(swipeDiff), '< 50)');
    }
  };

  if (!isShowing) return null;

  return (
    <div 
      className="navigation-popup"
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onClick={(e) => e.stopPropagation()}
      style={{touchAction: 'none', userSelect: 'none', cursor: 'grab'}}
    >
      <div className="popup-content">
        <div className="popup-header">Navigation Instructions</div>
        <div className="popup-instruction-text">
          {instruction}
        </div>
        <div className="popup-gestures">
          <div className="gesture-hint up-hint">⬆ SWIPE/DRAG UP for Next</div>
          <div className="gesture-hint down-hint">⬇ SWIPE/DRAG DOWN for Previous</div>
        </div>
      </div>
    </div>
  );
};

function Dashboard() {
  const [locations, setLocations] = useState([]);
  const [selectedLocation, setSelectedLocation] = useState(null);
  const [isNavigating, setIsNavigating] = useState(false);
  const [currentInstruction, setCurrentInstruction] = useState('');
  const [isListening, setIsListening] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [showPopup, setShowPopup] = useState(false);
  const [navigationStarted, setNavigationStarted] = useState(false);
  const [estimatedTime, setEstimatedTime] = useState(0);
  const [obstacleDetectionActive, setObstacleDetectionActive] = useState(false);
  const [lastAlertTime, setLastAlertTime] = useState(0);
  const [lastAlertedObject, setLastAlertedObject] = useState('');
  const [isFirstInstructionSpeaking, setIsFirstInstructionSpeaking] = useState(false);
  const pendingDistantAlertRef = useRef(null);
  const [isSpeaking, setIsSpeaking] = useState(false);
  // NEW: Alert level for visual feedback
  const [alertLevel, setAlertLevel] = useState(null); // 'CRITICAL' | 'DANGER' | 'WARNING' | null
  const alertVisualTimeoutRef = useRef(null);
  // NEW: Flag to prevent detection blocking during instruction playback
  const isDetectingRef = useRef(false);

  const videoRef = useRef(null);
  const socketRef = useRef(null);
  const recognitionRef = useRef(null);
  const initializedRef = useRef(false);
  const isPlayingAlertRef = useRef(false);
  const pausedInstructionRef = useRef(null); // Track paused instruction for resume

  // Enhanced text-to-speech with queue management
  const speak = useCallback((text, isAlert = false, onSpeakComplete = null) => {
    if (!window.speechSynthesis) return;

    // For alerts, we need to pause any ongoing instruction
    if (isAlert) {
      isPlayingAlertRef.current = true;
      // Save any current instruction to resume later
      if (currentInstruction && !currentInstruction.includes('Navigation to')) {
        pausedInstructionRef.current = currentInstruction;
      }
    }

    // Pause speech recognition during announcement
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
        console.log('🔇 Pausing recognition during announcement');
      } catch (err) {
        console.error('Error pausing recognition:', err);
      }
    }

    const utterance = new SpeechSynthesisUtterance(text);
    utterance.rate = 1.0;
    utterance.pitch = 1.0;

    utterance.onstart = () => {
      setIsSpeaking(true);
      console.log('🔊 Speech started:', text.substring(0, 50) + '...');
    };

    utterance.onend = () => {
      setIsSpeaking(false);
      console.log('✅ Speech ended');
      
      if (isAlert) {
        isPlayingAlertRef.current = false;
        console.log('🔔 Alert finished - checking for paused instruction');
        
        // Resume the paused instruction if available
        if (pausedInstructionRef.current && isNavigating) {
          setTimeout(() => {
            const instructionToResume = pausedInstructionRef.current;
            pausedInstructionRef.current = null;
            console.log('▶️ Resuming instruction:', instructionToResume.substring(0, 50));
            // Use regular speak without alert flag since instruction isn't an alert
            speak(instructionToResume, false);
          }, 500);
        }
      }
      
      // Resume recognition after announcement
      setTimeout(() => {
        if (recognitionRef.current && (isNavigating || !navigationStarted)) {
          try {
            recognitionRef.current.start();
            console.log('🎤 Resuming recognition after announcement');
          } catch (err) {
            console.error('Error resuming recognition:', err);
          }
        }
      }, 500);
      
      if (onSpeakComplete) {
        onSpeakComplete();
      }
    };

    utterance.onerror = (event) => {
      console.error('🔴 Speech synthesis error:', event.error);
      setIsSpeaking(false);
      
      if (isAlert) {
        isPlayingAlertRef.current = false;
        console.log('🔔 Alert error - resuming instruction');
        
        // Resume the paused instruction if available (even on error)
        if (pausedInstructionRef.current && isNavigating) {
          setTimeout(() => {
            const instructionToResume = pausedInstructionRef.current;
            pausedInstructionRef.current = null;
            speak(instructionToResume, false);
          }, 500);
        }
      }
      
      // Try to resume recognition even on error
      setTimeout(() => {
        if (recognitionRef.current && (isNavigating || !navigationStarted)) {
          try {
            recognitionRef.current.start();
          } catch (err) {
            console.error('Error resuming recognition after error:', err);
          }
        }
      }, 500);
    };

    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }, [isNavigating, navigationStarted, currentInstruction]);

  // Text-to-speech with pause awareness
  const speakInstruction = useCallback((text) => {
    // Don't interrupt if alert is playing
    if (isPlayingAlertRef.current) {
      console.log('⚠️ Alert is playing, queueing instruction');
      return;
    }
    
    // Pause recognition during instruction
    if (recognitionRef.current) {
      try {
        recognitionRef.current.abort();
        console.log('🔇 Pausing speech recognition during instruction');
      } catch (err) {
        console.error('Error pausing recognition:', err);
      }
    }
    
    // Note: currentInstruction should already be set by the caller
    // to keep screen and audio in sync
    console.log('🗣️ Speaking instruction:', text.substring(0, 50));
    
    speak(text, false, () => {
      // After instruction finishes, check if this was first instruction
      setIsFirstInstructionSpeaking(false);
      
      // Check if there's a pending distant alert to announce
      if (pendingDistantAlertRef.current && isNavigating && !isPlayingAlertRef.current) {
        console.log('📢 Announcing pending obstacle after instruction');
        const obstacleToAnnounce = pendingDistantAlertRef.current;
        pendingDistantAlertRef.current = null;
        
        // IMPORTANT: Announce obstacle WITHOUT alert flag (isAlert=false)
        // This prevents it from interfering with instruction state
        setTimeout(() => {
          speak(obstacleToAnnounce, false);
        }, 500);
      }
      
      // Resume recognition after instruction
      setTimeout(() => {
        if (recognitionRef.current && isNavigating) {
          try {
            recognitionRef.current.start();
            console.log('🎤 Resuming speech recognition after instruction');
          } catch (err) {
            console.error('Error resuming recognition:', err);
          }
        }
      }, 500);
    });
  }, [isNavigating, speak]);

  // Initialize Socket.IO connection
  useEffect(() => {
    socketRef.current = io(SOCKET_URL);

    socketRef.current.on('connect', () => {
      console.log('✅ Connected to server');
      setIsConnected(true);
      
      // Check backend health
      fetch(`${SOCKET_URL}/api/health`)
        .then(res => res.json())
        .then(data => console.log('🏥 Backend health:', data))
        .catch(err => console.error('🏥 Backend health check failed:', err));
    });

    socketRef.current.on('disconnect', () => {
      console.log('❌ Disconnected');
      setIsConnected(false);
    });

    return () => {
      socketRef.current?.disconnect();
    };
  }, []);

  // Initialize speech recognition
  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.error('Speech Recognition not supported');
      return;
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event) => {
      const resultIndex = event.results.length - 1;
      const transcript = event.results[resultIndex][0].transcript.toLowerCase().trim();
      console.log(`🎤 You said: "${transcript}"`);

      if (transcript.length < 2) return;

      // If waiting for destination
      if (!navigationStarted) {
        const mentionedLocation = locations.find((loc) =>
          transcript.includes(loc.toLowerCase())
        );

        if (mentionedLocation) {
          console.log(`✅ Navigation to: ${mentionedLocation}`);
          handleStartNavigation(mentionedLocation);
        } else {
          console.log('❌ Location not recognized');
          speak('Location not recognized. Please try again.');
        }
      } else if (isNavigating) {
        // Handle next/previous commands during navigation
        if (transcript.includes('next')) {
          console.log('📢 Voice command: Next');
          handleNextStep();
        } else if (transcript.includes('previous') || transcript.includes('back')) {
          console.log('📢 Voice command: Previous');
          handlePrevStep();
        }
      }
    };

    recognition.onerror = (event) => {
      console.error('Speech recognition error:', event.error);
      setIsListening(false);
      
      if (event.error === 'no-speech' || event.error === 'audio-capture') {
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
      setIsListening(false);
      // Auto-restart if waiting for destination or navigating
      try {
        if (recognitionRef.current && !navigationStarted) {
          recognitionRef.current.start();
        } else if (recognitionRef.current && isNavigating) {
          recognitionRef.current.start();
        }
      } catch (err) {
        console.error('Restart error:', err);
      }
    };

    recognitionRef.current = recognition;

    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (err) {
          console.error('Error stopping recognition:', err);
        }
      }
    };
  }, [locations, navigationStarted, isNavigating, speak]);

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
            console.log('📹 Camera metadata loaded:', videoRef.current.videoWidth, 'x', videoRef.current.videoHeight);
            videoRef.current.play().catch(err => console.error('❌ Play error:', err));
          };
          videoRef.current.onplay = () => {
            console.log('🎥 Camera stream started playing');
          };
        }
      } catch (err) {
        console.error('❌ Camera error:', err);
        alert('Camera permission denied. Please allow camera access.');
      }
    };

    startCamera();

    return () => {
      if (videoRef.current && videoRef.current.srcObject) {
        console.log('📹 Stopping camera stream');
        videoRef.current.srcObject.getTracks().forEach((track) => track.stop());
      }
    };
  }, []);

  // Ask for destination on connection
  useEffect(() => {
    if (isConnected && !navigationStarted && !initializedRef.current) {
      initializedRef.current = true;
      setTimeout(() => {
        const question = 'Welcome to College Navigation. Where would you like to go in your college? You can say canteen, engineering, architecture, or any other location.';
        speak(question);
        setCurrentInstruction(question);
      }, 500);

      setTimeout(() => {
        if (recognitionRef.current) {
          try {
            console.log('🎤 Starting listening...');
            recognitionRef.current.start();
          } catch (err) {
            console.error('Error starting recognition:', err);
          }
        }
      }, 2500);
    }
  }, [isConnected, navigationStarted, speak]);

  // Obstacle detection during navigation
  useEffect(() => {
    if (!isNavigating || !obstacleDetectionActive || !videoRef.current) {
      console.log('🛑 Obstacle detection paused:', { isNavigating, obstacleDetectionActive, hasVideo: !!videoRef.current });
      return;
    }
    
    // Don't detect during first instruction - user needs to focus on initial direction
    if (isFirstInstructionSpeaking) {
      console.log('⏸️ Obstacle detection paused during first instruction');
      return;
    }

    // SKIP DETECTION WHILE SPEAKING - keep instructions smooth
    if (isSpeaking) {
      return; // Silently skip, don't log to reduce console spam
    }

    let detectionCount = 0;
    let lastDetectionLog = Date.now();

    const captureAndDetectObstacles = async () => {
      try {
        detectionCount++;
        
        // NOTE: Removed isDetectingRef blocking - allow frames to process in parallel
        // for truly real-time detection
        
        // Log every 10 attempts
        if (Date.now() - lastDetectionLog > 10000) {
          console.log(`🔄 Obstacle detection running (attempt #${detectionCount})...`);
          lastDetectionLog = Date.now();
        }

        if (!videoRef.current) {
          console.warn('⚠️ Video reference lost');
          return;
        }

        // Check video is playing and has data
        if (videoRef.current.readyState < 2) {
          console.log('⏳ Video not ready yet, readyState:', videoRef.current.readyState);
          return;
        }

        // Get video dimensions
        const width = videoRef.current.videoWidth;
        const height = videoRef.current.videoHeight;
        
        if (width === 0 || height === 0) {
          console.warn('⚠️ Video dimensions not available yet');
          return;
        }

        const canvas = document.createElement('canvas');
        canvas.width = width;
        canvas.height = height;
        const ctx = canvas.getContext('2d');
        
        if (!ctx) {
          console.error('❌ Could not get canvas context');
          return;
        }

        ctx.drawImage(videoRef.current, 0, 0);
        // Ultra-low quality (0.3) for fastest real-time processing
        const imageData = canvas.toDataURL('image/jpeg', 0.3);

        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 2000); // 2 second timeout

        const response = await fetch(`${SOCKET_URL}/api/detect-obstacles`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ image: imageData }),
          signal: controller.signal
        });

        clearTimeout(timeout);

        if (!response.ok) {
          console.error(`❌ API error: ${response.status}`);
          return;
        }

        const data = await response.json();
        
        // Log less frequently to reduce spam
        if (detectionCount % 5 === 0) {
          console.log(`🔍 Detection: ${data.count} objects`);
        }

        if (data.detections && data.detections.length > 0) {
          // Get most urgent detection
          const urgencyOrder = { 'CRITICAL': 0, 'DANGER': 1, 'WARNING': 2, 'CAUTION': 3 };
          const mostUrgent = data.detections.reduce((prev, curr) => {
            const prevScore = urgencyOrder[prev.urgency] || 999;
            const currScore = urgencyOrder[curr.urgency] || 999;
            return currScore < prevScore ? curr : prev;
          });

          const now = Date.now();
          const distance = mostUrgent.distance || 5;
          const objectName = mostUrgent.name || 'object';
          const timeSinceLastAlert = now - lastAlertTime;

          // Less frequent logging
          if (detectionCount % 5 === 0) {
            console.log(`🔍 ${objectName} at ${distance.toFixed(2)}m`);
          }

          // CRITICAL: Very close obstacle (< 0.2m) - IMMEDIATE RED ALERT
          if (distance < 0.2) {
            if (timeSinceLastAlert > 10000) { // 10 second cooldown
              console.log(`🚨🚨🚨 CRITICAL ALERT - ${objectName.toUpperCase()} VERY CLOSE (${distance.toFixed(2)}m)`);
              
              // Set visual alert level
              setAlertLevel('CRITICAL');
              if (alertVisualTimeoutRef.current) clearTimeout(alertVisualTimeoutRef.current);
              
              // IMMEDIATELY CANCEL all ongoing speech synthesis for instant interrupt
              if (window.speechSynthesis) {
                window.speechSynthesis.cancel();
                console.log('🛑 EMERGENCY: Cancelled all ongoing speech');
              }
              
              // Speak the critical warning 3 times with 2-second pauses
              const speakCriticalWarning = (times) => {
                if (times <= 0) {
                  console.log('✅ Critical alert sequence completed');
                  isPlayingAlertRef.current = false;
                  // Clear critical alert visual after sequence
                  setAlertLevel(null);
                  return;
                }
                
                isPlayingAlertRef.current = true;
                // More specific: include object type
                let warningText = 'Please stop ';
                if (objectName === 'person') {
                  warningText += 'person ahead, please stop person ahead, stop stop stop';
                } else if (['car', 'motorcycle', 'bus', 'truck'].includes(objectName)) {
                  warningText += 'vehicle ahead, please stop vehicle ahead, stop stop stop';
                } else {
                  warningText += 'obstacle ahead, please stop obstacle ahead, stop stop stop';
                }
                
                speak(warningText, true, () => {
                  console.log(`⏱ Critical alert ${4 - times}/3...`);
                  setTimeout(() => {
                    speakCriticalWarning(times - 1);
                  }, 2000);
                });
              };
              
              speakCriticalWarning(3); // Say it 3 times
              setLastAlertTime(now);
              setLastAlertedObject(objectName);
            } else {
              console.log(`⏳ Critical cooldown: ${((10000 - timeSinceLastAlert)/1000).toFixed(1)}s remaining`);
            }
          } 
          // DANGER: Near obstacle (0.2-0.35m) - Announce AFTER instruction finishes
          else if (distance >= 0.2 && distance < 0.35) {
            if (timeSinceLastAlert > 5000) { // 5 second cooldown (NO yellow animation)
              console.log(`⚠️ DANGER: ${objectName} at ${distance.toFixed(2)}m`);
              
              // Queue announcement for after instruction finishes
              const distanceStr = distance.toFixed(2);
              pendingDistantAlertRef.current = `${objectName.charAt(0).toUpperCase() + objectName.slice(1)} is ${distanceStr} meters in front`;
              
              setLastAlertTime(now);
              setLastAlertedObject(objectName);
            } else {
              console.log(`⏳ Cooldown: ${((5000 - timeSinceLastAlert)/1000).toFixed(1)}s remaining`);
            }
          }
          // WARNING: Distant obstacle (0.35-5m) - Queue announcement, no visual alert
          else if (distance >= 0.35 && distance < 5) {
            // Queue this alert to be announced after instruction finishes (no yellow animation)
            if (timeSinceLastAlert > 5000) {
              const distanceStr = distance < 1 ? distance.toFixed(2) : distance.toFixed(1);
              pendingDistantAlertRef.current = `${objectName.charAt(0).toUpperCase() + objectName.slice(1)} is about ${distanceStr} meters away`;
              console.log(`📍 Obstacle queued for announcement: ${pendingDistantAlertRef.current}`);
              setLastAlertTime(now);
            }
          }
        } else {
          console.log('✅ No obstacles detected - path clear');
        }
      } catch (err) {
        console.error('❌ Obstacle detection error:', err);
      } finally {
        // Always clear the detecting flag to prevent permanent blocking
        isDetectingRef.current = false;
      }
    };

    console.log('🟢 Starting obstacle detection (REAL-TIME MODE - every 400ms)');
    // Capture frames every 400ms (2.5 FPS) - parallel processing for real-time detection
    const interval = setInterval(captureAndDetectObstacles, 400);
    
    return () => {
      console.log('🛑 Stopping obstacle detection loop');
      clearInterval(interval);
    };
  }, [isNavigating, obstacleDetectionActive, lastAlertTime, lastAlertedObject, isFirstInstructionSpeaking, speak]);

  // Handle start navigation
  const handleStartNavigation = useCallback((location) => {
    setSelectedLocation(location);
    
    // Calculate estimated time (10-15 minutes ONLY)
    const randomTime = Math.floor(Math.random() * 6) + 10; // 10-15 minutes
    setEstimatedTime(randomTime);

    // Step 1: Announce navigation beginning
    const beginningAnnouncement = `Navigation to ${location} begins`;
    setCurrentInstruction(beginningAnnouncement); // Display on screen
    
    console.log('📍 Starting navigation sequence for:', location);
    console.log('⏱ Estimated time:', randomTime, 'minutes');
    
    speak(beginningAnnouncement, false, () => {
      // Step 2: After beginning announcement, announce destination time
      const timeAnnouncement = `You will reach your destination in about ${randomTime} minutes`;
      setCurrentInstruction(timeAnnouncement); // Display on screen
      
      speak(timeAnnouncement, false, () => {
        // Step 3: Now start actual navigation
        setNavigationStarted(true);
        setIsNavigating(true);
        setObstacleDetectionActive(true);
        
        console.log('🚀 Fetching first instruction...');
        
        fetch(`${SOCKET_URL}/api/start-navigation`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ destination: location }),
        })
          .then((res) => {
            console.log('📡 API Response status:', res.status);
            return res.json();
          })
          .then((data) => {
            console.log('📡 API Response data:', data);
            if (data.success) {
              console.log('✅ First instruction:', data.instruction);
              
              // Add guidance for first instruction
              const guidedInstruction = data.instruction + '. Now, swipe up for the next instruction, or swipe down for the previous instruction.';
              
              setCurrentInstruction(guidedInstruction);
              setShowPopup(true);
              
              // Step 4: Speak the first instruction with guidance after brief pause
              // Flag that first instruction is being spoken - pause obstacle detection
              setIsFirstInstructionSpeaking(true);
              setTimeout(() => {
                speakInstruction(guidedInstruction);
              }, 500);
            } else {
              const errorMsg = 'Navigation failed: ' + (data.error || 'Unknown error');
              console.error('❌', errorMsg);
              setCurrentInstruction(errorMsg);
              speak(errorMsg, true);
              setIsNavigating(false);
              setNavigationStarted(false);
              setObstacleDetectionActive(false);
            }
          })
          .catch((err) => {
            const errorMsg = `Navigation API Error: ${err.message || err}`;
            console.error('❌', errorMsg);
            console.error('Full error:', err);
            setCurrentInstruction(errorMsg);
            speak(`Navigation failed. ${err.message}`, true);
            setIsNavigating(false);
            setNavigationStarted(false);
            setObstacleDetectionActive(false);
          });
      });
    });
  }, [speak, speakInstruction]);

  // Handle next step
  const handleNextStep = useCallback(() => {
    if (!socketRef.current || !isNavigating) return;

    fetch(`${SOCKET_URL}/api/next-step`)
      .then((res) => res.json())
      .then((data) => {
        console.log('Next instruction:', data.instruction);
        // Clear any stale paused instruction reference
        pausedInstructionRef.current = null;
        // IMPORTANT: Set screen text FIRST, then speak
        setCurrentInstruction(data.instruction);
        // Small delay to ensure state update before speaking
        setTimeout(() => {
          speakInstruction(data.instruction);
        }, 50);
        
        // Check if we've reached the destination
        if (data.instruction && data.instruction.toLowerCase().includes('reached your destination')) {
          console.log('✅ Destination reached!');
          // After speaking destination message, reset to welcome
          setTimeout(() => {
            setIsNavigating(false);
            setNavigationStarted(false);
            setSelectedLocation(null);
            setShowPopup(false);
            setObstacleDetectionActive(false);
            setLastAlertTime(0);
            setLastAlertedObject('');
            setCurrentInstruction('Navigation complete. Where would you like to go?');
            speak('Navigation complete. Where would you like to go?');
            
            // Restart listening
            if (recognitionRef.current) {
              try {
                setTimeout(() => {
                  recognitionRef.current.start();
                }, 500);
              } catch (err) {
                console.error('Error restarting recognition:', err);
              }
            }
          }, 3000);
        }
      })
      .catch((err) => console.error('Next step error:', err));
  }, [isNavigating, speakInstruction, speak]);

  // Handle previous step
  const handlePrevStep = useCallback(() => {
    if (!socketRef.current || !isNavigating) return;

    fetch(`${SOCKET_URL}/api/prev-step`)
      .then((res) => res.json())
      .then((data) => {
        console.log('Previous instruction:', data.instruction);
        // Clear any stale paused instruction reference
        pausedInstructionRef.current = null;
        // IMPORTANT: Set screen text FIRST, then speak
        setCurrentInstruction(data.instruction);
        // Small delay to ensure state update before speaking
        setTimeout(() => {
          speakInstruction(data.instruction);
        }, 50);
      })
      .catch((err) => console.error('Prev step error:', err));
  }, [isNavigating, speakInstruction]);

  // Handle stop navigation
  const handleStopNavigation = useCallback(() => {
    if (!socketRef.current) return;

    fetch(`${SOCKET_URL}/api/stop-navigation`, {
      method: 'POST',
    })
      .then((res) => res.json())
      .then(() => {
        setIsNavigating(false);
        setNavigationStarted(false);
        setSelectedLocation(null);
        setShowPopup(false);
        setObstacleDetectionActive(false);
        setLastAlertTime(0);
        setLastAlertedObject('');
        setCurrentInstruction('Navigation stopped. Where would you like to go?');
        speak('Navigation stopped. Where would you like to go?');
        
        // Restart listening
        if (recognitionRef.current) {
          try {
            setTimeout(() => {
              recognitionRef.current.start();
            }, 500);
          } catch (err) {
            console.error('Error restarting recognition:', err);
          }
        }
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

      {/* RED ALERT OVERLAY - ONLY FOR CRITICAL OBSTACLES */}
      {alertLevel === 'CRITICAL' && (
        <div
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            backgroundColor: 'rgba(255, 0, 0, 0.5)',
            pointerEvents: 'none',
            animation: 'pulse-critical 0.3s infinite',
            zIndex: 1000
          }}
        >
          <style>{`
            @keyframes pulse-critical {
              0%, 100% { opacity: 0.7; }
              50% { opacity: 0.3; }
            }
          `}</style>
        </div>
      )}

      <div className="instruction-panel">
        <div className="instruction-text">{currentInstruction}</div>

        {!navigationStarted ? (
          <div className="mode-selection">
            <p style={{fontSize: '0.9rem', marginBottom: '15px', color: '#00c6ff'}}>
              {isListening ? '🎤 Listening for your destination...' : 'Say where you would like to go'}
            </p>
          </div>
        ) : isNavigating ? (
          <div className="navigation-controls">
            <div className="nav-info">
              <span>📍 {selectedLocation}</span>
              <span>⏱ ~{estimatedTime} min</span>
            </div>
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
        ) : null}
      </div>

      <NavigationPopup 
        instruction={currentInstruction}
        onNext={handleNextStep}
        onPrev={handlePrevStep}
        isShowing={showPopup && isNavigating}
      />

      <div className="status-bar">
        <span>{isConnected ? '✅ Connected' : '❌ Offline'}</span>
        {selectedLocation && <span>📍 {selectedLocation}</span>}
        {obstacleDetectionActive && <span>🔍 Obstacle Detection Active</span>}
      </div>
    </div>
  );
}

export default Dashboard;
