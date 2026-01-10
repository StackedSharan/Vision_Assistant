**Vision Assistant — Tech Stack (One-Page Summary)**

- **Project:** Vision_Assistant
- **Purpose:** Real-time assistive navigation + obstacle detection using camera, maps and speech.

**Frontend**
- **Framework / Build:** React (CRA) — `react` ^19.2.0; scaffolded with `react-scripts` `5.0.1`.
- **Routing:** `react-router-dom` (`^7.9.6`) for SPA routes (`/`, `/dashboard`).
- **Mapping:** `leaflet` (`^1.9.4`) + `react-leaflet` (`^5.0.0`) for interactive maps and displaying GeoJSON routes.
- **Realtime client:** `socket.io-client` (`^4.8.1`) used to send/receive frames, navigation requests, and event messages to/from backend.
- **Testing & tooling:** `@testing-library/*` packages and `web-vitals` (testing helpers and performance metrics).
- **Notable files:** `frontend/src/App.js`, `frontend/src/components/MapComponent.js`, `frontend/data/map.geojson`, `frontend/package.json`.

**Backend**
- **Language / Framework:** Python + `Flask` (`Flask==3.1.2` in requirements) as primary web server.
- **Realtime / Websockets:** `Flask-SocketIO` / `python-socketio` for bidirectional socket events (frame streaming, alerts, navigation responses).
- **Computer Vision & ML:**
  - YOLOv8 via `ultralytics` (YOLOv8n weight present as `yolov8n.pt`) for object detection in `backend/app.py`.
  - TensorFlow / TFLite (`tensorflow==2.20.0`) used by a TFLite interpreter (`ssd_mobilenet_v2.tflite`) in `backend/modules/object_detection.py`.
  - OpenCV (`opencv-python` / `opencv-contrib-python==4.12.0.88`) and `numpy` for image preprocessing and I/O.
- **Navigation / Geo:** `geojson` + `geopy` for map parsing and geodesic distance; `networkx` (graph + Dijkstra) for pathfinding (`backend/modules/navigator.py`).
- **Speech & Audio:** Vosk (`vosk==0.3.45`) for offline ASR; `gTTS` for TTS generation; `sounddevice` for microphone capture. `backend/modules/voice_assistant.py` wraps these.
- **Data storage:** SQLite via `sqlite3` (DB file `backend/memory.db`) with `backend/init_db.py` and `backend/config.py` for config constants.
- **Notable backend files & models:**
  - `backend/app.py` — Flask + SocketIO entrypoint (frame processing, navigation endpoints).
  - `backend/modules/navigator.py`, `backend/modules/object_detection.py`, `backend/modules/voice_assistant.py`.
  - Models/data: `backend/yolov8n.pt`, `backend/models/ssd_mobilenet_v2.tflite`, `backend/models/model.tflite`, `backend/models/coco_labels.txt`, `backend/models/vosk-model-en/`, `backend/models/map.geojson`.

**Dependencies (high level)**
- Frontend: `react`, `react-dom`, `react-scripts`, `react-router-dom`, `leaflet`, `react-leaflet`, `socket.io-client`, `@testing-library/*`.
- Backend (selected): `Flask`, `Flask-SocketIO`, `python-socketio`, `numpy`, `opencv-contrib-python`, `tensorflow`, `ultralytics` (YOLO), `networkx`, `geopy`, `geojson`, `vosk`, `gTTS`, `sounddevice`, `gevent`, `requests`.

**Deployment & Runtime Notes**
- Real-time inference is CPU/GPU intensive: prefer machines with GPU (CUDA) for high frame-rate YOLO/TensorFlow inference.
- TensorFlow+ultralytics compatibility requires choosing a Python version supported by `tensorflow==2.20.0` — verify on target environment.
- `gTTS` generates MP3s that are played via OS commands; ensure platform audio player is available (e.g., `mpg123` on Linux).
- For reproducible installs: use `pip install -r requirements.txt` (repo root or `backend/requirements.txt`) and `npm install` inside `frontend/`.

**Quick run (dev)**
1. Backend (from project root):
```bash
python -m pip install -r backend/requirements.txt
python backend/app.py
```
2. Frontend (from `frontend/`):
```bash
npm install
npm start
```

**Key files to reference in report**
- Backend entry: `backend/app.py`
- Navigator: `backend/modules/navigator.py`
- Object detection (TFLite): `backend/modules/object_detection.py`
- Voice assistant: `backend/modules/voice_assistant.py`
- Frontend entry: `frontend/src/App.js`, mapping: `frontend/src/components/MapComponent.js`, `frontend/data/map.geojson`.

**Recommendation**
- Pin `ultralytics`/YOLO version in backend requirements for reproducible installs; consider adding a short `TECH_STACK.md` (or use this file) to the repo root.

-- End of one-page summary --
