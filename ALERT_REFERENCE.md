# Quick Reference: Smart Obstacle Detection

## Distance Zones & Alert Behavior

### 🚨 CRITICAL ZONE (< 0.2m / < 20cm)
**What you say**: "Please stop [OBJECT] ahead, please stop [OBJECT] ahead, stop stop stop"
**Repeats**: 3 times with 2-second pauses
**Interrupts instruction**: YES (SAFETY)
**Cooldown**: 10 seconds
**Examples**:
- "Please stop person ahead, please stop person ahead, stop stop stop"
- "Please stop vehicle ahead, please stop vehicle ahead, stop stop stop"  
- "Please stop obstacle ahead, please stop obstacle ahead, stop stop stop"

### ⚠️ NEAR ZONE (0.2-0.3m / 20-30cm)
**What you say**: "[Object] about X.XX meters in front"
**Repeats**: 1 time only
**Interrupts instruction**: YES (too close)
**Cooldown**: 8 seconds or new object
**Examples**:
- "Person about 0.25 meters in front"
- "Car about 0.22 meters in front"
- "Table about 0.28 meters in front"

### 📍 DISTANT ZONE (0.3-5m / 30cm-5m)
**What you say**: "[Object] detected about X.X meters away"
**When said**: AFTER current instruction finishes (queued)
**Repeats**: 1 time only
**Interrupts instruction**: NO (queued until instruction ends)
**Examples**:
- "Chair detected about 1.5 meters away"
- "Person detected about 2.3 meters away"
- "Bicycle detected about 0.8 meters away"

### ✅ SAFE ZONE (> 5m)
**What you say**: Nothing (silent)
**Alert**: No alert needed

## When Obstacles Are Announced

```
Scenario 1: During First Instruction
┌─────────────────────────────────┐
│ "Walk straight 20 meters..."    │ ← DETECTION PAUSED (no obstacles announced)
└─────────────────────────────────┘
         (instruction finishes)
              ↓
         Detection resumes
         Next instruction plays

Scenario 2: Critical During Navigation
┌─────────────────────────────────┐
│ "Turn right at intersection..." │ ← INTERRUPTED by critical alert
└─────────────────────────────────┘
              ↓
┌─────────────────────────────────┐
│ "Please stop person ahead..." ×3│ ← Critical warning (3 times)
└─────────────────────────────────┘
              ↓
┌─────────────────────────────────┐
│ "Turn right at intersection..." │ ← Instruction resumes
└─────────────────────────────────┘

Scenario 3: Distant During Navigation
┌─────────────────────────────────┐
│ "Walk straight 50 meters..."    │ ← Obstacle detected & QUEUED
└─────────────────────────────────┘
         (instruction finishes)
              ↓
┌─────────────────────────────────┐
│ "Chair detected 1.5 meters away"│ ← Queued alert announced
└─────────────────────────────────┘
              ↓
┌─────────────────────────────────┐
│ "Now turn left at door..."      │ ← Next instruction
└─────────────────────────────────┘
```

## Alert Message Format

### Critical Alerts
- **Format**: "Please stop [OBJECT] ahead, please stop [OBJECT] ahead, stop stop stop"
- **Object types**:
  - If `person` → "person ahead"
  - If `car`, `motorcycle`, `bus`, `truck` → "vehicle ahead"
  - Else → "obstacle ahead"
- **Example**: "Please stop person ahead, please stop person ahead, stop stop stop"

### Near Alerts  
- **Format**: "[OBJECT] about [DISTANCE] meters in front"
- **Object**: First letter capitalized
- **Distance**: Two decimal places (X.XX)
- **Example**: "Person about 0.25 meters in front"

### Distant Alerts
- **Format**: "[OBJECT] detected about [DISTANCE] meters away"
- **Object**: First letter capitalized
- **Distance**: One decimal place if > 1m (1.5), two decimals if < 1m (0.8)
- **Example**: "Chair detected about 1.5 meters away"

## Distance Calibration

**Focal Length**: 800 pixels (improved from 600)
**Min Detection**: 0.1m (very close)
**Max Detection**: 50m (far away)
**Accuracy Correction**: Applied for objects < 1m

### Real-World Object Widths
- person: 0.5m
- car: 1.8m
- bicycle: 0.6m
- dog: 0.6m
- chair: 0.4m
- table: 1.0m
- potted plant: 0.5m
- tree: 1.0m

## Implementation Files Changed

**Backend**: `backend/vision/distance.py`
- Focal length: 600 → 800
- Thresholds: 0.1-0.2m, 0.2-0.3m, 0.3-5m, 5m+

**Frontend**: `frontend/src/components/Dashboard.js`
- State: `isFirstInstructionSpeaking`
- Ref: `pendingDistantAlertRef`
- Logic: 3-tier alerts + first instruction protection + queuing

## Testing Checklist

- [ ] **First instruction**: Obstacles NOT announced during first instruction
- [ ] **Critical alert**: Hand < 20cm away → Hears 3x warning immediately
- [ ] **Near alert**: Hand 20-30cm away → Hears single announcement
- [ ] **Distant alert**: Hand 1-5m away → Announcement queued until instruction ends
- [ ] **Message accuracy**: Correct distance shown (X.XX or X.X format)
- [ ] **Object type**: Correct object name in alert ("person", "chair", etc.)
- [ ] **No interruption**: Distant alerts don't interrupt instructions
- [ ] **Instruction resume**: After alert, instruction resumes smoothly

---

**Version**: 1.0
**Last Updated**: January 11, 2026
**Status**: Ready for Testing ✅
