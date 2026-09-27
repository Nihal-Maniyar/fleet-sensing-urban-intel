"""Route and Waypoint abstractions for realistic road-aligned bus trajectories."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple


@dataclass(frozen=True)
class Waypoint:
    """A geographic road-aligned waypoint along a route."""

    latitude: float
    longitude: float
    name: str = ""
    order: int = 0
    speed_kmh: float = 30.0


@dataclass
class Route:
    """A collection of ordered waypoints representing an actual road corridor."""

    route_id: str
    name: str
    description: str
    waypoints: List[Waypoint] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.route_id:
            raise ValueError("route_id cannot be empty")

    def total_distance_meters(self) -> float:
        """Calculate total route length in meters."""
        if len(self.waypoints) < 2:
            return 0.0
        total = 0.0
        for i in range(len(self.waypoints) - 1):
            w1 = self.waypoints[i]
            w2 = self.waypoints[i + 1]
            total += haversine_distance(w1.latitude, w1.longitude, w2.latitude, w2.longitude)
        return total

    def get_waypoint_by_name(self, name: str) -> Optional[Waypoint]:
        """Find a waypoint by its landmark name."""
        for wp in self.waypoints:
            if name.lower() in wp.name.lower():
                return wp
        return None

    def interpolate(self, fraction: float) -> Tuple[float, float, float]:
        """Interpolate coordinate (lat, lon, heading) at normalized progress [0.0, 1.0]."""
        if not self.waypoints:
            raise ValueError("Cannot interpolate an empty route")
        if len(self.waypoints) == 1 or fraction <= 0.0:
            return (self.waypoints[0].latitude, self.waypoints[0].longitude, 0.0)
        if fraction >= 1.0:
            last = self.waypoints[-1]
            prev = self.waypoints[-2]
            heading = calculate_bearing(prev.latitude, prev.longitude, last.latitude, last.longitude)
            return (last.latitude, last.longitude, heading)

        # Distances between consecutive waypoints
        segment_lengths: List[float] = []
        for i in range(len(self.waypoints) - 1):
            w1, w2 = self.waypoints[i], self.waypoints[i + 1]
            dist = haversine_distance(w1.latitude, w1.longitude, w2.latitude, w2.longitude)
            segment_lengths.append(dist)

        total_length = sum(segment_lengths)
        if total_length == 0.0:
            return (self.waypoints[0].latitude, self.waypoints[0].longitude, 0.0)

        target_dist = fraction * total_length
        accumulated = 0.0

        for i, length in enumerate(segment_lengths):
            if accumulated + length >= target_dist:
                seg_fraction = (target_dist - accumulated) / length if length > 0 else 0.0
                w1, w2 = self.waypoints[i], self.waypoints[i + 1]
                lat = w1.latitude + seg_fraction * (w2.latitude - w1.latitude)
                lon = w1.longitude + seg_fraction * (w2.longitude - w1.longitude)
                heading = calculate_bearing(w1.latitude, w1.longitude, w2.latitude, w2.longitude)
                return (lat, lon, heading)
            accumulated += length

        last = self.waypoints[-1]
        return (last.latitude, last.longitude, 0.0)


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Compute great-circle distance between two points in meters."""
    r = 6371000.0  # Earth's radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def calculate_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate initial compass bearing from (lat1, lon1) to (lat2, lon2) in degrees [0, 360)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360.0) % 360.0
