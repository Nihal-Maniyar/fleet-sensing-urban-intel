"""Geographic coordinate models and transformations."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple


@dataclass(frozen=True)
class Coordinate:
    """WGS84 decimal degree coordinate representation."""

    latitude: float
    longitude: float

    def __post_init__(self) -> None:
        if not (-90.0 <= self.latitude <= 90.0):
            raise ValueError(f"Latitude out of bounds: {self.latitude}. Must be between -90 and 90.")
        if not (-180.0 <= self.longitude <= 180.0):
            raise ValueError(f"Longitude out of bounds: {self.longitude}. Must be between -180 and 180.")

    def as_tuple(self) -> Tuple[float, float]:
        return (self.latitude, self.longitude)
