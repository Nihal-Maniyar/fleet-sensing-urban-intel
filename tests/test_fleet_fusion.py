"""Unit tests for Fleet Fusion policy implemented in `database.fusion`.

These tests exercise the deterministic spatial-temporal fusion rules and
verify idempotency and preservation of observations.
"""

from __future__ import annotations

import datetime
import unittest

import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker

from database.models import Base, Incident, Observation
from database.operations import (
    create_observation,
    create_or_update_incident,
    insert_event_idempotent,
)
from database.identifiers import generate_incident_id
from database.fusion import fuse_observation
from database.enums import EventType, Severity, Department, IncidentStatus


class TestFleetFusion(unittest.TestCase):
    def setUp(self) -> None:
        self.engine = sa.create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(self.engine)
        self.engine.dispose()

    def _now(self) -> datetime.datetime:
        return datetime.datetime.now(datetime.timezone.utc)

    def test_compatible_observations_are_fused(self):
        now = self._now()
        insert_event_idempotent(self.session, {"event_id": "EVT-100000", "bus_id": "BUS-001"})
        insert_event_idempotent(self.session, {"event_id": "EVT-100001", "bus_id": "BUS-002"})

        obs1 = create_observation(
            self.session,
            observation_id="OBS-100000",
            event_id="EVT-100000",
            bus_id="BUS-001",
            event_type=EventType.POTHOLE.value,
            timestamp=now,
            latitude=18.520400,
            longitude=73.856700,
            confidence=0.85,
            evidence_image="img1.jpg",
        )

        obs2 = create_observation(
            self.session,
            observation_id="OBS-100001",
            event_id="EVT-100001",
            bus_id="BUS-002",
            event_type=EventType.POTHOLE.value,
            timestamp=now,
            latitude=18.520405,
            longitude=73.856705,
            confidence=0.90,
            evidence_image="img2.jpg",
        )

        inc1, created1 = fuse_observation(self.session, obs1)
        self.assertTrue(created1)
        inc2, created2 = fuse_observation(self.session, obs2)
        # Second observation should attach to same incident
        self.assertFalse(created2)
        self.assertEqual(inc1.incident_id, inc2.incident_id)
        fetched = self.session.get(Incident, inc1.incident_id)
        self.assertEqual(fetched.observation_count, 2)

    def test_distance_greater_than_15_no_fusion(self):
        now = self._now()
        insert_event_idempotent(self.session, {"event_id": "EVT-110000", "bus_id": "BUS-010"})
        insert_event_idempotent(self.session, {"event_id": "EVT-110001", "bus_id": "BUS-011"})

        obs1 = create_observation(
            self.session,
            observation_id="OBS-110000",
            event_id="EVT-110000",
            bus_id="BUS-010",
            event_type=EventType.POTHOLE.value,
            timestamp=now,
            latitude=18.520400,
            longitude=73.856700,
            confidence=0.90,
            evidence_image="imgA.jpg",
        )

        # ~100 meters away
        obs2 = create_observation(
            self.session,
            observation_id="OBS-110001",
            event_id="EVT-110001",
            bus_id="BUS-011",
            event_type=EventType.POTHOLE.value,
            timestamp=now,
            latitude=18.521300,
            longitude=73.856700,
            confidence=0.92,
            evidence_image="imgB.jpg",
        )

        inc1, _ = fuse_observation(self.session, obs1)
        inc2, created2 = fuse_observation(self.session, obs2)
        self.assertTrue(created2)
        self.assertNotEqual(inc1.incident_id, inc2.incident_id)

    def test_time_difference_greater_than_5_minutes_no_fusion(self):
        t1 = self._now()
        t2 = t1 + datetime.timedelta(minutes=6)
        insert_event_idempotent(self.session, {"event_id": "EVT-120000", "bus_id": "BUS-020"})
        insert_event_idempotent(self.session, {"event_id": "EVT-120001", "bus_id": "BUS-021"})

        obs1 = create_observation(
            self.session,
            observation_id="OBS-120000",
            event_id="EVT-120000",
            bus_id="BUS-020",
            event_type=EventType.POTHOLE.value,
            timestamp=t1,
            latitude=18.520400,
            longitude=73.856700,
            confidence=0.90,
            evidence_image="img1.jpg",
        )

        obs2 = create_observation(
            self.session,
            observation_id="OBS-120001",
            event_id="EVT-120001",
            bus_id="BUS-021",
            event_type=EventType.POTHOLE.value,
            timestamp=t2,
            latitude=18.520401,
            longitude=73.856701,
            confidence=0.91,
            evidence_image="img2.jpg",
        )

        inc1, _ = fuse_observation(self.session, obs1)
        inc2, created2 = fuse_observation(self.session, obs2)
        self.assertTrue(created2)
        self.assertNotEqual(inc1.incident_id, inc2.incident_id)

    def test_confidence_boundary_and_below(self):
        now = self._now()
        insert_event_idempotent(self.session, {"event_id": "EVT-130000", "bus_id": "BUS-030"})
        insert_event_idempotent(self.session, {"event_id": "EVT-130001", "bus_id": "BUS-031"})

        # Exactly at threshold (0.80) should be fused / create incident
        obs_ok = create_observation(
            self.session,
            observation_id="OBS-130000",
            event_id="EVT-130000",
            bus_id="BUS-030",
            event_type=EventType.POTHOLE.value,
            timestamp=now,
            latitude=18.520400,
            longitude=73.856700,
            confidence=0.80,
            evidence_image="img_ok.jpg",
        )

        # Below threshold should NOT be fused
        obs_low = create_observation(
            self.session,
            observation_id="OBS-130001",
            event_id="EVT-130001",
            bus_id="BUS-031",
            event_type=EventType.POTHOLE.value,
            timestamp=now,
            latitude=18.520401,
            longitude=73.856701,
            confidence=0.79,
            evidence_image="img_low.jpg",
        )

        inc_ok, created_ok = fuse_observation(self.session, obs_ok)
        self.assertTrue(created_ok)

        res_low = fuse_observation(self.session, obs_low)
        self.assertIsNone(res_low)

    def test_same_bus_multiple_observations(self):
        now = self._now()
        insert_event_idempotent(self.session, {"event_id": "EVT-140000", "bus_id": "BUS-040"})
        insert_event_idempotent(self.session, {"event_id": "EVT-140001", "bus_id": "BUS-040"})

        obs1 = create_observation(
            self.session,
            observation_id="OBS-140000",
            event_id="EVT-140000",
            bus_id="BUS-040",
            event_type=EventType.POTHOLE.value,
            timestamp=now,
            latitude=18.520400,
            longitude=73.856700,
            confidence=0.90,
            evidence_image="img1.jpg",
        )

        obs2 = create_observation(
            self.session,
            observation_id="OBS-140001",
            event_id="EVT-140001",
            bus_id="BUS-040",
            event_type=EventType.POTHOLE.value,
            timestamp=now,
            latitude=18.520401,
            longitude=73.856701,
            confidence=0.91,
            evidence_image="img2.jpg",
        )

        inc, _ = fuse_observation(self.session, obs1)
        inc2, _ = fuse_observation(self.session, obs2)
        self.assertEqual(inc.incident_id, inc2.incident_id)
        fetched = self.session.get(Incident, inc.incident_id)
        # bus_count should remain 1 because both observations came from same bus
        self.assertEqual(fetched.bus_count, 1)

    def test_different_event_types_do_not_fuse(self):
        now = self._now()
        insert_event_idempotent(self.session, {"event_id": "EVT-150000", "bus_id": "BUS-050"})
        insert_event_idempotent(self.session, {"event_id": "EVT-150001", "bus_id": "BUS-051"})

        obs1 = create_observation(
            self.session,
            observation_id="OBS-150000",
            event_id="EVT-150000",
            bus_id="BUS-050",
            event_type=EventType.POTHOLE.value,
            timestamp=now,
            latitude=18.520400,
            longitude=73.856700,
            confidence=0.90,
            evidence_image="img1.jpg",
        )

        obs2 = create_observation(
            self.session,
            observation_id="OBS-150001",
            event_id="EVT-150001",
            bus_id="BUS-051",
            event_type=EventType.GARBAGE.value,
            timestamp=now,
            latitude=18.520401,
            longitude=73.856701,
            confidence=0.92,
            evidence_image="img2.jpg",
        )

        inc1, _ = fuse_observation(self.session, obs1)
        inc2, created2 = fuse_observation(self.session, obs2)
        self.assertTrue(created2)
        self.assertNotEqual(inc1.incident_id, inc2.incident_id)

    def test_existing_incident_is_updated_instead_of_duplicate(self):
        now = self._now()
        # Create an initial incident
        inc, _ = create_or_update_incident(
            self.session,
            incident_id=generate_incident_id(900000),
            event_type=EventType.POTHOLE.value,
            latitude=18.520400,
            longitude=73.856700,
            confidence=0.85,
            severity=Severity.MEDIUM.value,
            department=Department.ROAD_AUTHORITY.value,
            first_observed_at=now,
            last_observed_at=now,
            observation_count=1,
            bus_count=1,
            status=IncidentStatus.CANDIDATE.value,
        )

        insert_event_idempotent(self.session, {"event_id": "EVT-160000", "bus_id": "BUS-060"})

        obs = create_observation(
            self.session,
            observation_id="OBS-160000",
            event_id="EVT-160000",
            bus_id="BUS-060",
            event_type=EventType.POTHOLE.value,
            timestamp=now,
            latitude=18.520401,
            longitude=73.856701,
            confidence=0.95,
            evidence_image="img_upd.jpg",
        )

        updated_inc, created_flag = fuse_observation(self.session, obs)
        self.assertFalse(created_flag)
        self.assertEqual(updated_inc.incident_id, inc.incident_id)
        refreshed = self.session.get(Incident, inc.incident_id)
        self.assertEqual(refreshed.observation_count, 2)

    def test_observations_are_not_deleted_and_processing_is_idempotent(self):
        now = self._now()
        insert_event_idempotent(self.session, {"event_id": "EVT-170000", "bus_id": "BUS-070"})

        obs = create_observation(
            self.session,
            observation_id="OBS-170000",
            event_id="EVT-170000",
            bus_id="BUS-070",
            event_type=EventType.POTHOLE.value,
            timestamp=now,
            latitude=18.520400,
            longitude=73.856700,
            confidence=0.90,
            evidence_image="img.jpg",
        )

        inc, created1 = fuse_observation(self.session, obs)
        inc_again, created2 = fuse_observation(self.session, obs)
        self.assertIsNotNone(inc)
        self.assertFalse(created2)
        # Observation still present
        stored_obs = self.session.get(Observation, "OBS-170000")
        self.assertIsNotNone(stored_obs)


if __name__ == "__main__":
    unittest.main()
