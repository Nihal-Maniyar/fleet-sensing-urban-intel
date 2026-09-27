"""Tests for GPS simulator, coordinate calculations, and Pune routes."""

import sys
import unittest
from pathlib import Path

SIM_DIR = Path(__file__).resolve().parent.parent
if str(SIM_DIR) not in sys.path:
    sys.path.insert(0, str(SIM_DIR))

from gps.coordinates import Coordinate
from gps.simulator import GPSSimulator
from routes.pune_routes import FC_ROAD_ROUTE, JM_ROAD_ROUTE, KARVE_ROAD_ROUTE
from routes.route import calculate_bearing, haversine_distance


class TestGPSAndRoutes(unittest.TestCase):
    """Test suite for spatial logic, route calculations, and GPS noise."""

    def test_coordinate_validation(self) -> None:
        """Validates coordinate bounds."""
        coord = Coordinate(latitude=18.5204, longitude=73.8567)
        self.assertEqual(coord.latitude, 18.5204)
        self.assertEqual(coord.longitude, 73.8567)

        with self.assertRaises(ValueError):
            Coordinate(latitude=95.0, longitude=73.0)

        with self.assertRaises(ValueError):
            Coordinate(latitude=18.0, longitude=190.0)

    def test_haversine_distance(self) -> None:
        """Test great-circle distance between two known Pune points."""
        # Deccan Gymkhana (18.5158, 73.8418) to Goodluck Chowk (18.5196, 73.8436)
        dist = haversine_distance(18.5158, 73.8418, 18.5196, 73.8436)
        # Expected distance along FC Road is roughly 450-500 meters
        self.assertGreater(dist, 400.0)
        self.assertLess(dist, 600.0)

    def test_bearing_calculation(self) -> None:
        """Test heading bearing calculation."""
        # Due north
        b_north = calculate_bearing(0.0, 0.0, 1.0, 0.0)
        self.assertAlmostEqual(b_north, 0.0, places=1)

        # Due east
        b_east = calculate_bearing(0.0, 0.0, 0.0, 1.0)
        self.assertAlmostEqual(b_east, 90.0, places=1)

    def test_gps_noise_preserves_road_reference(self) -> None:
        """GPS simulator introduces minor noise while preserving reference."""
        sim = GPSSimulator(noise_std_meters=2.0, seed=42)
        road_lat = 18.519600
        road_lon = 73.843600

        raw_lat, raw_lon = sim.apply_noise(road_lat, road_lon)
        # Difference should be subtle (within ~10 meters, ~0.0001 deg)
        self.assertNotEqual((raw_lat, raw_lon), (road_lat, road_lon))
        self.assertAlmostEqual(raw_lat, road_lat, places=4)
        self.assertAlmostEqual(raw_lon, road_lon, places=4)

    def test_deterministic_offset(self) -> None:
        """Providing fixed offset ensures 100% deterministic sensor jitter."""
        sim = GPSSimulator()
        road_lat = 18.519600
        road_lon = 73.843600

        lat1, lon1 = sim.apply_noise(road_lat, road_lon, deterministic_offset_meters=(2.0, -1.5))
        lat2, lon2 = sim.apply_noise(road_lat, road_lon, deterministic_offset_meters=(2.0, -1.5))
        self.assertEqual(lat1, lat2)
        self.assertEqual(lon1, lon2)

    def test_pune_routes_defined_and_interpolated(self) -> None:
        """Pune routes are properly populated with valid waypoints."""
        self.assertGreater(len(FC_ROAD_ROUTE.waypoints), 3)
        self.assertGreater(FC_ROAD_ROUTE.total_distance_meters(), 1000.0)

        # Interpolate midway along FC road
        mid_lat, mid_lon, heading = FC_ROAD_ROUTE.interpolate(0.5)
        self.assertGreater(mid_lat, 18.515)
        self.assertLess(mid_lat, 18.535)
        self.assertGreaterEqual(heading, 0.0)
        self.assertLess(heading, 360.0)


if __name__ == "__main__":
    unittest.main()
