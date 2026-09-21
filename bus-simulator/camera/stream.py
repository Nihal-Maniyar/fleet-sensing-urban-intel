"""Camera and video stream capture sources.

Supports synthetic procedural road video generation with dynamic road defects,
as well as prerecorded MP4/AVI video files and live webcam capture.
"""

from __future__ import annotations

import logging
import math
import random
import time
from typing import Callable, List, Optional, Tuple

import cv2
import numpy as np

logger = logging.getLogger("actual_bus_simulator.camera")


class VideoStreamSource:
    """Base abstract video stream source."""

    def read(self) -> Tuple[bool, np.ndarray]:
        raise NotImplementedError

    def release(self) -> None:
        pass


class SyntheticDefect:
    """Represents a simulated defect on the road plane moving towards the bus camera."""

    def __init__(self, class_name: str = "POTHOLE", lane_offset: float = 0.0) -> None:
        self.class_name = class_name
        self.lane_offset = lane_offset  # -1.0 (left), 0.0 (center), +1.0 (right)
        self.progress = 0.0  # 0.0 (near horizon) to 1.1 (past camera)
        self.size_scale = random.uniform(0.8, 1.4)
        self.passed_camera = False


class SyntheticRoadStream(VideoStreamSource):
    """Procedural road video generator producing animated dashcam perspective footage.

    Renders perspective road lanes, asphalt texture, moving lane dashes, horizon,
    and defect objects (potholes, garbage) that approach the camera realistically.
    """

    def __init__(
        self,
        width: int = 640,
        height: int = 480,
        fps: int = 20,
        auto_spawn_interval_sec: float = 8.0,
        on_defect_pass_callback: Optional[Callable[[str], None]] = None,
    ) -> None:
        self.width = width
        self.height = height
        self.fps = fps
        self.auto_spawn_interval_sec = auto_spawn_interval_sec
        self.on_defect_pass_callback = on_defect_pass_callback

        self._frame_count = 0
        self._last_spawn_time = time.time()
        self._defects: List[SyntheticDefect] = []

        # Perspective geometry
        self.horizon_y = int(self.height * 0.45)

    def trigger_defect(self, class_name: str = "POTHOLE", lane_offset: float = 0.0) -> None:
        """Spawn a defect at the horizon moving towards the bus."""
        self._defects.append(SyntheticDefect(class_name=class_name, lane_offset=lane_offset))
        logger.info("Spawned synthetic %s on road lane", class_name)

    def read(self) -> Tuple[bool, np.ndarray]:
        """Generate and render next animated frame."""
        self._frame_count += 1
        now = time.time()

        # Auto spawn defects periodically if configured
        if self.auto_spawn_interval_sec > 0:
            if now - self._last_spawn_time >= self.auto_spawn_interval_sec:
                self._last_spawn_time = now
                offset = random.choice([-0.3, 0.0, 0.25])
                self.trigger_defect("POTHOLE", offset)

        frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)

        # 1. Sky & cityscape background above horizon
        frame[0:self.horizon_y, :] = (130, 115, 100)  # Urban sky tone
        cv2.rectangle(frame, (0, self.horizon_y - 25), (self.width, self.horizon_y), (80, 75, 70), -1)

        # 2. Road surface below horizon (dark asphalt)
        frame[self.horizon_y:self.height, :] = (48, 50, 54)

        # Perspective road trapezoid
        top_left = (int(self.width * 0.38), self.horizon_y)
        top_right = (int(self.width * 0.62), self.horizon_y)
        bottom_left = (int(self.width * 0.05), self.height)
        bottom_right = (int(self.width * 0.95), self.height)

        road_pts = np.array([top_left, top_right, bottom_right, bottom_left], dtype=np.int32)
        cv2.fillPoly(frame, [road_pts], (42, 44, 46))

        # Lane boundary lines (white)
        cv2.line(frame, top_left, bottom_left, (210, 210, 215), 3, cv2.LINE_AA)
        cv2.line(frame, top_right, bottom_right, (210, 210, 215), 3, cv2.LINE_AA)

        # Center dashed yellow divider line with motion scroll
        center_top = (int(self.width * 0.5), self.horizon_y)
        center_bottom = (int(self.width * 0.5), self.height)

        scroll_offset = (self._frame_count * 12) % 60
        for y_dash in range(self.horizon_y + scroll_offset, self.height, 60):
            # Scale dash width by perspective depth
            depth_frac = (y_dash - self.horizon_y) / (self.height - self.horizon_y)
            dash_h = max(4, int(25 * depth_frac))
            dash_w = max(2, int(4 * depth_frac))
            cv2.rectangle(
                frame,
                (int(self.width * 0.5 - dash_w), y_dash),
                (int(self.width * 0.5 + dash_w), min(self.height, y_dash + dash_h)),
                (0, 200, 240),
                -1,
            )

        # 3. Update and render dynamic road defects
        speed_delta = 0.025  # Progress increment per frame
        active_defects: List[SyntheticDefect] = []

        for defect in self._defects:
            defect.progress += speed_delta

            if defect.progress > 1.0:
                if not defect.passed_camera:
                    defect.passed_camera = True
                    if self.on_defect_pass_callback:
                        self.on_defect_pass_callback(defect.class_name)
                # Let it roll off screen
                if defect.progress < 1.15:
                    active_defects.append(defect)
                continue

            active_defects.append(defect)

            # Quadratic perspective scaling (objects expand rapidly as they get closer)
            p = defect.progress
            screen_y = int(self.horizon_y + (self.height - self.horizon_y) * (p ** 1.6))

            # Perspective X position
            road_w_at_y = (top_right[0] - top_left[0]) + (bottom_right[0] - bottom_left[0] - (top_right[0] - top_left[0])) * p
            center_x = self.width * 0.5 + (road_w_at_y * 0.35 * defect.lane_offset)

            # Defect dimensions
            defect_w = int(max(15, (85 * (p ** 1.3)) * defect.size_scale))
            defect_h = int(max(8, (45 * (p ** 1.3)) * defect.size_scale))

            # Draw defect graphic
            if defect.class_name == "POTHOLE":
                # Dark depressive cavity with jagged shadow outline
                cavity_color = (18, 18, 20)
                rim_color = (10, 10, 12)
                cv2.ellipse(
                    frame,
                    (int(center_x), screen_y),
                    (defect_w // 2, defect_h // 2),
                    0,
                    0,
                    360,
                    cavity_color,
                    -1,
                )
                cv2.ellipse(
                    frame,
                    (int(center_x), screen_y),
                    (defect_w // 2, defect_h // 2),
                    0,
                    0,
                    360,
                    rim_color,
                    2,
                )
                # Internal texture/cracks
                if p > 0.4:
                    cv2.line(
                        frame,
                        (int(center_x - defect_w * 0.3), screen_y),
                        (int(center_x + defect_w * 0.2), screen_y + 2),
                        (8, 8, 10),
                        1,
                    )
            elif defect.class_name == "GARBAGE":
                # Waste pile
                cv2.rectangle(
                    frame,
                    (int(center_x - defect_w // 2), screen_y - defect_h // 2),
                    (int(center_x + defect_w // 2), screen_y + defect_h // 2),
                    (80, 140, 110),
                    -1,
                )

        self._defects = active_defects

        return True, frame


class OpenCVFileStream(VideoStreamSource):
    """Reads from a video file (.mp4, .avi) or hardware webcam index."""

    def __init__(self, source: str | int) -> None:
        self.source = source
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            raise RuntimeError(f"Could not open video source: {source}")

    def read(self) -> Tuple[bool, np.ndarray]:
        ret, frame = self.cap.read()
        if not ret:
            # If video file ended, loop back to beginning
            self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            ret, frame = self.cap.read()
        return ret, frame

    def release(self) -> None:
        if self.cap:
            self.cap.release()
