// frontend/src/App.js

import React, { useState } from 'react';
import './App.css';

function App() {
  const [statusMessage, setStatusMessage] = useState('Say "remember this place as [name]"');
  const [isAssistantActive, setIsAssistantActive] = useState(false);

  const getCurrentLocation = () => {
    return new Promise((resolve, reject) => {
      if (!navigator.geolocation) {
        reject(new Error("Geolocation is not supported."));
      } else {
        navigator.geolocation.getCurrentPosition(
          (position) => resolve(position.coords),
          () => reject(new Error("Unable to retrieve your location."))
        );
      }
    });
  };
  
  // This is a new helper function for our new API call
  const sendPlaceToBackend = async (placeName, location) => {
    const { latitude, longitude } = location;
    
    // This is a POST request, so we need to configure it with more options
    const response = await fetch('http://localhost:5000/api/remember_place', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json', // Tell the server we're sending JSON
      },
      // The data we are sending needs to be a string, so we use JSON.stringify
      body: JSON.stringify({
        name: placeName,
        latitude: latitude,
        longitude: longitude,
      }),
    });

    if (!response.ok) {
      throw new Error("Failed to save the location on the backend.");
    }
    
    return response.json(); // Return the success message from the server
  };


  const handleStartAssistant = async () => {
    if (isAssistantActive) return;

    setIsAssistantActive(true);
    setStatusMessage('First, getting your location...');

    try {
      // 1. Get current GPS location
      const location = await getCurrentLocation();
      setStatusMessage('Location found. Now, please speak your command...');

      // In a real app, we would call the /api/listen endpoint here.
      // For this test, we will use a prompt to simulate the voice command.
      const command = prompt("Please enter your command now:", "remember this place as home");

      // 2. Parse the command to see if it's our "remember" command
      if (command && command.toLowerCase().startsWith('remember this place as')) {
        // Extract the name of the place from the command string
        const placeName = command.substring('remember this place as'.length).trim();
        
        if (placeName) {
          setStatusMessage(`Trying to remember this place as "${placeName}"...`);
          
          // 3. Call our new function to send the data to the backend
          const result = await sendPlaceToBackend(placeName, location);
          
          // 4. Display the confirmation message from the server
          setStatusMessage(result.message);

        } else {
          setStatusMessage("You need to provide a name, like 'remember this place as home'.");
        }
      } else {
        // Here is where we would handle other commands like "what's around me?"
        setStatusMessage("I didn't understand that command. Please try again.");
      }

    } catch (error) {
      console.error("Error:", error.message);
      setStatusMessage(error.message);
    } finally {
      setIsAssistantActive(false);
    }
  };

  return (
    <div className="App">
      <header className="App-header">
        <h1>Vision Assistant</h1>
        <p>{statusMessage}</p>
        
        <button 
          className="activate-button" 
          onClick={handleStartAssistant} 
          disabled={isAssistantActive}
        >
          {isAssistantActive ? 'Working...' : 'Activate Assistant'}
        </button>
      </header>
    </div>
  );
}

export default App;