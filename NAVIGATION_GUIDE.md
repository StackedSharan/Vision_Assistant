# Navigation Guide for Vision Assistant

## Overview

The Vision Assistant helps blind and visually impaired students navigate the college campus using voice commands, real-time obstacle detection, and spatial audio cues. This guide explains how to use the navigation features.

## Campus Landmarks

### Main Landmarks on Campus

1. **Main Entrance** - The primary entry point to the college campus. Located at the beginning of all routes. Good starting point for orientation.

2. **Architecture Block (Arch)** - Home to architecture students. Near the main entrance. Known for its distinctive modern building design. Good reference point.

3. **Engineering Building (Engg)** - Houses the engineering departments. Central location on campus. Major hub for classes and labs.

4. **Canteen (Canteen)** - The main food facility on campus. Located centrally. Popular meeting point. Great for breaks and refreshments.

5. **Underground (UG)** - Undergraduate hostel facility. Residential area. Quieter location compared to main campus areas.

6. **Postgraduate (UGPG)** - Postgraduate and advanced research facilities. Academic and research center.

## Voice Commands for Navigation

### Basic Navigation Commands

**Format:** "From [Start Location] to [End Location]"

**Examples:**
- "From Main Entrance to Canteen"
- "From Architecture Block to Engineering Building"
- "From Engg to UG Hostel"
- "From Canteen to UGPG Building"

### Supported Variations

The system recognizes multiple ways to say landmark names:

- **Engineering Building**: "Engg", "Engineering Block", "Engineering", "Engg Block"
- **Architecture Block**: "Arch", "Architecture", "Architecture Block"
- **Main Entrance**: "Entrance", "Main Gate", "Gate"
- **Underground Hostel**: "UG Hostel", "UG", "Undergraduate", "Undergrad Hostel"
- **Postgraduate**: "UGPG", "Postgrad", "PG Building", "Research Building"

### What Happens After You Give a Voice Command

1. **Route Confirmation** - The system announces the selected route and provides initial navigation instructions
2. **Turn-by-Turn Guidance** - You receive voice instructions as you navigate
3. **Real-time Obstacle Alerts** - The system warns you about obstacles ahead using:
   - **Verbal warnings** - "Person 2.5m ahead"
   - **Spatial audio cues** - Obstacles are localized left/right using pan audio
   - **Haptic feedback** - Device vibration intensity increases as obstacles get closer

4. **Arrival Notification** - System confirms when you reach your destination

## Understanding Obstacle Alerts

### Urgency Levels

**🟢 Safe (Green)** - No critical obstacles
- No alert is spoken
- Path is clear for navigation

**🟡 Warning (Yellow)** - Obstacle 1.5-3 meters away
- Single vibration pulse (100ms)
- Verbal alert: "Person 2.5m ahead"
- Safe to proceed with caution

**🔴 Critical (Red)** - Obstacle less than 1.5 meters away
- Urgent vibration pattern (200ms-100ms-200ms)
- Urgent verbal alert: "⚠️ ALERT: Person 1.0m ahead - URGENT"
- Recommend stop and assess situation

### How Obstacles Are Detected

- System uses computer vision (YOLOv8) to detect:
  - People
  - Vehicles (cars, bikes, buses)
  - Animals (dogs, cats)
  - Obstacles (chairs, bottles, etc.)

- **Distance Estimation** - Based on relative size of detected objects
- **Position Tracking** - Obstacles are tracked over multiple frames to reduce false alerts
- **Duplicate Suppression** - Same obstacle won't be repeated if it persists longer than expected

## Accessibility Features

### Double-Tap Voice Assistant

- **Activation** - Double-tap anywhere on the screen to activate the voice assistant
- **Function** - Ask questions about campus, landmarks, weather, or get help
- **Response** - AI-powered assistant provides verbal answers using text-to-speech

### Voice Input Tips

1. **Speak Clearly** - Use normal speaking voice
2. **Wait for Beep** - System will indicate when it's ready to listen
3. **Natural Language** - You can use conversational speech, not just commands
4. **Repeat if Needed** - If system didn't understand, repeat your command

### Spatial Audio Cues

- **Left/Right Panning** - Obstacles are indicated directionally using stereo audio
- **Volume Variation** - Closer obstacles have higher volume
- **Audio Pan Range** - -1.0 (far left) to +1.0 (far right)

## Estimated Travel Times

Travel times depend on walking speed (approximately 1.2 meters/second or 4.3 km/h):

- **Main Entrance to Canteen** - ~3-4 minutes
- **Main Entrance to Engineering Building** - ~4-5 minutes
- **Engineering Building to UG Hostel** - ~5-7 minutes
- **Canteen to UGPG Building** - ~4-6 minutes

*Note: Times may vary based on campus conditions and actual walking speed*

## Troubleshooting Navigation

### "Route not found" Message
- Check that both start and end landmarks are on the college campus
- Try using alternate landmark names (e.g., "Engg" instead of "Engineering")

### Obstacle Alerts Too Frequent
- System filters duplicate detections across frames
- Only persistent obstacles trigger repeated alerts
- If frustration occurs, you can pause navigation and resume after the obstacle passes

### GPS/Location Issues
- Ensure Location Services are enabled on your device
- System works best in open areas
- Indoor accuracy may be limited

### Voice Command Not Recognized
- Speak more clearly
- Wait for the "listening" tone before speaking
- Use landmark names from the supported list
- Try alternative landmark names

## Advanced Features

### Double-Tap Voice Assistant

Beyond navigation, you can ask the chatbot:
- "What landmarks are nearby?"
- "How long is my journey?"
- "What obstacles are ahead?"
- "Describe the canteen location"
- "What's the shortest path to Engineering?"

### Calibration

For better distance estimation:
1. The system can be calibrated using your device's camera
2. Calibration stores a reference focal length
3. This improves obstacle distance accuracy over time

## Tips for New Users

1. **Start with Short Routes** - Begin with nearby destinations to build confidence
2. **Familiar Routes First** - Try routes you've walked before manually
3. **Listen Carefully** - Pay attention to spatial audio cues (left/right panning)
4. **Slow Walking Speed** - Initially, walk slower than normal to give system time to detect obstacles
5. **Hands Free** - Use voice commands; system is designed for hands-free operation

## Safety Reminders

⚠️ **Always Maintain Situational Awareness**
- Treat system recommendations as assistance, not definitive guidance
- Stop if you feel unsafe or disoriented
- Use a cane or other mobility aid in conjunction with this system
- Always consider your own judgment and safety first

## Getting Help

If you encounter issues:
1. Double-tap to activate voice assistant
2. Ask "Help" or "What can you do?"
3. System will provide available commands and guidance
4. Report issues to accessibility support team

## Example Navigation Session

**User:** "From Main Entrance to Canteen"

**System:** "Route confirmed. From Main Entrance to Canteen. First instruction: Move forward 50 meters along the main path. Proceed."

**[User walks forward]**

**System:** "Person 2.5 meters ahead on the left." [Single vibration pulse]

**[User slows down and adjusts course]**

**System:** "Person cleared. Continue forward 40 meters. Next turn will be right at the courtyard."

**[User continues walking]**

**System:** "Turn right at the courtyard. Canteen entrance will be 30 meters ahead."

**[User arrives]**

**System:** "You have arrived at your destination: Canteen. Navigation complete."

---

## FAQ

**Q: Can I use the system outdoors only?**
A: The system works best outdoors where GPS and camera vision are reliable. Indoor navigation is limited.

**Q: What if I don't say the exact landmark name?**
A: The system recognizes common variations and abbreviations (e.g., "Engg" for "Engineering Building").

**Q: How accurate is the obstacle detection?**
A: Detection is ~90% accurate within 5 meters. False positives are filtered using temporal smoothing.

**Q: Can I ask the chatbot questions while navigating?**
A: Yes! Double-tap anytime to ask questions. The chatbot can answer queries about landmarks, directions, or campus information.

**Q: What happens if GPS signal is lost?**
A: System will alert you. Try moving to a more open area or wait for signal recovery. Last known position will be maintained.

