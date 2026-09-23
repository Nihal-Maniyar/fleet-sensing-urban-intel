"""Fleet Fusion policy and incident clustering engine.

Implements the configurable spatial-temporal fleet fusion defined in docs/fleet-fusion.md:
1. Road-align observations where possible while retaining raw coordinates.
2. Group compatible observations within spatial (<25m) and time windows (2h).
3. Corroborate across independent buses (e.g., BUS-001 and BUS-002).
4. Derive incident confidence, severity, department routing, and trigger civic tickets.
5. Provide automated resolution candidate verification when post-repair evidence arrives.
"""

from __future__ import annotations

import datetime
import math
from typing import Any, Dict, List, Optional, Tuple


# Configuration thresholds
SPATIAL_THRESHOLD_METERS = 25.0
TIME_WINDOW_SECONDS = 7200.0  # 2 hours
CONFIDENCE_BOOST_PER_BUS = 0.03

DEPARTMENT_ROUTING = {
    "POTHOLE": "MUNICIPAL_CORPORATION",
    "GARBAGE": "SOLID_WASTE_MANAGEMENT",
    "TRAFFIC_OBSTRUCTION": "TRAFFIC_POLICE",
    "PEDESTRIAN_RISK": "URBAN_PLANNING",
}


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great circle distance between two points in meters."""
    R = 6371000.0  # Earth radius in meters
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c


def parse_iso_utc(ts: Any) -> datetime.datetime:
    """Parse ISO UTC timestamp into datetime object."""
    if isinstance(ts, datetime.datetime):
        if ts.tzinfo is None:
            return ts.replace(tzinfo=datetime.timezone.utc)
        return ts
    if isinstance(ts, str):
        cleaned = ts.replace("Z", "+00:00")
        try:
            return datetime.datetime.fromisoformat(cleaned)
        except Exception:
            pass
    return datetime.datetime.now(datetime.timezone.utc)


def iso_utc(dt: datetime.datetime) -> str:
    """Format datetime as ISO 8601 UTC trailing Z string."""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


class FleetFusionEngine:
    """Configurable, explainable spatial-temporal fusion engine."""

    def __init__(
        self,
        spatial_threshold_meters: float = SPATIAL_THRESHOLD_METERS,
        time_window_seconds: float = TIME_WINDOW_SECONDS,
    ) -> None:
        self.spatial_threshold = spatial_threshold_meters
        self.time_window = time_window_seconds

    def effective_coords(self, obj: Dict[str, Any]) -> Tuple[float, float]:
        """Return (lat, lon) preferring road-aligned coordinates if available."""
        if obj.get("road_aligned_latitude") is not None and obj.get("road_aligned_longitude") is not None:
            return float(obj["road_aligned_latitude"]), float(obj["road_aligned_longitude"])
        return float(obj["latitude"]), float(obj["longitude"])

    def find_matching_incident(
        self,
        observation: Dict[str, Any],
        incidents: Dict[str, Dict[str, Any]],
    ) -> Optional[Dict[str, Any]]:
        """Find an existing incident matching event_type within spatial & time thresholds."""
        obs_type = observation.get("event_type")
        obs_lat, obs_lon = self.effective_coords(observation)
        obs_time = parse_iso_utc(observation.get("timestamp"))

        for inc in incidents.values():
            if inc.get("event_type") != obs_type:
                continue

            inc_lat, inc_lon = self.effective_coords(inc)
            dist = haversine_distance_meters(obs_lat, obs_lon, inc_lat, inc_lon)
            if dist > self.spatial_threshold:
                continue

            inc_time = parse_iso_utc(inc.get("last_observed_at", inc.get("first_observed_at")))
            time_diff = abs((obs_time - inc_time).total_seconds())
            if time_diff <= self.time_window:
                return inc

        return None

    def process_observation(
        self,
        observation: Dict[str, Any],
        incidents: Dict[str, Dict[str, Any]],
        tickets: Dict[str, Dict[str, Any]],
    ) -> Tuple[Dict[str, Any], Optional[Dict[str, Any]]]:
        """Fuse incoming observation into existing or new incident, and trigger ticket if verified.

        Returns: (incident, newly_created_or_updated_ticket)
        """
        obs_lat, obs_lon = self.effective_coords(observation)
        obs_time = parse_iso_utc(observation.get("timestamp"))
        obs_time_str = iso_utc(obs_time)
        bus_id = observation.get("bus_id", "BUS-UNKNOWN")
        confidence = float(observation.get("confidence", 0.9))
        event_type = observation.get("event_type", "POTHOLE")

        matched_incident = self.find_matching_incident(observation, incidents)
        created_ticket: Optional[Dict[str, Any]] = None

        if matched_incident is not None:
            # Corroborating observation into existing incident
            buses = matched_incident.setdefault("buses", [])
            if bus_id not in buses:
                buses.append(bus_id)

            matched_incident["observation_count"] = matched_incident.get("observation_count", 1) + 1
            matched_incident["bus_count"] = len(buses)
            matched_incident["last_observed_at"] = obs_time_str

            # Update confidence & severity
            old_conf = float(matched_incident.get("confidence", 0.9))
            new_conf = min(0.99, max(old_conf, confidence) + CONFIDENCE_BOOST_PER_BUS * (len(buses) - 1))
            matched_incident["confidence"] = round(new_conf, 2)

            if len(buses) >= 2 or new_conf >= 0.92:
                matched_incident["status"] = "VERIFIED"
                matched_incident["severity"] = "HIGH"
            else:
                matched_incident["severity"] = observation.get("severity", "MEDIUM")

            # Check if ticket should be issued or updated
            ticket_id = matched_incident.get("ticket_id")
            if not ticket_id and matched_incident["status"] == "VERIFIED":
                ticket_id = f"POT-2026-{matched_incident['incident_id'].split('-')[-1]}"
                matched_incident["ticket_id"] = ticket_id

                created_ticket = {
                    "ticket_id": ticket_id,
                    "incident_id": matched_incident["incident_id"],
                    "workorder_id": f"WO-2026-{ticket_id.split('-')[-1]}",
                    "event_type": event_type,
                    "confidence": matched_incident["confidence"],
                    "latitude": obs_lat,
                    "longitude": obs_lon,
                    "evidence_image": observation.get("evidence_image", f"runtime/evidence/{observation.get('event_id', 'EVT-000001')}.jpg"),
                    "google_maps_url": f"https://www.google.com/maps/dir/?api=1&destination={obs_lat},{obs_lon}",
                    "estimated_repair_sla_hours": 48,
                    "status": "REPORTED",
                    "created_at": obs_time_str,
                    "updated_at": obs_time_str,
                    "timeline": [
                        {"label": "Reported", "done": True, "time": obs_time_str},
                        {"label": "Acknowledged", "done": False, "time": "Pending"},
                        {"label": "In Progress", "done": False, "time": "Pending"},
                        {"label": "Resolved", "done": False, "time": "Pending"},
                    ],
                }
                tickets[ticket_id] = created_ticket

            return matched_incident, created_ticket

        else:
            # Create new incident record
            inc_seq = len(incidents) + 1
            inc_id = f"INC-{inc_seq:06d}"

            # High single confidence can produce verified, otherwise candidate
            init_status = "VERIFIED" if confidence >= 0.95 else "CANDIDATE"
            severity = observation.get("severity", "HIGH" if confidence >= 0.9 else "MEDIUM")
            department = DEPARTMENT_ROUTING.get(event_type, "MUNICIPAL_CORPORATION")

            new_incident = {
                "incident_id": inc_id,
                "event_type": event_type,
                "status": init_status,
                "latitude": obs_lat,
                "longitude": obs_lon,
                "observation_count": 1,
                "bus_count": 1,
                "buses": [bus_id],
                "confidence": round(confidence, 2),
                "severity": severity,
                "department": department,
                "first_observed_at": obs_time_str,
                "last_observed_at": obs_time_str,
                "locality": observation.get("locality", "Pune Transit Corridor"),
                "description": f"Sensed {event_type.replace('_', ' ').lower()} reported by {bus_id}.",
                "ticket_id": None,
            }

            if init_status == "VERIFIED":
                ticket_id = f"POT-2026-{inc_seq:06d}"
                new_incident["ticket_id"] = ticket_id
                created_ticket = {
                    "ticket_id": ticket_id,
                    "incident_id": inc_id,
                    "workorder_id": f"WO-2026-{inc_seq:06d}",
                    "event_type": event_type,
                    "confidence": new_incident["confidence"],
                    "latitude": obs_lat,
                    "longitude": obs_lon,
                    "evidence_image": observation.get("evidence_image", f"runtime/evidence/{observation.get('event_id', 'EVT-000001')}.jpg"),
                    "google_maps_url": f"https://www.google.com/maps/dir/?api=1&destination={obs_lat},{obs_lon}",
                    "estimated_repair_sla_hours": 48,
                    "status": "REPORTED",
                    "created_at": obs_time_str,
                    "updated_at": obs_time_str,
                    "timeline": [
                        {"label": "Reported", "done": True, "time": obs_time_str},
                        {"label": "Acknowledged", "done": False, "time": "Pending"},
                        {"label": "In Progress", "done": False, "time": "Pending"},
                        {"label": "Resolved", "done": False, "time": "Pending"},
                    ],
                }
                tickets[ticket_id] = created_ticket

            incidents[inc_id] = new_incident
            return new_incident, created_ticket
