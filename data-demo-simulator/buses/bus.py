"""Bus entity representation adhering to project naming standards."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

BUS_ID_PATTERN = re.compile(r"^BUS-\d{3,}$")


@dataclass
class Bus:
    """Represents an individual public transit bus sensing node.

    Identifier format: BUS-001, BUS-002, etc. (strictly enforced).
    """

    bus_id: str
    route_id: Optional[str] = None
    connectivity_state: str = "ONLINE"
    speed_kmh: float = 30.0
    current_latitude: Optional[float] = None
    current_longitude: Optional[float] = None
    heading_degrees: Optional[float] = None

    def __post_init__(self) -> None:
        if not BUS_ID_PATTERN.match(self.bus_id):
            raise ValueError(
                f"Invalid bus_id format: '{self.bus_id}'. Must follow 'BUS-XXX' pattern (e.g. BUS-001)."
            )
        if self.connectivity_state not in ("ONLINE", "OFFLINE"):
            raise ValueError(
                f"Invalid connectivity_state: '{self.connectivity_state}'. Must be 'ONLINE' or 'OFFLINE'."
            )

    def set_online(self) -> None:
        """Switch bus connectivity to ONLINE."""
        self.connectivity_state = "ONLINE"

    def set_offline(self) -> None:
        """Switch bus connectivity to OFFLINE (activates SQLite/WAL outbox queueing)."""
        self.connectivity_state = "OFFLINE"

    @property
    def is_online(self) -> bool:
        return self.connectivity_state == "ONLINE"
