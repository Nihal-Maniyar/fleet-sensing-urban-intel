"""Tests for GNSS/NavIC and IMU sensor simulation."""

import unittest
from pathlib import Path
import sys

sim_dir = Path(__file__).resolve().parent.parent
if str(sim_dir) not in sys.path:
    sys.path.insert(0, str(sim_dir))

from sensors.gnss import GNSSSimulator, PUNE_ROUTES
from sensors.imu import IMUSimulator


class TestSensors(unittest.TestCase):
    """Verify GNSS trajectory tracking and IMU dynamic physics."""

    def test_gnss_simulator_progression(self):
        gnss = GNSSSimulator(route_id="ROUTE-PUNE-FC", speed_kmh=40.0)
        raw_lat, raw_lon, road_lat, road_lon, heading = gnss.step(dt_seconds=0.1)

        # Values should be within Pune bounds
        self.assertTrue(18.4 <= raw_lat <= 18.6)
        self.assertTrue(73.7 <= raw_lon <= 73.9)
        self.assertTrue(18.4 <= road_lat <= 18.6)
        self.assertTrue(73.7 <= road_lon <= 73.9)
        self.assertTrue(0.0 <= heading <= 360.0)

        # Raw coords should have slight noise variance from road-aligned coords
        diff_lat = abs(raw_lat - road_lat)
        self.assertLess(diff_lat, 0.001)  # Within a few meters

    def test_imu_shock_trigger(self):
        imu = IMUSimulator(sample_rate_hz=20.0)

        # Normal reading: az near 9.81 m/s^2, shock_detected=False
        normal = imu.step(speed_kmh=35.0)
        self.assertAlmostEqual(normal.az, 9.81, delta=1.5)
        self.assertFalse(normal.shock_detected)

        # Trigger pothole impact shock
        imu.trigger_shock(intensity_g=2.5)
        shock_reading = imu.step(speed_kmh=35.0)
        self.assertTrue(shock_reading.shock_detected)
        # Az acceleration should spike noticeably above normal baseline
        self.assertGreater(abs(shock_reading.az - 9.81), 4.0)


if __name__ == "__main__":
    unittest.main()
