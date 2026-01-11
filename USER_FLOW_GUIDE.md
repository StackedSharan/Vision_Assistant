# College Navigation System - User Flow Guide

## Quick Start

### System Startup
1. Dashboard loads
2. System plays audio: **"Welcome to College Navigation. Where would you like to go in your college? You can say canteen, engineering, architecture, or any other location."**
3. Microphone is listening for voice input

### Navigation Flow

#### Step 1: Speak Your Destination
- Say any available location: **"canteen"**, **"engineering"**, **"architecture"**, **"aiml"**, **"parking"**, **"ugpg"**, **"mainbuilding"**
- System recognizes your speech and confirms

#### Step 2: Route Announcement
System announces:
```
"ROUTE FOUND TO [YOUR DESTINATION IN UPPERCASE]. 
YOU WILL REACH YOUR DESTINATION IN ABOUT X MINUTES."
```
(X is randomly calculated between 5-30 minutes for demonstration)

#### Step 3: Navigation Starts
- First instruction displays in **Popup Window**
- Popup shows:
  - **Header:** "Navigation Instructions"
  - **Main text:** Current instruction in green (#00ff88)
  - **Gesture hints:** 
    - "⬆ Swipe Up for Next" (cyan)
    - "⬇ Swipe Down for Previous" (orange)
- Location and estimated time shown above buttons

#### Step 4: Get Instructions
**Three ways to navigate instructions:**

1. **Swipe Gestures:**
   - **Swipe UP** → Next instruction
   - **Swipe DOWN** → Previous instruction

2. **Voice Commands:**
   - Say **"next"** → Get next instruction
   - Say **"previous"** or **"back"** → Get previous instruction

3. **Touch Buttons:**
   - **⬆ Prev** button
   - **⬇ Next** button
   - **⏹ Stop** button

#### Step 5: Stop Navigation
- Click **"⏹ Stop"** button, OR
- Say **"stop"** (if voice is enabled)

System returns to initial state and asks for destination again.

## Available Locations
- 🚪 **Entrance** (default starting point)
- 🍽️ **Canteen**
- 🏗️ **Engineering**
- 🎨 **Architecture**
- 🤖 **AIML**
- 🚗 **Parking**
- 🏢 **UGPG** (Undergraduate/Postgraduate)
- 🏛️ **Mainbuilding**

## UI Components

### Main Dashboard
- **Video Feed:** Camera stream (background)
- **Instruction Panel:** Bottom section with text and controls
- **Status Bar:** Connection status and current location

### Navigation Popup
- Appears when navigation starts
- Displays current instruction in large text
- Shows gesture hints
- Touch-enabled for swipe interactions
- Can be dismissed or navigated with gestures

### Control Buttons
- **Prev (⬆):** Previous step
- **Next (⬇):** Next step  
- **Stop (⏹):** Stop navigation

## Status Indicators

### Connection Status
- **✅ Connected** - System is ready
- **❌ Offline** - No connection to server

### Listening Indicator
- 🎤 **Listening...** - Microphone is active

### Navigation Info
- 📍 **Location name** - Current destination
- ⏱ **~X min** - Estimated travel time

## Voice Recognition

### Supported Languages
- English (en-US)

### How It Works
- **Continuous listening** - Always listening when waiting for input or navigating
- **Auto-restart** - Automatically restarts if microphone error occurs
- **Minimum input** - Ignores very short or unclear speech
- **Real-time feedback** - Console logs show what was recognized

### Troubleshooting Voice Input
1. **Not recognizing location:**
   - Speak clearly and naturally
   - Say the full location name
   - Wait for the system to confirm

2. **Microphone not working:**
   - Check camera/microphone permissions
   - Allow microphone access when prompted
   - Ensure no other app is blocking audio input

3. **Speech not understood:**
   - System will announce "Location not recognized. Please try again."
   - Speak the destination name again

## Demo Features

### Random Travel Time
- Each route gets a random estimated time (5-30 minutes)
- Helps demonstrate real-world navigation scenarios
- Provides a more realistic experience

### Starting Point
- All routes start from **"Entrance"** by default
- System uses this as the origin for all navigations
- Suitable for campus tour demonstration

## Accessibility Features

### Multi-Modal Interaction
- ✅ Voice input (speech recognition)
- ✅ Touch gestures (swipe)
- ✅ Button controls (tap)
- ✅ Audio feedback (text-to-speech)

### Visual Design
- High contrast colors for visibility
- Large, readable text (min 1rem)
- Color-coded hints (cyan/orange)
- Clear visual hierarchy
- Smooth animations for feedback

### Audio Feedback
- System announces all major actions
- Clear, natural voice
- Adjustable speech rate (default 1.0)

## Tips for Best Experience

1. **Speak clearly** - Use natural volume and pace
2. **Wait for prompts** - Let the system finish speaking before speaking
3. **Use gestures** - Swipe gestures are the fastest way to navigate
4. **Face camera** - Keep camera pointed at surroundings during navigation
5. **Stay aware** - Watch for obstacles while following instructions

## Technical Details

### Browser Requirements
- Modern browser with Web Speech API support
- WebRTC enabled for camera access
- Socket.IO support for real-time communication

### Supported Browsers
- Chrome 25+
- Edge 79+
- Opera 27+
- Safari 14.1+
- Firefox (with limitations)

### Network
- Requires connection to backend server (default: localhost:5000)
- Uses Socket.IO for WebSocket communication
- REST API for instruction fetching
