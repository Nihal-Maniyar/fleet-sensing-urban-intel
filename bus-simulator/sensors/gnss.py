"""GNSS/NavIC satellite receiver and road alignment simulator.

Traverses authentic Pune road corridors, calculates heading, road-aligned coordinates,
and adds realistic GNSS satellite noise while preserving raw vs snapped coordinates separately.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass
class Waypoint:
    latitude: float
    longitude: float
    name: str
    order: int


@dataclass
class PuneRouteCorridor:
    route_id: str
    name: str
    waypoints: List[Waypoint]

    def total_distance_meters(self) -> float:
        total = 0.0
        for i in range(len(self.waypoints) - 1):
            total += haversine_distance(
                self.waypoints[i].latitude,
                self.waypoints[i].longitude,
                self.waypoints[i + 1].latitude,
                self.waypoints[i + 1].longitude,
            )
        return total


FC_ROAD = PuneRouteCorridor(
    route_id="ROUTE-PUNE-FC",
    name="FC Road Corridor",
    waypoints=[
        Waypoint(18.5158, 73.8418, "Deccan Gymkhana", 1),
        Waypoint(18.5196, 73.8436, "Goodluck Chowk (Pothole Hotspot)", 2),
        Waypoint(18.5235, 73.8415, "FC Main Gate", 3),
        Waypoint(18.5278, 73.8424, "Dnyaneshwar Paduka Chowk", 4),
        Waypoint(18.5320, 73.8450, "Agriculture College", 5),
    ],
)

JM_ROAD = PuneRouteCorridor(
    route_id="ROUTE-PUNE-JM",
    name="JM Road Corridor",
    waypoints=[
        Waypoint(18.5222, 73.8493, "Balgandharva", 1),
        Waypoint(18.5255, 73.8500, "Sambhaji Park Crossing", 2),
        Waypoint(18.5280, 73.8510, "Modern High School", 3),
        Waypoint(18.5325, 73.8525, "Sancheti Hospital Chowk", 4),
    ],
)

KARVE_ROAD = PuneRouteCorridor(
    route_id="ROUTE-PUNE-KARVE",
    name="Karve Road Corridor",
    waypoints=[
        Waypoint(18.5135, 73.8385, "Deccan Corner", 1),
        Waypoint(18.5110, 73.8325, "Garware College", 2),
        Waypoint(18.5085, 73.8268, "Nal Stop (Tunnel/Offline Test Zone)", 3),
        Waypoint(18.5060, 73.8210, "Paud Phata", 4),
    ],
)

SHIVAJI_ROAD = PuneRouteCorridor(
    route_id="ROUTE-PUNE-SHIVAJI",
    name="Shivaji Road Central Corridor",
    waypoints=[
        Waypoint(18.5018, 73.8580, "Swargate Bus Station", 1),
        Waypoint(18.5165, 73.8562, "Dagdusheth Ganpati", 2),
        Waypoint(18.5218, 73.8540, "PMC Central HQ", 3),
        Waypoint(18.5328, 73.8550, "Shivajinagar Station", 4),
    ],
)

PUNE_ROUTES: Dict[str, PuneRouteCorridor] = {
    "ROUTE-PUNE-FC": FC_ROAD,
    "ROUTE-PUNE-JM": JM_ROAD,
    "ROUTE-PUNE-KARVE": KARVE_ROAD,
    "ROUTE-PUNE-SHIVAJI": SHIVAJI_ROAD,
}


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance in meters between two WGS84 positions."""
    r = 6371000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * r * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Bearing in degrees from point 1 to point 2."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dlambda = math.radians(lon2 - lon1)
    y = math.sin(dlambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(dlambda)
    deg = math.degrees(math.atan2(y, x))
    return (deg + 360.0) % 360.0


class GNSSSimulator:
    """Simulates bus movement along a route corridor and produces raw and road-aligned GNSS."""

    def __init__(
        self,
        route_id: str = "ROUTE-PUNE-FC",
        speed_kmh: float = 35.0,
        noise_std_meters: float = 4.0,
    ) -> None:
        self.route = PUNE_ROUTES.get(route_id, FC_ROAD)
        self.route_id = self.route.route_id
        self.speed_kmh = speed_kmh
        self.noise_std_meters = noise_std_meters

        self.current_segment: int = 0
        self.segment_progress: float = 0.0  # 0.0 to 1.0
        self.current_lat: float = self.route.waypoints[0].latitude
        self.current_lon: float = self.route.waypoints[0].longitude
        self.heading: float = 0.0

    def step(self, dt_seconds: float = 0.1) -> Tuple[float, float, float, float, float]:
        """Advance bus along the route segment.

        Returns:
            Tuple: (raw_latitude, raw_longitude, road_aligned_latitude, road_aligned_longitude, heading_degrees)
        """
        wps = self.route.waypoints
        if self.current_segment >= len(wps) - 1:
            # Wrap around route for continuous operation
            self.current_segment = 0
            self.segment_progress = 0.0

        p1 = wps[self.current_segment]
        p2 = wps[self.current_segment + 1]

        seg_distance = haversine_distance(p1.latitude, p1.longitude, p2.latitude, p2.longitude)
        speed_ms = (self.speed_kmh * 1000.0) / 3600.0
        step_distance = speed_ms * dt_seconds

        if seg_distance > 0:
            self.segment_progress += step_distance / seg_distance

        if self.segment_progress >= 1.0:
            self.segment_progress = 0.0
            self.current_segment += 1
            if self.current_segment >= len(wps) - 1:
                self.current_segment = 0
            p1 = wps[self.current_segment]
            p2 = wps[self.current_segment + 1]

        # Calculate exact road-aligned coordinates via linear interpolation
        frac = max(0.0, min(1.0, self.segment_progress))
        road_lat = p1.latitude + frac * (p2.latitude - p1.latitude)
        road_lon = p1.longitude + frac * (p2.longitude - p1.longitude)
        self.heading = calculate_bearing(p1.latitude, p1.longitude, p2.latitude, p2.longitude)

        # Add Gaussian satellite noise for raw GNSS measurement
        lat_noise_deg = (random.gauss(0, self.noise_std_meters) / 111320.0)
        lon_noise_deg = (random.gauss(0, self.noise_std_meters) / (111320.0 * math.cos(math.radians(road_lat))))

        raw_lat = road_lat + lat_noise_deg
        raw_lon = road_lon + lon_noise_deg

        self.current_lat = raw_lat
        self.current_lon = raw_lon

        return raw_lat, raw_lon, road_lat, road_lon, self.heading
