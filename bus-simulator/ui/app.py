"""FastAPI web server serving the demonstration UI, live MJPEG video stream, and WebSocket telemetry.

Implements all demonstration UI requirements from docs/simulators.md and docs/architecture.md.
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

import cv2
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

try:
    from bus_instance import BusInstance
except ImportError:
    from ..bus_instance import BusInstance

logger = logging.getLogger("actual_bus_simulator.ui")


def create_app(bus_instance: BusInstance) -> FastAPI:
    """Create and configure FastAPI application bound to a specific BusInstance."""
    app = FastAPI(title=f"Actual Bus Simulator - {bus_instance.bus_id}")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    static_dir = Path(__file__).parent / "static"
    static_dir.mkdir(parents=True, exist_ok=True)

    # Mount runtime evidence directory so evidence snapshots can be viewed directly in browser
    evidence_dir = Path("runtime/evidence")
    evidence_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/evidence", StaticFiles(directory=str(evidence_dir)), name="evidence")

    @app.get("/", response_class=HTMLResponse)
    async def index() -> FileResponse:
        index_path = static_dir / "index.html"
        return FileResponse(str(index_path))

    @app.get("/video_feed")
    def video_feed() -> StreamingResponse:
        """Stream MJPEG frames showing video, YOLO bounding boxes, and ByteTrack IDs."""

        def frame_generator():
            while True:
                frame = bus_instance.latest_frame_annotated
                if frame is not None:
                    ret, buffer = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                    if ret:
                        frame_bytes = buffer.tobytes()
                        yield (
                            b"--frame\r\n"
                            b"Content-Type: image/jpeg\r\n\r\n" + frame_bytes + b"\r\n"
                        )
                # Cap MJPEG stream rate to ~20 FPS
                import time
                time.sleep(0.05)

        return StreamingResponse(
            frame_generator(),
            media_type="multipart/x-mixed-replace; boundary=frame",
        )

    @app.get("/api/telemetry")
    async def get_telemetry() -> Dict[str, Any]:
        """Fetch current telemetry state."""
        return {
            "bus_id": bus_instance.bus_id,
            "route_id": bus_instance.route_id,
            "connectivity_state": bus_instance.connectivity_state,
            "latitude": bus_instance.current_lat,
            "longitude": bus_instance.current_lon,
            "road_aligned_latitude": bus_instance.road_lat,
            "road_aligned_longitude": bus_instance.road_lon,
            "heading_degrees": bus_instance.heading,
            "speed_kmh": bus_instance.gnss.speed_kmh,
            "active_tracks_count": len(bus_instance.latest_tracks),
            "pending_outbox_count": bus_instance.outbox.count_pending(),
            "total_events": len(bus_instance.recent_events),
            "is_paused": bus_instance.is_paused,
            "imu": {
                "ax": bus_instance.latest_imu.ax if bus_instance.latest_imu else 0.0,
                "ay": bus_instance.latest_imu.ay if bus_instance.latest_imu else 0.0,
                "az": bus_instance.latest_imu.az if bus_instance.latest_imu else 9.81,
                "gx": bus_instance.latest_imu.gx if bus_instance.latest_imu else 0.0,
                "gy": bus_instance.latest_imu.gy if bus_instance.latest_imu else 0.0,
                "gz": bus_instance.latest_imu.gz if bus_instance.latest_imu else 0.0,
                "shock_detected": bus_instance.latest_imu.shock_detected if bus_instance.latest_imu else False,
            },
        }

    @app.get("/api/events")
    async def get_events() -> Dict[str, Any]:
        """Fetch list of recent contract events."""
        return {
            "events": [e.to_dict() for e in bus_instance.recent_events]
        }

    @app.post("/api/connectivity")
    async def set_connectivity(payload: Dict[str, str]) -> Dict[str, str]:
        """Set connectivity state ('ONLINE' or 'OFFLINE')."""
        state = payload.get("state", "ONLINE").upper()
        bus_instance.set_connectivity(state)
        return {"connectivity_state": bus_instance.connectivity_state}

    @app.post("/api/toggle_connectivity")
    async def toggle_connectivity() -> Dict[str, str]:
        """Toggle connectivity between ONLINE and OFFLINE."""
        new_state = bus_instance.toggle_connectivity()
        return {"connectivity_state": new_state}

    @app.post("/api/trigger_defect")
    async def trigger_defect(payload: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Trigger a defect on the road (pothole or garbage)."""
        cls_name = "POTHOLE"
        if payload and "class_name" in payload:
            cls_name = payload["class_name"].upper()
        bus_instance.trigger_defect(class_name=cls_name)
        return {"status": "triggered", "class_name": cls_name}

    @app.post("/api/trigger_shock")
    async def trigger_shock() -> Dict[str, str]:
        """Trigger an IMU physical shock spike."""
        bus_instance.trigger_shock(intensity_g=2.5)
        return {"status": "shock_triggered"}

    @app.post("/api/replay")
    async def replay_outbox() -> Dict[str, Any]:
        """Replay queued offline events from SQLite WAL outbox over MQTT."""
        count = bus_instance.replay_outbox()
        return {"replayed_count": count, "pending_count": bus_instance.outbox.count_pending()}

    @app.post("/api/toggle_pause")
    async def toggle_pause() -> Dict[str, bool]:
        """Pause or resume sensing pipeline."""
        bus_instance.is_paused = not bus_instance.is_paused
        return {"is_paused": bus_instance.is_paused}

    @app.websocket("/ws")
    async def websocket_telemetry(websocket: WebSocket) -> None:
        """Stream high-frequency live telemetry to client browser."""
        await websocket.accept()
        try:
            while True:
                telemetry = {
                    "bus_id": bus_instance.bus_id,
                    "route_id": bus_instance.route_id,
                    "connectivity_state": bus_instance.connectivity_state,
                    "latitude": round(bus_instance.current_lat, 6),
                    "longitude": round(bus_instance.current_lon, 6),
                    "road_aligned_latitude": round(bus_instance.road_lat, 6),
                    "road_aligned_longitude": round(bus_instance.road_lon, 6),
                    "heading_degrees": round(bus_instance.heading, 1),
                    "speed_kmh": round(bus_instance.gnss.speed_kmh, 1),
                    "active_tracks_count": len(bus_instance.latest_tracks),
                    "pending_outbox_count": bus_instance.outbox.count_pending(),
                    "total_events": len(bus_instance.recent_events),
                    "is_paused": bus_instance.is_paused,
                    "imu": {
                        "ax": bus_instance.latest_imu.ax if bus_instance.latest_imu else 0.0,
                        "ay": bus_instance.latest_imu.ay if bus_instance.latest_imu else 0.0,
                        "az": bus_instance.latest_imu.az if bus_instance.latest_imu else 9.81,
                        "gx": bus_instance.latest_imu.gx if bus_instance.latest_imu else 0.0,
                        "gy": bus_instance.latest_imu.gy if bus_instance.latest_imu else 0.0,
                        "gz": bus_instance.latest_imu.gz if bus_instance.latest_imu else 0.0,
                        "shock_detected": bus_instance.latest_imu.shock_detected if bus_instance.latest_imu else False,
                    },
                    "recent_events": [e.to_dict() for e in bus_instance.recent_events[:10]],
                }
                await websocket.send_text(json.dumps(telemetry))
                await asyncio.sleep(0.1)  # 10 Hz telemetry rate
        except WebSocketDisconnect:
            pass
        except Exception as e:
            logger.debug("WebSocket exception: %s", e)

    return app
