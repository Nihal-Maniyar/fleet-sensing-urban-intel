"""6-DOF IMU (Inertial Measurement Unit) sensor simulation.

Provides 3-axis accelerometer and 3-axis gyroscope readings with realistic road
vibration, cornering loads, and physical shock spikes when passing over road defects.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class IMUReading:
    """IMU 6-DOF sensor sample."""

    ax: float  # Longitudinal acceleration (m/s^2)
    ay: float  # Lateral acceleration (m/s^2)
    az: float  # Vertical acceleration (m/s^2, gravity ~ 9.81)
    gx: float  # Roll rate (deg/s)
    gy: float  # Pitch rate (deg/s)
    gz: float  # Yaw rate (deg/s)
    shock_detected: bool = False
    timestamp: Optional[str] = None


class IMUSimulator:
    """Simulates vehicle dynamics and accelerometer shocks upon pothole impact."""

    def __init__(self, sample_rate_hz: float = 20.0) -> None:
        self.sample_rate_hz = sample_rate_hz
        self._shock_active: bool = False
        self._shock_frames_left: int = 0
        self._shock_amplitude: float = 0.0

    def trigger_shock(self, intensity_g: float = 2.2) -> None:
        """Trigger an impact shock (e.g. bus wheel striking a pothole)."""
        self._shock_active = True
        self._shock_frames_left = int(self.sample_rate_hz * 0.4)  # 400ms decay
        self._shock_amplitude = intensity_g * 9.81

    def step(self, speed_kmh: float = 35.0, steering_angle_deg: float = 0.0) -> IMUReading:
        """Advance IMU sensor state and produce reading."""
        now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

        # Baseline vehicle forces
        # Gravity along vertical Z axis (~9.81 m/s^2)
        base_az = 9.81

        # Surface micro-roughness vibration proportional to vehicle speed
        speed_factor = max(0.1, speed_kmh / 50.0)
        vibration_z = random.gauss(0, 0.15 * speed_factor)
        vibration_x = random.gauss(0, 0.08 * speed_factor)
        vibration_y = random.gauss(0, 0.08 * speed_factor)

        # Lateral acceleration from steering/turns: a_y = v^2 / R
        v_ms = (speed_kmh * 1000.0) / 3600.0
        turn_ay = math.radians(steering_angle_deg) * (v_ms ** 2) * 0.05

        ax = vibration_x
        ay = turn_ay + vibration_y
        az = base_az + vibration_z

        gx = random.gauss(0, 0.2)
        gy = random.gauss(0, 0.2)
        gz = steering_angle_deg * 0.8 + random.gauss(0, 0.1)

        shock_flag = False
        if self._shock_active and self._shock_frames_left > 0:
            # Damped oscillatory decay for pothole impact
            decay = self._shock_frames_left / (self.sample_rate_hz * 0.4)
            freq = self._shock_frames_left * 1.5
            shock_z = self._shock_amplitude * decay * math.cos(freq)
            shock_pitch = (self._shock_amplitude / 9.81) * 8.0 * decay * math.sin(freq)

            az += shock_z
            gy += shock_pitch
            shock_flag = True

            self._shock_frames_left -= 1
            if self._shock_frames_left <= 0:
                self._shock_active = False

        return IMUReading(
            ax=round(ax, 3),
            ay=round(ay, 3),
            az=round(az, 3),
            gx=round(gx, 2),
            gy=round(gy, 2),
            gz=round(gz, 2),
            shock_detected=shock_flag,
            timestamp=now_utc,
        )
