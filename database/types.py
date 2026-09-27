"""Custom database types and geometry decorators supporting PostGIS and SQLite test fallback."""

from __future__ import annotations

import re
from typing import Any, Optional, Tuple

import sqlalchemy as sa
from geoalchemy2 import Geometry
from geoalchemy2.elements import WKBElement, WKTElement
from sqlalchemy.types import TypeDecorator

WKT_POINT_REGEX = re.compile(r"POINT\s*\(\s*([-\d\.]+)\s+([-\d\.]+)\s*\)", re.IGNORECASE)


class PointGeometry(TypeDecorator):
    """Custom geometry type decorator for Point geometries (SRID 4326).

    - On PostgreSQL: compiles to native PostGIS `geometry(POINT, 4326)`.
    - On SQLite (testing): stores as WKT / text to avoid requiring SpatiaLite triggers.
    """

    impl = Geometry(geometry_type="POINT", srid=4326, spatial_index=False)
    cache_ok = True

    def __init__(self, srid: int = 4326, **kwargs: Any) -> None:
        self.srid = srid
        kwargs["spatial_index"] = False
        super().__init__(geometry_type="POINT", srid=srid, **kwargs)
        self.spatial_index = False

    def load_dialect_impl(self, dialect: Any) -> Any:
        if dialect is None:
            return self.impl
        if dialect.name == "sqlite":
            return dialect.type_descriptor(sa.String(255))
        return dialect.type_descriptor(
            Geometry(geometry_type="POINT", srid=self.srid, spatial_index=False)
        )

    def process_bind_param(self, value: Any, dialect: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (WKTElement, WKBElement)):
            return value
        if isinstance(value, tuple) and len(value) == 2:
            lat, lon = value
            return f"SRID={self.srid};POINT({lon} {lat})"
        if isinstance(value, str):
            if value.startswith("SRID=") or value.startswith("POINT"):
                return value
            return f"SRID={self.srid};{value}"
        return value

    def process_result_value(self, value: Any, dialect: Any) -> Any:
        return value


def point_to_wkt(latitude: float, longitude: float, srid: int = 4326) -> str:
    """Format coordinates as WKT Point with SRID. Note: Longitude is X, Latitude is Y."""
    return f"SRID={srid};POINT({longitude:.6f} {latitude:.6f})"


def parse_point_wkt(wkt_str: str) -> Optional[Tuple[float, float]]:
    """Parse WKT point string into (latitude, longitude) tuple."""
    if not wkt_str:
        return None
    match = WKT_POINT_REGEX.search(wkt_str)
    if match:
        lon = float(match.group(1))
        lat = float(match.group(2))
        return lat, lon
    return None
