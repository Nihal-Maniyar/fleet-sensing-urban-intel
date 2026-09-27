"""Initial PostGIS schema with core tables, constraints, and GiST indexes.

Revision ID: 0001_initial_postgis_schema
Revises: None
Create Date: 2026-09-21 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geometry

# revision identifiers, used by Alembic.
revision: str = "0001_initial_postgis_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable PostGIS extension (PostgreSQL only)
    conn = op.get_bind()
    if conn.dialect.name == "postgresql":
        op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 2. Table: buses
    op.create_table(
        "buses",
        sa.Column("bus_id", sa.String(32), primary_key=True, comment="Format: BUS-001"),
        sa.Column("route_id", sa.String(64), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("last_heartbeat_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 3. Table: events
    op.create_table(
        "events",
        sa.Column("event_id", sa.String(32), primary_key=True, comment="Format: EVT-000001"),
        sa.Column(
            "bus_id",
            sa.String(32),
            sa.ForeignKey("buses.bus_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column(
            "connectivity_state",
            sa.String(16),
            nullable=False,
            server_default="ONLINE",
        ),
        sa.Column("raw_payload", sa.JSON(), nullable=True),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "connectivity_state IN ('ONLINE', 'OFFLINE')",
            name="ck_events_connectivity_state",
        ),
    )

    # Geometry column definitions for observations
    geom_raw_col = (
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False)
        if conn.dialect.name == "postgresql"
        else sa.String(255)
    )
    geom_road_col = (
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False)
        if conn.dialect.name == "postgresql"
        else sa.String(255)
    )

    # 4. Table: observations
    op.create_table(
        "observations",
        sa.Column("observation_id", sa.String(32), primary_key=True, comment="Format: OBS-000001"),
        sa.Column(
            "event_id",
            sa.String(32),
            sa.ForeignKey("events.event_id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "bus_id",
            sa.String(32),
            sa.ForeignKey("buses.bus_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("event_type", sa.String(64), nullable=False, index=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("road_aligned_latitude", sa.Float(), nullable=True),
        sa.Column("road_aligned_longitude", sa.Float(), nullable=True),
        sa.Column("geom_raw", geom_raw_col, nullable=False),
        sa.Column("geom_road_aligned", geom_road_col, nullable=True),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(16), nullable=True),
        sa.Column("evidence_image", sa.String(512), nullable=False),
        sa.Column("heading_degrees", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "event_type IN ('POTHOLE', 'GARBAGE', 'TRAFFIC_OBSTRUCTION', 'PEDESTRIAN_RISK')",
            name="ck_observations_event_type",
        ),
        sa.CheckConstraint(
            "severity IS NULL OR severity IN ('LOW', 'MEDIUM', 'HIGH')",
            name="ck_observations_severity",
        ),
        sa.CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_observations_confidence_range"),
        sa.CheckConstraint("latitude >= -90.0 AND latitude <= 90.0", name="ck_observations_lat_range"),
        sa.CheckConstraint("longitude >= -180.0 AND longitude <= 180.0", name="ck_observations_lon_range"),
        sa.CheckConstraint(
            "road_aligned_latitude IS NULL OR (road_aligned_latitude >= -90.0 AND road_aligned_latitude <= 90.0)",
            name="ck_observations_road_lat_range",
        ),
        sa.CheckConstraint(
            "road_aligned_longitude IS NULL OR (road_aligned_longitude >= -180.0 AND road_aligned_longitude <= 180.0)",
            name="ck_observations_road_lon_range",
        ),
    )

    if conn.dialect.name == "postgresql":
        op.create_index(
            "idx_observations_geom_raw",
            "observations",
            ["geom_raw"],
            postgresql_using="gist",
        )
        op.create_index(
            "idx_observations_geom_road_aligned",
            "observations",
            ["geom_road_aligned"],
            postgresql_using="gist",
        )
    op.create_index(
        "idx_observations_type_time",
        "observations",
        ["event_type", "timestamp"],
    )

    # Geometry column definition for incidents
    geom_inc_col = (
        Geometry(geometry_type="POINT", srid=4326, spatial_index=False)
        if conn.dialect.name == "postgresql"
        else sa.String(255)
    )

    # 5. Table: incidents
    op.create_table(
        "incidents",
        sa.Column("incident_id", sa.String(32), primary_key=True, comment="Format: INC-000001"),
        sa.Column("event_type", sa.String(64), nullable=False, index=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="CANDIDATE", index=True),
        sa.Column("latitude", sa.Float(), nullable=False),
        sa.Column("longitude", sa.Float(), nullable=False),
        sa.Column("geom", geom_inc_col, nullable=False),
        sa.Column("observation_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("bus_count", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("severity", sa.String(16), nullable=False, server_default="MEDIUM"),
        sa.Column("department", sa.String(64), nullable=False, server_default="MUNICIPAL_CORPORATION"),
        sa.Column("first_observed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("last_observed_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "event_type IN ('POTHOLE', 'GARBAGE', 'TRAFFIC_OBSTRUCTION', 'PEDESTRIAN_RISK')",
            name="ck_incidents_event_type",
        ),
        sa.CheckConstraint(
            "status IN ('CANDIDATE', 'VERIFIED', 'REJECTED', 'RESOLUTION_CANDIDATE', 'RESOLVED')",
            name="ck_incidents_status",
        ),
        sa.CheckConstraint("severity IN ('LOW', 'MEDIUM', 'HIGH')", name="ck_incidents_severity"),
        sa.CheckConstraint("confidence >= 0.0 AND confidence <= 1.0", name="ck_incidents_confidence_range"),
        sa.CheckConstraint("latitude >= -90.0 AND latitude <= 90.0", name="ck_incidents_lat_range"),
        sa.CheckConstraint("longitude >= -180.0 AND longitude <= 180.0", name="ck_incidents_lon_range"),
        sa.CheckConstraint("observation_count >= 1", name="ck_incidents_obs_count_positive"),
        sa.CheckConstraint("bus_count >= 1", name="ck_incidents_bus_count_positive"),
    )

    if conn.dialect.name == "postgresql":
        op.create_index(
            "idx_incidents_geom",
            "incidents",
            ["geom"],
            postgresql_using="gist",
        )
    op.create_index(
        "idx_incidents_status_type",
        "incidents",
        ["status", "event_type"],
    )

    # 6. Table: incident_observations (Audit Junction)
    op.create_table(
        "incident_observations",
        sa.Column(
            "incident_id",
            sa.String(32),
            sa.ForeignKey("incidents.incident_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "observation_id",
            sa.String(32),
            sa.ForeignKey("observations.observation_id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("linked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # 7. Table: tickets
    op.create_table(
        "tickets",
        sa.Column("ticket_id", sa.String(32), primary_key=True, comment="Format: POT-YYYY-XXXXXX"),
        sa.Column(
            "incident_id",
            sa.String(32),
            sa.ForeignKey("incidents.incident_id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("workorder_id", sa.String(32), nullable=True, comment="Format: WO-YYYY-XXXXXX"),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("status", sa.String(32), nullable=False, server_default="REPORTED", index=True),
        sa.Column("department", sa.String(64), nullable=False, index=True),
        sa.Column("google_maps_url", sa.String(512), nullable=True),
        sa.Column("estimated_repair_sla_hours", sa.Integer(), nullable=False, server_default="48"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "status IN ('REPORTED', 'ACKNOWLEDGED', 'IN_PROGRESS', 'RESOLVED')",
            name="ck_tickets_status",
        ),
        sa.CheckConstraint("estimated_repair_sla_hours > 0", name="ck_tickets_sla_positive"),
    )

    # 8. Table: ticket_status_history
    op.create_table(
        "ticket_status_history",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column(
            "ticket_id",
            sa.String(32),
            sa.ForeignKey("tickets.ticket_id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("from_status", sa.String(32), nullable=True),
        sa.Column("to_status", sa.String(32), nullable=False),
        sa.Column("changed_by", sa.String(64), nullable=False, server_default="system"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("changed_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint(
            "to_status IN ('REPORTED', 'ACKNOWLEDGED', 'IN_PROGRESS', 'RESOLVED')",
            name="ck_ticket_history_to_status",
        ),
    )
    op.create_index(
        "idx_ticket_history_ticket_time",
        "ticket_status_history",
        ["ticket_id", "changed_at"],
    )


def downgrade() -> None:
    conn = op.get_bind()

    # Drop tables in reverse order of foreign key dependencies
    op.drop_table("ticket_status_history")
    op.drop_table("tickets")
    op.drop_table("incident_observations")
    op.drop_table("incidents")
    op.drop_table("observations")
    op.drop_table("events")
    op.drop_table("buses")

    if conn.dialect.name == "postgresql":
        op.execute("DROP EXTENSION IF EXISTS postgis;")
