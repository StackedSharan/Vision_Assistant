import React, { useEffect, useRef, useState } from 'react';
import io from 'socket.io-client';

const socket = io();

function speak(text) {
  if ('speechSynthesis' in window) {
    const u = new SpeechSynthesisUtterance(text);
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(u);
  } else {
    alert(text);
  }
}

function captureFrame(video) {
  const canvas = document.createElement('canvas');
  canvas.width = video.videoWidth || 640;
  canvas.height = video.videoHeight || 480;
  const ctx = canvas.getContext('2d');
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  return canvas.toDataURL('image/jpeg', 0.7);
}

function ChatBox() {
  const [listening, setListening] = useState(false);
  const [lastMessage, setLastMessage] = useState('');
  const videoRef = useRef(null);
  const recognitionRef = useRef(null);
  const lastTapTime = useRef(0);

  useEffect(() => {
    // setup socket listeners
    socket.on('surroundings_analysis', (data) => {
      const msg = data.message || data;
      setLastMessage(msg);
      speak(msg);
    });

    socket.on('navigation_response', (data) => {
      if (data.error) {
        setLastMessage(data.error);
        speak(data.error);
      } else if (data.instructions) {
        const first = data.instructions[0];
        const msg = first ? first.text : 'Route received.';
        setLastMessage(msg);
        speak(msg);
      }
    });

    // prepare camera stream (hidden) so analyze_surroundings can capture frame
    async function initCamera() {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'environment' }, audio: false });
        if (videoRef.current) videoRef.current.srcObject = stream;
        if (videoRef.current) videoRef.current.play().catch(() => { });
      } catch (e) {
        console.warn('Camera not available:', e);
      }
    }
    initCamera();

    // Listen for custom event from Dashboard
    const handleActivateChat = () => {
      handleLongPressActivated();
    };
    window.addEventListener('activate-chat', handleActivateChat);

    return () => {
      socket.off('surroundings_analysis');
      socket.off('navigation_response');
      window.removeEventListener('activate-chat', handleActivateChat);
    };
  }, []);

  function startRecognition(onResult) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      const fallback = prompt('Speech recognition not supported. Please type your question:');
      onResult(fallback || '');
      return;
    }

    const recog = new SpeechRecognition();
    recog.lang = 'en-US';
    recog.interimResults = false;
    recog.maxAlternatives = 1;
    recog.onresult = (e) => {
      const t = e.results[0][0].transcript;
      onResult(t);
    };
    recog.onerror = (e) => {
      console.error('Speech recognition error', e);
      onResult('');
    };
    recog.start();
    recognitionRef.current = recog;
  }

  function stopRecognition() {
    if (recognitionRef.current) {
      try { recognitionRef.current.stop(); } catch (e) { }
      recognitionRef.current = null;
    }
  }

  async function handleLongPressActivated() {
    setListening(true);
    speak('Listening. Please ask your question.');

    startRecognition(async (text) => {
      setListening(false);
      stopRecognition();
      if (!text) {
        speak('Sorry, I did not catch that.');
        return;
      }

      setLastMessage(text);

      const q = text.toLowerCase();

      if (q.includes('what') && q.includes('front')) {
        // analyze surroundings: capture frame and emit
        if (videoRef.current) {
          const dataUrl = captureFrame(videoRef.current);
          socket.emit('analyze_surroundings', { image_data: dataUrl });
          speak('Analyzing surroundings now.');
        } else {
          speak("Camera isn't available right now.");
        }
        return;
      }

      if (q.includes('how long') || q.includes('how much time') || q.includes('reach')) {
        // ask for destination
        speak('What is your destination?');
        startRecognition(async (destText) => {
          stopRecognition();
          if (!destText) { speak('I did not catch the destination.'); return; }
          const dest = destText.toLowerCase();

          // get known landmarks and try to match
          try {
            const res = await fetch('/api/landmarks');
            const js = await res.json();
            const names = js.landmarks || [];
            // simple match: find landmark that includes dest phrase
            let matched = null;
            for (const n of names) {
              if (n.includes(dest) || dest.includes(n)) { matched = n; break; }
            }

            if (!matched && names.length > 0) matched = names[0]; // fallback to first landmark

            // pick a start: fallback to first landmark as current
            const start = names.length > 0 ? names[0] : matched;

            const etaRes = await fetch('/api/eta', {
              method: 'POST', headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({ start: start, end: matched || dest })
            });
            const etaJson = await etaRes.json();
            if (etaJson.error) {
              speak('Could not compute ETA: ' + (etaJson.error || ''));
            } else {
              speak(etaJson.message || 'You should be there in a few minutes.');
            }
          } catch (e) {
            console.error('ETA error', e);
            speak('There was an error computing the ETA.');
          }
        });
        return;
      }

      // default: echo back / generic assistant response
      // Try to answer using surroundings if contains keywords
      if (q.includes('what') || q.includes('see') || q.includes('in front')) {
        if (videoRef.current) {
          const dataUrl = captureFrame(videoRef.current);
          socket.emit('analyze_surroundings', { image_data: dataUrl });
          speak('Analyzing and responding.');
        } else {
          speak('Camera not available; I cannot analyze surroundings.');
        }
        return;
      }

      // fallback reply
      // Use server-side chat (RAG) for general questions
      try {
        const res = await fetch('/api/chat', {
          method: 'POST', headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ query: text })
        });
        const js = await res.json();
        if (js.answer) {
          setLastMessage(js.answer);
          speak(js.answer);
        } else if (js.error) {
          speak('Error from assistant: ' + js.error);
        } else {
          speak('Sorry, I could not get an answer.');
        }
      } catch (e) {
        console.error('Chat API error', e);
        speak('There was an error contacting the assistant.');
      }
    });
  }

  function handlePointerDown() {
    // Detect double-tap: two taps within 300ms
    const now = Date.now();
    if (now - lastTapTime.current < 300) {
      // Double-tap detected
      handleLongPressActivated();
    }
    lastTapTime.current = now;
  }

  return (
    <>
      <video ref={videoRef} style={{ display: 'none' }} playsInline muted />
      {/* Screen-wide double-tap zone for ChatBox activation */}
      <div
        onMouseDown={handlePointerDown}
        onTouchStart={handlePointerDown}
        aria-label="Double-tap anywhere to activate voice assistant"
        style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 1, pointerEvents: 'none' }}
      />
      {/* Accessibility announcement */}
      <div aria-live="polite" aria-label="Double-tap anywhere on the screen to activate the voice assistant">
      </div>
      {/* Chat response box (only show when assistant speaks) */}
      {lastMessage && (
        <div aria-live="polite" style={{ position: 'fixed', right: 18, bottom: 92, width: 260, background: '#fff', color: '#000', padding: 8, borderRadius: 8, boxShadow: '0 4px 10px rgba(0,0,0,0.2)' }}>
          <strong>Assistant</strong>
          <div style={{ marginTop: 6 }}>{lastMessage}</div>
        </div>
      )}
    </>
  );
}

export default ChatBox;
