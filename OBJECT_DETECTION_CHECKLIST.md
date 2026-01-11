# Object Detection Verification Checklist

## Setup (Do This First)

- [ ] **Install missing dependencies**
  ```bash
  cd C:\Projects\Vision_Assistant\backend
  pip install ultralytics flask-cors
  ```

- [ ] **Verify YOLO model exists**
  - File: `C:\Projects\Vision_Assistant\backend\yolov8n.pt` (should exist)

- [ ] **Start Backend Server**
  ```bash
  cd C:\Projects\Vision_Assistant\backend
  python app.py
  ```
  Look for these messages:
  - ✅ "Models loading..."
  - ✅ "Models loaded successfully" 
  - ✅ "* Running on http://localhost:5000"

- [ ] **Start Frontend (new terminal)**
  ```bash
  cd C:\Projects\Vision_Assistant\frontend
  npm start
  ```

## Verification Steps

### 1. Backend Health Check
- [ ] Open browser at http://localhost:3000
- [ ] Open DevTools (F12) → Console tab
- [ ] Should see: "✅ Connected to server"
- [ ] Should see: "🏥 Backend health: { status: 'ok' }"

### 2. Camera Initialization
- [ ] Browser asks for camera permission → **Click Allow**
- [ ] Wait 2-3 seconds
- [ ] Should see in console:
  - "📹 Camera metadata loaded: 1280x720"
  - "🎥 Camera stream started playing"

### 3. Start Navigation
- [ ] Say "canteen" or click any destination button
- [ ] You should hear navigation announcement
- [ ] Look for in console: "🟢 Starting obstacle detection loop (every 1 second)"

### 4. Verify Detection Loop Running
- [ ] Every 1-2 seconds you should see:
  ```
  📸 Sending frame to detection API (1280x720)...
  📊 Detection result: X objects detected
  ```
- [ ] X is a number (0 or more)

### 5. Test with Obstacles
- [ ] Wave your hand in front of camera
- [ ] Should hear: "There is a hand in front of you at about X meters away"
- [ ] Look for in console: "⚠️ OBSTACLE ALERT: There is a hand..."
- [ ] Wait 7 seconds without moving hand
- [ ] Should hear announcement again (same object, 7 second update)

### 6. Test Critical Alert
- [ ] Move your hand VERY CLOSE to camera (less than 20cm)
- [ ] Should hear 3 times: "Warning obstacle ahead please stop"
- [ ] Wait 2 seconds between each warning
- [ ] Look for: "🚨🚨🚨 CRITICAL PROXIMITY ALERT"

### 7. Test Instruction Resume
- [ ] While navigating, trigger an obstacle alert
- [ ] After alert finishes (3 warnings or 1 announcement)
- [ ] **CRITICAL VERIFICATION**: Navigation instruction should automatically resume
- [ ] You should hear the direction/turn info again without having to ask for next step
- [ ] Look for in console: "▶️ Resuming instruction: ..."

## Troubleshooting

### Problem: No detection output in console
**Check**:
1. Is backend running? (should see "Running on http://localhost:5000")
2. Did you allow camera permission? (browser should ask)
3. Does DevTools show "🎥 Camera stream started playing"?

**Fix**:
- Restart backend: `Ctrl+C` then `python app.py`
- Refresh browser: `Ctrl+R`
- Check requirements installed: `pip list | grep -E "ultralytics|tensorflow"`

### Problem: Backend crashes when starting
**Check console for**:
```
ModuleNotFoundError: No module named 'ultralytics'
ImportError: No module named 'tensorflow'
```

**Fix**:
```bash
pip install -r requirements.txt
# Or specifically:
pip install ultralytics tensorflow opencv-python numpy flask flask-socketio flask-cors
```

### Problem: "Backend health check failed" message
**This means**:
- Backend is not accessible at http://localhost:5000
- Either not running OR running on different port

**Fix**:
1. Check backend terminal - is it running?
2. Check if port 5000 is in use: `netstat -ano | findstr :5000`
3. Kill process if needed and restart

### Problem: Alerts speak but don't resume instruction
**This means**:
- Alert logic is working
- Instruction resume logic not triggering

**Check**:
1. Console for "▶️ Resuming instruction:" after alert
2. If not there, check `pausedInstructionRef` in code (line ~120)
3. Verify `speak()` function has resume logic in `utterance.onend` (line ~165)

**Fix**:
- Refresh browser
- Restart backend
- Check for JavaScript errors in DevTools (red X's)

## Performance Expectations

| Metric | Expected | Actual |
|--------|----------|--------|
| Detection latency | 1-2 seconds | _______ |
| Alert announcement | < 1 second | _______ |
| Instruction resume | < 1 second | _______ |
| CPU usage | < 30% | _______ |
| Memory usage | < 200MB | _______ |

## Success Criteria

All of the following should be true:

- [ ] Object detection loop starts when navigation begins
- [ ] Frames are sent to backend every 1 second
- [ ] Backend returns detection results
- [ ] Obstacles within 0.2-5m trigger announcements
- [ ] Announcements happen every 5-10 seconds (updates)
- [ ] Critical obstacles (< 0.2m) trigger 3x warnings
- [ ] Instructions automatically resume after alerts
- [ ] Console shows detailed logging for everything
- [ ] No crashes or error messages
- [ ] Blind user can navigate safely with obstacle warnings

If all checks pass → **Object Detection is Working!** ✅

## Quick Restart Steps

```bash
# Terminal 1 - Backend
cd C:\Projects\Vision_Assistant\backend
python app.py

# Terminal 2 - Frontend  
cd C:\Projects\Vision_Assistant\frontend
npm start

# Browser: http://localhost:3000
# DevTools: F12 (check console)
```

---

**Last Updated**: January 11, 2026
**Status**: Ready for Testing
