"""GPS/NavIC sensor simulation with realistic noise and road alignment preservation."""

from __future__ import annotations

import math
import random
from typing import Optional, Tuple

try:
    from routes.route import calculate_bearing, haversine_distance
except (ImportError, ValueError):
    from ..routes.route import calculate_bearing, haversine_distance
from .coordinates import Coordinate


class GPSSimulator:
    """Simulates realistic vehicle GNSS/NavIC sensor readings.

    Crucially, it preserves raw GPS coordinates separately from road-aligned
    coordinates, as mandated by project architecture and api-contract.md.
    """

    def __init__(
        self,
        noise_std_meters: float = 2.0,
        seed: Optional[int] = 42,
    ) -> None:
        self.noise_std_meters = noise_std_meters
        self._rng = random.Random(seed)

    def set_seed(self, seed: int) -> None:
        """Seed random generator for deterministic reproducibility."""
        self._rng = random.Random(seed)

    def apply_noise(
        self,
        road_lat: float,
        road_lon: float,
        deterministic_offset_meters: Optional[Tuple[float, float]] = None,
    ) -> Tuple[float, float]:
        """Produce raw GPS reading with realistic sensor jitter.

        Args:
            road_lat: Ground truth road-aligned latitude
            road_lon: Ground truth road-aligned longitude
            deterministic_offset_meters: Optional fixed (north_meters, east_meters) offset
                                         for repeatable scenario testing.

        Returns:
            Tuple of (raw_latitude, raw_longitude)
        """
        # Approx 1 degree latitude ~ 111,320 meters
        meters_per_lat_deg = 111320.0
        # Approx 1 degree longitude ~ 111,320 * cos(lat) meters
        meters_per_lon_deg = 111320.0 * math.cos(math.radians(road_lat))

        if deterministic_offset_meters is not None:
            dn, de = deterministic_offset_meters
        else:
            dn = self._rng.gauss(0.0, self.noise_std_meters)
            de = self._rng.gauss(0.0, self.noise_std_meters)

        raw_lat = road_lat + (dn / meters_per_lat_deg)
        raw_lon = road_lon + (de / meters_per_lon_deg)

        return (round(raw_lat, 6), round(raw_lon, 6))

    def compute_heading(
        self,
        prev_lat: float,
        prev_lon: float,
        curr_lat: float,
        curr_lon: float,
    ) -> float:
        """Compute heading in degrees [0, 360)."""
        return round(calculate_bearing(prev_lat, prev_lon, curr_lat, curr_lon), 1)
