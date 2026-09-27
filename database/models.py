"""SQLAlchemy ORM models defining the database schema for Beyonders Urban Intelligence.

Strictly aligned with docs/database.md and docs/api-contract.md.
"""

from __future__ import annotations

import datetime
from typing import Any, List, Optional

import sqlalchemy as sa
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from database.enums import (
    ConnectivityState,
    Department,
    EventType,
    IncidentStatus,
    Severity,
    TicketStatus,
)
from database.types import PointGeometry, point_to_wkt


class Base(DeclarativeBase):
    """Base declarative class for all models."""

    pass


class Bus(Base):
    """Registry of fleet vehicles and telemetry status."""

    __tablename__ = "buses"

    bus_id: Mapped[str] = mapped_column(String(32), primary_key=True, comment="Format: BUS-001")
    route_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    last_heartbeat_at: Mapped[Optional[datetime.datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    events: Mapped[List[Event]] = relationship("Event", back_populates="bus", cascade="all, delete-orphan")
    observations: Mapped[List[Observation]] = relationship(
        "Observation", back_populates="bus", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Bus {self.bus_id} (route={self.route_id}, active={self.is_active})>"


class Event(Base):
    """Raw edge-detected events ingested from MQTT or simulators."""

    __tablename__ = "events"

    event_id: Mapped[str] = mapped_column(
        String(32), primary_key=True, comment="Format: EVT-000001"
    )
    bus_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("buses.bus_id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(
        String(64), nullable=False, comment="e.g. actual_bus_simulator, data_demo_simulator"
    )
    connectivity_state: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=ConnectivityState.ONLINE.value,
        server_default=ConnectivityState.ONLINE.value,
    )
    raw_payload: Mapped[Optional[dict[str, Any]]] = mapped_column(JSON, nullable=True)
    received_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            f"connectivity_state IN ('{ConnectivityState.ONLINE.value}', '{ConnectivityState.OFFLINE.value}')",
            name="ck_events_connectivity_state",
        ),
    )

    # Relationships
    bus: Mapped[Bus] = relationship("Bus", back_populates="events")
    observation: Mapped[Optional[Observation]] = relationship(
        "Observation", back_populates="event", uselist=False, cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Event {self.event_id} (bus={self.bus_id}, state={self.connectivity_state})>"


class Observation(Base):
    """Persisted, normalized observation facts linked to raw and road-aligned points."""

    __tablename__ = "observations"

    observation_id: Mapped[str] = mapped_column(
        String(32), primary_key=True, comment="Format: OBS-000001"
    )
    event_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("events.event_id", ondelete="CASCADE"), unique=True, nullable=False
    )
    bus_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("buses.bus_id", ondelete="CASCADE"), nullable=False, index=True
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    road_aligned_latitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    road_aligned_longitude: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # PostGIS geometries: geom_raw & geom_road_aligned (SRID 4326)
    geom_raw = Column(PointGeometry(srid=4326), nullable=False)
    geom_road_aligned = Column(PointGeometry(srid=4326), nullable=True)

    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    evidence_image: Mapped[str] = mapped_column(String(512), nullable=False)
    heading_degrees: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            f"event_type IN ('{EventType.POTHOLE.value}', '{EventType.GARBAGE.value}', "
            f"'{EventType.TRAFFIC_OBSTRUCTION.value}', '{EventType.PEDESTRIAN_RISK.value}')",
            name="ck_observations_event_type",
        ),
        CheckConstraint(
            f"severity IS NULL OR severity IN ('{Severity.LOW.value}', '{Severity.MEDIUM.value}', '{Severity.HIGH.value}')",
            name="ck_observations_severity",
        ),
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_observations_confidence_range"),
        CheckConstraint("latitude >= -90.0 AND latitude <= 90.0", name="ck_observations_lat_range"),
        CheckConstraint("longitude >= -180.0 AND longitude <= 180.0", name="ck_observations_lon_range"),
        CheckConstraint(
            "road_aligned_latitude IS NULL OR (road_aligned_latitude >= -90.0 AND road_aligned_latitude <= 90.0)",
            name="ck_observations_road_lat_range",
        ),
        CheckConstraint(
            "road_aligned_longitude IS NULL OR (road_aligned_longitude >= -180.0 AND road_aligned_longitude <= 180.0)",
            name="ck_observations_road_lon_range",
        ),
        # GiST spatial indexes for PostGIS
        Index("idx_observations_geom_raw", geom_raw, postgresql_using="gist"),
        Index("idx_observations_geom_road_aligned", geom_road_aligned, postgresql_using="gist"),
        Index("idx_observations_type_time", "event_type", "timestamp"),
    )

    # Relationships
    event: Mapped[Event] = relationship("Event", back_populates="observation")
    bus: Mapped[Bus] = relationship("Bus", back_populates="observations")
    incident_associations: Mapped[List[IncidentObservation]] = relationship(
        "IncidentObservation", back_populates="observation", cascade="all, delete-orphan"
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Automatically populate geom_raw if not explicitly supplied
        if self.geom_raw is None and self.latitude is not None and self.longitude is not None:
            self.geom_raw = point_to_wkt(self.latitude, self.longitude)
        # Automatically populate geom_road_aligned if coords supplied
        if (
            self.geom_road_aligned is None
            and self.road_aligned_latitude is not None
            and self.road_aligned_longitude is not None
        ):
            self.geom_road_aligned = point_to_wkt(
                self.road_aligned_latitude, self.road_aligned_longitude
            )

    def __repr__(self) -> str:
        return (
            f"<Observation {self.observation_id} (type={self.event_type}, "
            f"conf={self.confidence:.2f}, lat={self.latitude:.4f}, lon={self.longitude:.4f})>"
        )


class Incident(Base):
    """Result of spatial-temporal fleet fusion aggregating observations."""

    __tablename__ = "incidents"

    incident_id: Mapped[str] = mapped_column(
        String(32), primary_key=True, comment="Format: INC-000001"
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=IncidentStatus.CANDIDATE.value,
        server_default=IncidentStatus.CANDIDATE.value,
        index=True,
    )
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)

    # PostGIS geometry: centroid / road-aligned location
    geom = Column(PointGeometry(srid=4326), nullable=False)

    observation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    bus_count: Mapped[int] = mapped_column(Integer, nullable=False, default=1, server_default="1")
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
        default=Severity.MEDIUM.value,
        server_default=Severity.MEDIUM.value,
    )
    department: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        default=Department.MUNICIPAL_CORPORATION.value,
        server_default=Department.MUNICIPAL_CORPORATION.value,
    )
    first_observed_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_observed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            f"event_type IN ('{EventType.POTHOLE.value}', '{EventType.GARBAGE.value}', "
            f"'{EventType.TRAFFIC_OBSTRUCTION.value}', '{EventType.PEDESTRIAN_RISK.value}')",
            name="ck_incidents_event_type",
        ),
        CheckConstraint(
            f"status IN ('{IncidentStatus.CANDIDATE.value}', '{IncidentStatus.VERIFIED.value}', "
            f"'{IncidentStatus.REJECTED.value}', '{IncidentStatus.RESOLUTION_CANDIDATE.value}', "
            f"'{IncidentStatus.RESOLVED.value}')",
            name="ck_incidents_status",
        ),
        CheckConstraint(
            f"severity IN ('{Severity.LOW.value}', '{Severity.MEDIUM.value}', '{Severity.HIGH.value}')",
            name="ck_incidents_severity",
        ),
        CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_incidents_confidence_range"),
        CheckConstraint("latitude >= -90.0 AND latitude <= 90.0", name="ck_incidents_lat_range"),
        CheckConstraint("longitude >= -180.0 AND longitude <= 180.0", name="ck_incidents_lon_range"),
        CheckConstraint("observation_count >= 1", name="ck_incidents_obs_count_positive"),
        CheckConstraint("bus_count >= 1", name="ck_incidents_bus_count_positive"),
        # GiST spatial index for PostGIS
        Index("idx_incidents_geom", geom, postgresql_using="gist"),
        Index("idx_incidents_status_type", "status", "event_type"),
    )

    # Relationships
    incident_associations: Mapped[List[IncidentObservation]] = relationship(
        "IncidentObservation", back_populates="incident", cascade="all, delete-orphan"
    )
    ticket: Mapped[Optional[Ticket]] = relationship(
        "Ticket", back_populates="incident", uselist=False
    )

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if self.geom is None and self.latitude is not None and self.longitude is not None:
            self.geom = point_to_wkt(self.latitude, self.longitude)

    def __repr__(self) -> str:
        return (
            f"<Incident {self.incident_id} (type={self.event_type}, status={self.status}, "
            f"buses={self.bus_count}, obs={self.observation_count})>"
        )


class IncidentObservation(Base):
    """Audit junction table linking incidents to supporting observations."""

    __tablename__ = "incident_observations"

    incident_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("incidents.incident_id", ondelete="CASCADE"), primary_key=True
    )
    observation_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("observations.observation_id", ondelete="RESTRICT"), primary_key=True
    )
    linked_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    # Relationships
    incident: Mapped[Incident] = relationship("Incident", back_populates="incident_associations")
    observation: Mapped[Observation] = relationship("Observation", back_populates="incident_associations")

    def __repr__(self) -> str:
        return f"<IncidentObservation (inc={self.incident_id}, obs={self.observation_id})>"


class Ticket(Base):
    """Civic authority ticket created when an incident is verified."""

    __tablename__ = "tickets"

    ticket_id: Mapped[str] = mapped_column(
        String(32), primary_key=True, comment="Format: POT-YYYY-XXXXXX"
    )
    incident_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("incidents.incident_id", ondelete="RESTRICT"), unique=True, nullable=False
    )
    workorder_id: Mapped[Optional[str]] = mapped_column(
        String(32), nullable=True, comment="Format: WO-YYYY-XXXXXX"
    )
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=TicketStatus.REPORTED.value,
        server_default=TicketStatus.REPORTED.value,
        index=True,
    )
    department: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    google_maps_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    estimated_repair_sla_hours: Mapped[int] = mapped_column(
        Integer, nullable=False, default=48, server_default="48"
    )
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            f"status IN ('{TicketStatus.REPORTED.value}', '{TicketStatus.ACKNOWLEDGED.value}', "
            f"'{TicketStatus.IN_PROGRESS.value}', '{TicketStatus.RESOLVED.value}')",
            name="ck_tickets_status",
        ),
        CheckConstraint("estimated_repair_sla_hours > 0", name="ck_tickets_sla_positive"),
    )

    # Relationships
    incident: Mapped[Incident] = relationship("Incident", back_populates="ticket")
    status_history: Mapped[List[TicketStatusHistory]] = relationship(
        "TicketStatusHistory",
        back_populates="ticket",
        cascade="all, delete-orphan",
        order_by="TicketStatusHistory.changed_at",
    )

    def __repr__(self) -> str:
        return f"<Ticket {self.ticket_id} (status={self.status}, incident={self.incident_id})>"


class TicketStatusHistory(Base):
    """Append-only audit trail of civic authority workflow actions."""

    __tablename__ = "ticket_status_history"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ticket_id: Mapped[str] = mapped_column(
        String(32), ForeignKey("tickets.ticket_id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_status: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    to_status: Mapped[str] = mapped_column(String(32), nullable=False)
    changed_by: Mapped[str] = mapped_column(String(64), nullable=False, default="system")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    changed_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint(
            f"to_status IN ('{TicketStatus.REPORTED.value}', '{TicketStatus.ACKNOWLEDGED.value}', "
            f"'{TicketStatus.IN_PROGRESS.value}', '{TicketStatus.RESOLVED.value}')",
            name="ck_ticket_history_to_status",
        ),
        Index("idx_ticket_history_ticket_time", "ticket_id", "changed_at"),
    )

    # Relationships
    ticket: Mapped[Ticket] = relationship("Ticket", back_populates="status_history")

    def __repr__(self) -> str:
        return f"<TicketStatusHistory {self.id} ({self.ticket_id}: {self.from_status}->{self.to_status})>"
