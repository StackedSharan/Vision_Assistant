# Quick Start & Testing Reference

## Starting the Application

### Terminal 1 - Backend
```bash
cd c:\Projects\Vision_Assistant\backend
python app.py
```
Expected output:
```
 * Running on http://localhost:5000
 * Socket.IO server started
```

### Terminal 2 - Frontend
```bash
cd c:\Projects\Vision_Assistant\frontend
npm start
```
Expected output:
```
On Your Network: http://xxx.x.x.x:3000
LOCAL: http://localhost:3000
```

---

## Quick Test Sequence

### ✅ Step 1: Destination Selection
- Say: **"canteen"** (clearly, when prompted)

### ✅ Step 2: Verify Navigation Sequence
Listen for (in order):
1. "Navigation to canteen begins"
2. "You will reach your destination in about X minutes" (X = 10-15)
3. First instruction announced

### ✅ Step 3: Test Swipes
- **Swipe UP** ↑ → Next instruction (check console: "✅ ⬆ SWIPED UP")
- **Swipe DOWN** ↓ → Previous instruction (check console: "✅ ⬇ SWIPED DOWN")

### ✅ Step 4: Test Buttons
- Click **⬆ Prev** → Previous instruction
- Click **⬇ Next** → Next instruction
- Click **⏹ Stop** → Stop navigation

### ✅ Step 5: Test Voice Commands
During navigation, say:
- **"next"** → Next instruction (console: "📢 Voice command: Next")
- **"previous"** → Previous instruction (console: "📢 Voice command: Previous")

### ✅ Step 6: Test Obstacle Detection
Move an object closer to camera:
- At 1-2 meters: "There is a person in front of you at about 1.5 meters away"
- Different object: Same format with different object name
- 3+ seconds later: No repeat (5-second cooldown active)

### ✅ Step 7: Test Critical Alert
Move object very close (< 0.2m):
- Hear: **"Warning obstacle ahead please stop"** (3 times, with 2-second gaps)
- Instructions paused during warnings
- Can't repeat for 10 seconds (10-second cooldown)

---

## Console Expectations

| Action | Expected Console Log |
|--------|----------------------|
| Page loads | `✅ Connected to server` |
| Listen for destination | `🎤 Starting listening...` |
| Say "canteen" | `🎤 You said: "canteen"` |
| Navigation starts | `📍 Starting navigation sequence for: canteen` |
| Swipe UP | `✅ ⬆ SWIPED UP - NEXT INSTRUCTION` |
| Swipe DOWN | `✅ ⬇ SWIPED DOWN - PREVIOUS INSTRUCTION` |
| Say "next" | `📢 Voice command: Next` |
| Obstacle detected | `🔍 Detection: person at 0.8m` |
| Alert plays | `⚠️ OBSTACLE ALERT: There is a person...` |
| Critical alert | `🚨🚨🚨 CRITICAL PROXIMITY ALERT` |

---

## Common Locations to Try

Available destinations:
- `canteen`
- `engineering`
- `architecture`
- `aiml`
- `ugpg`
- `entrance`
- `parking`
- `mainbuilding`

---

## Debugging Quick Checklist

### Swipes Not Working?
- [ ] Ensure you're swiping ON the popup (the white/dark box with instruction text)
- [ ] Swipe distance must be > 50px (several inches of movement)
- [ ] Try slow, deliberate swipes
- [ ] Check console for `📊 Swipe detected` logs

### Voice Not Working?
- [ ] Check microphone permissions in browser
- [ ] Speak clearly, wait 1-2 seconds after finishing
- [ ] Check console for `🎤 You said` logs
- [ ] Try different location names

### Obstacles Not Announcing?
- [ ] Ensure camera feed is visible and working
- [ ] Check "🔍 Obstacle Detection Active" in status bar
- [ ] Move objects/people in front of camera
- [ ] Check backend console for detection errors

### Audio Clashing?
- [ ] Check console for `⚠️ Alert is playing, queueing instruction`
- [ ] Verify `✅ Critical alert sequence completed` appears
- [ ] Check that instructions have console: `Alert completed, resuming navigation`

---

## Key Timing Reference

| Event | Timing |
|-------|--------|
| Begin → Time announcement | ~2 seconds |
| Time announcement → First instruction | ~1 second |
| Standard obstacle cooldown | 5 seconds |
| Proximity alert cooldown | 10 seconds |
| Gap between 3x critical warnings | 2 seconds each |
| Obstacle detection cycle | 1 FPS (1000ms intervals) |

---

## Expected Announcement Examples

### Navigation Start
- "Navigation to canteen begins"
- "You will reach your destination in about 12 minutes"
- "Head walk straight towards parking for about 50 meters"

### Obstacle Detection
- Standard: "There is a person in front of you at about 0.8 meters away"
- Critical: "Warning obstacle ahead please stop" (×3 with gaps)

---

## Status Indicators

| Status | Meaning |
|--------|---------|
| ✅ Connected | Backend connected, ready |
| ❌ Offline | Backend unreachable |
| 📍 [location] | Current navigation destination |
| ⏱ ~X min | Estimated time remaining |
| 🔍 Obstacle Detection Active | Object detection running |

---

## File Locations

| Component | File |
|-----------|------|
| Frontend App | `frontend/src/components/Dashboard.js` |
| Backend API | `backend/api_routes.py` |
| Backend App | `backend/app.py` |
| Navigation Logic | `backend/modules/navigation.py` |
| Object Detection | `backend/modules/object_detection.py` |
| Styles | `frontend/src/App.css` |

---

## If Everything Fails

1. Stop both services (Ctrl+C in each terminal)
2. Clear browser cache (Ctrl+Shift+Del)
3. Restart backend: `python app.py`
4. Restart frontend: `npm start`
5. Open fresh browser tab to `http://localhost:3000`
6. Open console (F12) and check for errors
7. Follow Quick Test Sequence above

---

## Success Signal

✅ **You'll know it's working when:**
- [x] Welcome message plays on load
- [x] Navigation announcements in proper sequence (Begin → Time → First Instruction)
- [x] Swipe gestures work with console logging
- [x] Buttons respond immediately
- [x] Voice commands recognized
- [x] Obstacle detection announces: "There is a [X] at about [Y] meters"
- [x] Critical alert: "Warning obstacle ahead please stop" (×3 with gaps)
- [x] No audio overlapping or clashing
- [x] Professional, smooth experience

🎉 **All systems operational!**
