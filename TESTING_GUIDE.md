# Quick Testing Guide - Enhanced Dashboard

## Before You Start
Make sure your backend is running:
```bash
cd backend
python app.py
```

And frontend:
```bash
cd frontend
npm start
```

## Test Scenario 1: Basic Navigation Flow
1. Dashboard loads
2. System asks: "Where would you like to go in your college?"
3. Say: **"canteen"**
4. Wait for route announcement
5. See popup with first instruction
6. ✅ Check: Obstacle Detection Status shows "🔍 Obstacle Detection Active"

## Test Scenario 2: Swipe Gestures
1. During navigation, look at popup
2. **Swipe UP** on the popup
   - Should get NEXT instruction
   - New text should appear
   - System should announce it
3. **Swipe DOWN** on the popup
   - Should get PREVIOUS instruction
   - Should go back to previous step
4. Check console logs:
   - Should see "⬆ Swiped Up - Next Instruction"
   - Should see "⬇ Swiped Down - Previous Instruction"

## Test Scenario 3: Button Navigation
1. During navigation, look at control buttons
2. Click **⬆ Prev** button
   - Should get previous instruction
   - Should announce it
3. Click **⬇ Next** button
   - Should get next instruction
   - Should announce it
4. Both should work without popup

## Test Scenario 4: Voice Commands
1. During navigation, say: **"next"**
   - Should get next instruction
   - Should show new instruction
2. Say: **"previous"**
   - Should get previous instruction
3. Check console:
   - Should see "📢 Voice command: Next"
   - Should see "📢 Voice command: Previous"

## Test Scenario 5: Obstacle Detection - Normal Distance
1. During navigation, move around
2. If object detected at 0.5-2 meters:
   - System announces: "There is a [OBJECT] in front of you at about X.X meters away"
   - Example: "There is a chair in front of you at about 0.5 meters away"
3. After announcement, wait 5 seconds
4. Same object won't announce again (cooldown protection)
5. Different object after 5s will announce
6. Check console:
   - "⚠️ ALERT: There is a [OBJECT]..."

## Test Scenario 6: Proximity Warning - Critical Distance (< 0.2m)
1. Move very close to object (< 0.2m)
2. System announces: **"Person too close, person too close, stop, stop, stop"**
   - Only announced ONCE
   - Won't repeat for 10 seconds
3. Check console:
   - "🚨 CRITICAL: Obstacle too close!"
4. After 10 seconds, if still close, will announce again

## Test Scenario 7: Alert Pause Behavior
1. During navigation with instruction playing
2. If obstacle detected:
   - Current instruction announcement stops
   - Alert plays instead
   - After alert, instruction can resume
3. Check console:
   - "⚠️ Alert is playing, queueing instruction" (if timed right)
   - "Alert completed, resuming instructions"

## Test Scenario 8: No Alert Repetition
1. Stay near same object for 6+ seconds
2. First announcement at 0s
3. Cooldown active from 0-5 seconds (no repeat)
4. After 5 seconds, if still detecting:
   - New detection can trigger new announcement
   - But same object type won't announce again immediately
5. Verify in console timestamps

## Test Scenario 9: Multi-Modal Interaction
1. Try DIFFERENT input methods in sequence:
   - Swipe UP (gesture)
   - Click Next button
   - Say "next" (voice)
   - Say "previous" (voice)
   - Swipe DOWN (gesture)
2. All should work without conflicts
3. No UI glitches
4. Smooth transitions between inputs

## Test Scenario 10: Stop Navigation
1. Click **⏹ Stop** button
2. Obstacle detection should stop
3. Status bar should remove "🔍 Obstacle Detection Active"
4. System should ask: "Navigation stopped. Where would you like to go?"
5. Should be able to say new destination

## Console Logging Checklist

Look for these logs in browser console (F12):

**On Navigation Start:**
```
✅ Connected to server
🎤 Starting listening...
Navigation started: [instruction text]
```

**On Gesture Input:**
```
⬆ Swiped Up - Next Instruction
⬇ Swiped Down - Previous Instruction
Next instruction: [text]
Previous instruction: [text]
```

**On Voice Input:**
```
🎤 You said: "[text]"
📢 Voice command: Next
📢 Voice command: Previous
```

**On Obstacle Detection:**
```
⚠️ ALERT: There is a [object] in front of you at about X.X meters away
🚨 CRITICAL: Obstacle too close!
Alert completed, resuming instructions
```

**On Navigation Stop:**
```
Navigation stopped. Where would you like to go?
```

## Timing Expectations

| Action | Time | Notes |
|--------|------|-------|
| Route announcement | 2-3 sec | Varies by text length |
| Popup appears | After announcement | Clear visible transition |
| Swipe detection | Immediate | 50px+ movement required |
| Obstacle detection cycle | 1 second | Every 1000ms |
| Alert cooldown (normal) | 5 seconds | Between different objects |
| Alert cooldown (critical) | 10 seconds | Proximity warnings |
| Voice recognition | 0-2 sec | After speech ends |
| Instruction announcement | 1-3 sec | Depends on text length |

## Common Issues & Solutions

### Swipe Not Working
- Make sure you're swiping ON the popup area
- Minimum swipe distance: 50px vertically
- Check console for "⬆ Swiped Up" or "⬇ Swiped Down" logs

### Buttons Not Responding
- Make sure navigation is active (isNavigating = true)
- Check if alert is playing (might pause instruction)
- Try clicking again after alert finishes

### No Obstacle Alerts
- Check camera permission granted
- Verify objects in view
- Check browser console for detection errors
- Make sure navigation is active

### Overlapping Audio
- If you hear mixed audio, wait for current speech to finish
- Audio should never overlap - one at a time
- Check `isPlayingAlertRef` in code if modifying

### Voice Commands Not Working
- Say keywords: "next", "previous", "back"
- Wait for system to finish speaking first
- Check microphone permission
- Look for "🎤 You said:" in console

## Performance Tips

- Keep browser devtools closed (unless debugging)
- Close other tabs using microphone/camera
- Good lighting for object detection
- Smooth, steady hand movements for gestures
- Normal speaking voice (not too soft)

## Success Indicators

✅ Dashboard loads without errors
✅ Welcome message plays
✅ Can say destination
✅ Route announcement plays
✅ Popup appears with instruction
✅ Swipe gestures work
✅ Buttons respond
✅ Voice commands recognized
✅ Obstacles announced clearly
✅ No overlapping audio
✅ Alerts have proper cooldowns
✅ Can navigate full instruction set
✅ Stop button works
✅ Can restart with new destination
