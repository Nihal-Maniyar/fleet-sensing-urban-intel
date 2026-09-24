# Pothole Video Detection & Tracking Prototype (Phase 1)

A complete local AI-powered road video processing pipeline for detecting, tracking, and logging potholes. Built with **Ultralytics YOLOv8**, **ByteTrack**, and a custom **Persistent Incident Manager**.

---

## 1. Project Purpose

Road surface anomalies (potholes) present significant safety hazards and damage vehicles. This prototype processes dashcam or vehicle inspection video to:
- Detect potholes frame-by-frame with high precision.
- Track the physical movement of each pothole across consecutive video frames using ByteTrack.
- Prevent duplicate reporting: multiple frames showing the same physical pothole are consolidated into a single unique **Incident**.
- Export an annotated demonstration video and a structured JSON incident report for integration with city municipal systems.

---

## 2. Pipeline Architecture

```text
INPUT VIDEO (e.g., input/road_video.mp4)
      ↓
OPENCV FRAME EXTRACTION & VALIDATION
      ↓
YOLOv8 POTHOLE DETECTION (models/best.pt)
      ↓
BYTETRACK OBJECT TRACKING (Unique Track IDs)
      ↓
INCIDENT MANAGER (Filters persistent detections ≥ 3 frames)
      ↓
OUTPUT GENERATION:
  ├── ANNOTATED VIDEO (output/pothole_detection.mp4)
  └── INCIDENT LOG (output/incidents.json)
```

---

## 3. Environment & Prerequisites

- **Operating System:** Windows 10 / 11
- **Python Version:** Python 3.10, 3.11, or 3.13 (Python 3.10+ recommended)
- **Hardware Acceleration:** NVIDIA GPU with CUDA supported (falls back automatically to CPU if unavailable).

---

## 4. Setup Instructions (Windows)

Open **PowerShell** or **Command Prompt** in the project root directory:

### Step 1: Create Virtual Environment
```powershell
python -m venv venv
```

### Step 2: Activate the Virtual Environment
On Windows PowerShell:
```powershell
.\venv\Scripts\Activate.ps1
```
*(If you encounter execution policy restrictions, run: `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`)*

Or in Command Prompt (cmd):
```cmd
venv\Scripts\activate.bat
```

### Step 3: Install Requirements
```powershell
pip install -r requirements.txt
```

---

## 5. Model Configuration (`best.pt`)

- **Model:** Pretrained YOLOv8 Pothole Detection Model
- **Hugging Face Repository:** [https://huggingface.co/Samdutse/pothole-yolov8](https://huggingface.co/Samdutse/pothole-yolov8)
- **Direct Download URL:** [https://huggingface.co/Samdutse/pothole-yolov8/resolve/main/best.pt](https://huggingface.co/Samdutse/pothole-yolov8/resolve/main/best.pt)
- **Expected Local Path:**
  ```
  models/best.pt
  ```

> **Note:** The pipeline includes automatic verification. If `models/best.pt` is missing, it will automatically attempt to download it directly from Hugging Face on the first run.

---

## 6. Input Video Placement

Place your input road / vehicle video at:
```
input/road_video.mp4
```

Supported formats: `.mp4`, `.avi`, `.mov`, `.mkv`.

---

## 7. How to Run the Pipeline

### Standard Execution (Default settings)
```powershell
python run.py
```
This automatically loads `models/best.pt`, processes `input/road_video.mp4`, and writes the outputs to `output/`.

### Custom Video Path
```powershell
python run.py --input input/my_drive.mp4
```

### Custom Confidence Threshold
```powershell
python run.py --confidence 0.50
```

### Pure Detection (Without Tracking)
```powershell
python run.py --no-tracking
```

### Force GPU or CPU
```powershell
python run.py --device cuda
# Or force CPU:
python run.py --device cpu
```

### Custom Incident Persistence Threshold
```powershell
# Require at least 5 consecutive frames before triggering an incident:
python run.py --min-frames 5
```

---

## 8. Tracking & Incident Generation Logic

### ByteTrack Tracking
- Ultralytics `tracker="bytetrack.yaml"` is utilized.
- Rather than assigning arbitrary new IDs on each frame, ByteTrack associates bounding boxes with the same pothole track ID across successive frames.

### Incident Consolidation
- A detection appearing on only 1 or 2 isolated frames (e.g. noise or false positive) does not trigger an incident.
- When a track persists for at least `MIN_CONSECUTIVE_FRAMES = 3`:
  - **Incident #N** is registered.
  - As the vehicle continues driving past the pothole, subsequent detections update the existing incident's `last_frame`, `detection_count`, and `confidence`.
  - **Result:** 1 physical pothole = **1 Incident Record** in `output/incidents.json`.

---

## 9. Output Files

### Annotated Output Video
Location:
```
output/pothole_detection.mp4
```
Contains:
- Original video resolution and framerate.
- Bounding boxes around detected potholes.
- Multi-line HUD label per detection:
  ```
  Pothole
  ID: 3
  Confidence: 0.87
  ```
- Top-left HUD information panel:
  ```
  POTHOLE DETECTION
  Frame: 120/1000
  FPS: 25.0
  Detected: 2
  Active Tracks: 2
  Unique Incidents: 1
  ```

### Incident JSON Log
Location:
```
output/incidents.json
```
Structure:
```json
{
    "total_incidents": 2,
    "incidents": [
        {
            "incident_id": 1,
            "track_id": 1,
            "confidence": 0.87,
            "first_frame": 120,
            "last_frame": 145,
            "video_timestamp": 4.83,
            "detection_count": 26
        }
    ]
}
```

---

## 10. CPU / GPU Behavior

- On startup, the system tests `torch.cuda.is_available()`.
- If an NVIDIA GPU with CUDA is present, it uses GPU acceleration (`Device: CUDA`).
- If no CUDA device is found, it falls back seamlessly to CPU (`Device: CPU`).
- CUDA is completely optional; the entire pipeline is 100% functional on CPU.

---

## 11. Troubleshooting

| Issue | Cause | Solution |
|---|---|---|
| `[ERROR] Input video not found at: input/road_video.mp4` | Video file has not been placed in `input/` folder yet | Copy your road recording into `input/road_video.mp4` |
| `[ERROR] Model file not found` / Download fails | Network proxy or firewall blocking Hugging Face | Manually download `best.pt` from [Hugging Face](https://huggingface.co/Samdutse/pothole-yolov8/resolve/main/best.pt) and place it into `models/best.pt` |
| `OpenCV cannot open video file` | Corrupt or invalid video format | Verify the file plays in Windows Media Player / VLC; convert to standard H.264 MP4 |
| `ExecutionPolicy` error when activating `venv` | Windows PowerShell default security policy | Run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` then activate `venv` |
| Low processing FPS on CPU | Video resolution is very high (e.g. 4K) | Downscale input video to 1080p or 720p for faster processing on CPU |
