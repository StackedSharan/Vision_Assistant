// frontend/src/App.js (FINAL VERSION)

import React, { useState } from 'react';
import './App.css';

function App() {
  const [statusMessage, setStatusMessage] = useState('Press the button to start the assistant.');
  const [isAssistantActive, setIsAssistantActive] = useState(false);

  // Helper function to get GPS location
  const getCurrentLocation = () => {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        return reject(new Error("Geolocation is not supported."));
      }
      navigator.geolocation.getCurrentPosition(
        (position) => resolve(position.coords),
        () => reject(new Error("Unable to retrieve your location. Please grant permission."))
      );
    });
  };

  // The main function that triggers the entire interactive assistant
  const handleStartAssistant = async () => {
    if (isAssistantActive) return;

    setIsAssistantActive(true);
    setStatusMessage('Getting your location...');

    try {
      const location = await getCurrentLocation();
      setStatusMessage('Location found. Activating assistant...');

      // Call the single, powerful backend endpoint, sending the location
      const response = await fetch('http://localhost:5001/api/interactive_assistant', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          latitude: location.latitude,
          longitude: location.longitude,
        }),
      });

      if (!response.ok) {
        throw new Error(`Server error: ${response.status}`);
      }
      
      const data = await response.json();
      console.log("Final response from backend:", data);

      // Display the final outcome of the conversation
      setStatusMessage(`Interaction finished. Last response: "${data.response}"`);

    } catch (error) {
      console.error("Error during interaction:", error.message);
      setStatusMessage(`Error: ${error.message}`);
    } finally {
      // Re-enable the button for the next interaction
      setIsAssistantActive(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Vision Assistant</h1>
        <p>{statusMessage}</p>
        <button className="activate-button" onClick={handleStartAssistant} disabled={isAssistantActive}>
          {isAssistantActive ? 'Assistant is Active...' : 'Activate Assistant'}
        </button>
      </header>
    </div>
  );
}

export default App;