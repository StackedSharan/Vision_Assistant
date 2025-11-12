// frontend/src/App.js (FINAL VERSION - Cleaned and Unified)

import React, { useState, useRef } from 'react';
import './App.css';

function App() {
  // --- MASTER LIST OF LANDMARKS ---
  // This list now contains your exact landmark names.
  const landmarkOptions = ["Architecture", "Engineering Block", "Entrance", "UG Block", "parking", "AIML Block", "Canteen"];

  // --- STATE FOR VISUAL POSITIONING & NAVIGATION ---
  const [vpsStatus, setVpsStatus] = useState("Ready");
  const [landmark, setLandmark] = useState("None"); // This will hold our confirmed starting position
  const [confidence, setConfidence] = useState(0);
  const [destination, setDestination] = useState(landmarkOptions[0]); // Default destination
  const videoRef = useRef(null); // Ref to hold the video element

  // --- FUNCTIONS FOR VISUAL POSITIONING & NAVIGATION ---

  const startWebcam = async () => {
    setVpsStatus("Starting webcam...");
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        setVpsStatus("Webcam active. Point at a landmark and click 'Confirm Position'.");
      }
    } catch (error) {
      console.error("Error accessing webcam:", error);
      setVpsStatus("Error: Could not access webcam. Please grant permission.");
    }
  };

  const confirmPosition = async () => {
    if (!videoRef.current || !videoRef.current.srcObject) {
      setVpsStatus("Error: Webcam is not active. Please start it first.");
      return;
    }
    
    setVpsStatus("Capturing image...");
    const canvas = document.createElement('canvas');
    canvas.width = videoRef.current.videoWidth;
    canvas.height = videoRef.current.videoHeight;
    const context = canvas.getContext('2d');
    context.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
    const imageDataURL = canvas.toDataURL('image/jpeg');
    
    setVpsStatus("Sending image to server for analysis...");
    try {
      const response = await fetch('http://127.0.0.1:5000/api/confirm_position', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ image: imageDataURL }),
      });
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      const result = await response.json();
      
      setLandmark(result.landmark); // This sets our confirmed start location
      setConfidence(result.confidence);
      setVpsStatus(`Position Confirmed: You are at the ${result.landmark}.`);
    } catch (error) {
      console.error("Error confirming position:", error);
      setVpsStatus("Error: Could not connect to the server.");
    }
  };

  const startNavigation = async () => {
    if (landmark === "None" || landmark === "") {
      setVpsStatus("Error: Please confirm your starting position first by pointing the camera at a landmark.");
      return;
    }
    if (landmark === destination) {
      setVpsStatus("You are already at your destination!");
      return;
    }

    setVpsStatus(`Calculating route from ${landmark} to ${destination}...`);
    try {
      const response = await fetch('http://127.0.0.1:5000/api/start_navigation', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          start_landmark: landmark,
          end_landmark: destination,
        }),
      });
      if (!response.ok) throw new Error(`Server error! status: ${response.status}`);
      const routeData = await response.json();

      if (routeData.error) {
        setVpsStatus(`Error: ${routeData.error}`);
      } else {
        // A real app would guide the user step-by-step. We display the first instruction.
        setVpsStatus(`Instruction: ${routeData.instructions[0]}`);
      }
    } catch (error) {
      console.error("Error starting navigation:", error);
      setVpsStatus("Error: Could not calculate route.");
    }
  };

  // --- JSX TO RENDER THE PAGE ---
  return (
    <div className="App">
      <header className="App-header">
        <h1>Vision Assistant</h1>
        
        <div className="feature-section">
          <h2>Visual Positioning & Navigation</h2>
          <p>Status: {vpsStatus}</p>
          
          <video 
            ref={videoRef} 
            width="320" 
            height="240" 
            autoPlay 
            playsInline 
            style={{ border: '2px solid #444', marginTop: '10px', backgroundColor: '#222' }}
          ></video>
          
          <div className="button-group">
            <button onClick={startWebcam}>Start Webcam</button>
            <button onClick={confirmPosition}>Confirm Position</button>
          </div>
          
          <h3>Confirmed Location: <span>{landmark}</span></h3>
          <h4>Confidence: <span>{(confidence * 100).toFixed(2)}%</span></h4>
          
          <div className="navigation-controls">
            <h3>Navigate To:</h3>
            <select 
              value={destination} 
              onChange={(e) => setDestination(e.target.value)}
              className="destination-select"
            >
              {landmarkOptions.map((option) => (
                <option key={option} value={option}>
                  {option}
                </option>
              ))}
            </select>
            <button onClick={startNavigation}>Start Navigation</button>
          </div>
        </div>

      </header>
    </div>
  );
}

export default App;