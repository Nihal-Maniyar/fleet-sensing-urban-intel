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
        Waypoint(18.51595, 73.84207, "Deccan Gymkhana", 1),
        Waypoint(18.51601, 73.84204, "FC_WP_2", 2),
        Waypoint(18.51606, 73.84203, "FC_WP_3", 3),
        Waypoint(18.51607, 73.84202, "FC_WP_4", 4),
        Waypoint(18.5161, 73.84199, "FC_WP_5", 5),
        Waypoint(18.51619, 73.84197, "FC_WP_6", 6),
        Waypoint(18.51631, 73.84193, "FC_WP_7", 7),
        Waypoint(18.51643, 73.84189, "FC_WP_8", 8),
        Waypoint(18.51669, 73.84181, "FC_WP_9", 9),
        Waypoint(18.51696, 73.84174, "FC_WP_10", 10),
        Waypoint(18.51724, 73.84168, "FC_WP_11", 11),
        Waypoint(18.5175, 73.84163, "FC_WP_12", 12),
        Waypoint(18.51757, 73.84162, "FC_WP_13", 13),
        Waypoint(18.5183, 73.84149, "FC_WP_14", 14),
        Waypoint(18.51836, 73.84148, "FC_WP_15", 15),
        Waypoint(18.51898, 73.84139, "FC_WP_16", 16),
        Waypoint(18.51907, 73.84137, "FC_WP_17", 17),
        Waypoint(18.51935, 73.84131, "FC_WP_18", 18),
        Waypoint(18.51957, 73.84128, "Goodluck Chowk (Pothole Hotspot)", 19),
        Waypoint(18.51993, 73.84124, "FC_WP_20", 20),
        Waypoint(18.52042, 73.84117, "FC_WP_21", 21),
        Waypoint(18.52054, 73.84116, "FC_WP_22", 22),
        Waypoint(18.52073, 73.84114, "FC_WP_23", 23),
        Waypoint(18.52105, 73.84108, "FC_WP_24", 24),
        Waypoint(18.5211, 73.84107, "FC_WP_25", 25),
        Waypoint(18.52123, 73.84105, "FC_WP_26", 26),
        Waypoint(18.52132, 73.84104, "FC_WP_27", 27),
        Waypoint(18.52134, 73.84104, "FC_WP_28", 28),
        Waypoint(18.52198, 73.84097, "FC_WP_29", 29),
        Waypoint(18.52203, 73.84097, "FC_WP_30", 30),
        Waypoint(18.52263, 73.84095, "FC_WP_31", 31),
        Waypoint(18.52363, 73.84116, "FC Main Gate", 32),
        Waypoint(18.52457, 73.8414, "FC_WP_33", 33),
        Waypoint(18.52465, 73.84141, "FC_WP_34", 34),
        Waypoint(18.52481, 73.84146, "FC_WP_35", 35),
        Waypoint(18.52541, 73.84161, "FC_WP_36", 36),
        Waypoint(18.5255, 73.84163, "FC_WP_37", 37),
        Waypoint(18.52573, 73.8417, "FC_WP_38", 38),
        Waypoint(18.52591, 73.84175, "FC_WP_39", 39),
        Waypoint(18.52595, 73.84176, "FC_WP_40", 40),
        Waypoint(18.52636, 73.8419, "FC_WP_41", 41),
        Waypoint(18.52639, 73.84191, "FC_WP_42", 42),
        Waypoint(18.52658, 73.842, "FC_WP_43", 43),
        Waypoint(18.52691, 73.84221, "FC_WP_44", 44),
        Waypoint(18.52717, 73.84235, "FC_WP_45", 45),
        Waypoint(18.52735, 73.84243, "FC_WP_46", 46),
        Waypoint(18.5274, 73.84246, "Dnyaneshwar Paduka Chowk", 47),
        Waypoint(18.52743, 73.84248, "FC_WP_48", 48),
        Waypoint(18.52756, 73.84254, "FC_WP_49", 49),
        Waypoint(18.52801, 73.84278, "FC_WP_50", 50),
        Waypoint(18.52814, 73.84283, "FC_WP_51", 51),
        Waypoint(18.52821, 73.84288, "FC_WP_52", 52),
        Waypoint(18.52838, 73.84297, "FC_WP_53", 53),
        Waypoint(18.52874, 73.84316, "FC_WP_54", 54),
        Waypoint(18.52939, 73.84351, "FC_WP_55", 55),
        Waypoint(18.52972, 73.84368, "FC_WP_56", 56),
        Waypoint(18.52988, 73.84376, "FC_WP_57", 57),
        Waypoint(18.52994, 73.8438, "FC_WP_58", 58),
        Waypoint(18.53004, 73.84385, "FC_WP_59", 59),
        Waypoint(18.53032, 73.84401, "FC_WP_60", 60),
        Waypoint(18.53124, 73.84451, "Agriculture College", 61),
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
        Waypoint(18.5218, 73.8565, "PMC Central HQ", 3),
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
