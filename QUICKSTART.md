# 🚀 AeroBrain Quick Start Guide

## 5-Minute Setup

### Step 1: Verify Setup (1 min)
```bash
cd "d:\Willovate Work\Drone_AI_Brain"
python setup_airsim.py
```
✅ You should see: "All checks passed! You're ready to run AeroBrain"

### Step 2: Start AirSim (2 min)
1. Download from: https://github.com/microsoft/AirSim/releases
2. Extract `AirSim.zip`
3. Run `AirSim.exe`
4. Wait for simulator to load (you should see a drone scene)

### Step 3: Run Your System (2 min)

**Option A: Autonomous Brain (Recommended)**
```bash
python drone_brain.py
```
You should see:
```
✅ Connected to AirSim
✅ Motors armed successfully
>>> Drone is hovering. Initiating AI Vision...
```

**Option B: Web Dashboard**
```bash
python app.py
```
Then open: http://localhost:5000 in your browser

---

## 🎯 First Flight Checklist

- [ ] AirSim.exe is running
- [ ] Virtual environment activated (`.venv`)
- [ ] All dependencies installed (`pip install -r requirements.txt`)
- [ ] `yolov8n.pt` model downloaded
- [ ] `setup_airsim.py` passed all checks
- [ ] Drone takes off and hovers in AirSim
- [ ] Camera feed appears in window

---

## 🔧 Custom Configuration

Open `config.py` and adjust:

```python
# Detection sensitivity (higher = more detections)
YOLO_CONFIDENCE = 0.4

# Movement speed (0.0 to 1.0)
PITCH_MAX_SPEED = 0.5

# Enable/disable features
USE_STATE_MACHINE = True
ENABLE_TRACKING = True
LOG_DETECTIONS = True
```

Then restart: `python drone_brain.py`

---

## 📊 Performance Optimization

### For Better FPS:
```python
FRAME_SKIP = 2              # Skip frames
YOLO_IMGSZ = 416            # Lower resolution
YOLO_CONFIDENCE = 0.5       # Fewer detections
```

### For Better Accuracy:
```python
FRAME_SKIP = 1              # Process all frames
YOLO_IMGSZ = 640            # Full resolution
YOLO_CONFIDENCE = 0.3       # More detections
```

---

## 🛑 Common Issues & Quick Fixes

### "Cannot connect to AirSim"
```bash
# Make sure AirSim.exe is running, then:
python drone_brain.py
```

### "YOLO model not found"
```bash
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt')"
```

### "Low FPS Performance"
- Set `FRAME_SKIP = 2` in config.py
- Set `YOLO_IMGSZ = 416`
- Reduce resolution

---

## 📈 Monitoring Your System

### Console Output
```
🎯 TARGET | ➔ EVADE RIGHT 30.0° | = HOLD DISTANCE | Area: 75000
🔍 SEARCHING FOR TARGET
```

### Web Dashboard
- Navigate to: http://localhost:5000
- See live video stream
- View real-time commands
- Monitor FPS

### Log File
```bash
# View logs
type aerobrain.log

# Watch live logs
Get-Content aerobrain.log -Wait
```

---

## 🎓 Next Steps

1. **Try different object classes** - Edit `config.py` to detect cars, bicycles, etc.
2. **Adjust sensitivity** - Tweak `YOLO_CONFIDENCE` for your environment
3. **Enable frame recording** - Set `SAVE_DEBUG_FRAMES = True`
4. **Add custom logic** - Modify `drone_brain.py` for your use case

---

## 📚 File Reference

| File | Purpose |
|------|---------|
| `drone_brain.py` | Main autonomous system |
| `app.py` | Web dashboard |
| `config.py` | All settings (edit this!) |
| `utils.py` | Helper utilities |
| `setup_airsim.py` | Setup verification |
| `README.md` | Full documentation |
| `requirements.txt` | Python packages |

---

## 🆘 Still Having Issues?

1. Run: `python setup_airsim.py` (will tell you what's wrong)
2. Check: `aerobrain.log` for error details
3. Verify: AirSim.exe is running
4. Reinstall packages: `pip install -r requirements.txt --force-reinstall`

---

**Ready to fly? Let's go!** 🚁✈️

Next: `python drone_brain.py`
