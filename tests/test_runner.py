"""Tests for the master project runner and command line orchestration."""

from pathlib import Path
import unittest

from run_project import REPO_ROOT, parse_args, ServiceManager


class TestRunner(unittest.TestCase):
    """Verify master runner arguments, paths, and process orchestration logic."""

    def test_repo_root_valid(self) -> None:
        self.assertTrue((REPO_ROOT / "run_project.py").is_file())
        self.assertTrue((REPO_ROOT / "scripts" / "run_project.py").is_file())
        self.assertTrue((REPO_ROOT / "scripts" / "README.md").is_file())

    def test_obsolete_scripts_deleted(self) -> None:
        self.assertFalse((REPO_ROOT / "scripts" / "run_demo.py").exists())
        self.assertFalse((REPO_ROOT / "scripts" / "run_prototype.py").exists())
        self.assertFalse((REPO_ROOT / "scripts" / "seed_demo_data.py").exists())

    def test_default_runner_arguments(self) -> None:
        import sys
        orig_argv = sys.argv
        try:
            sys.argv = ["run_project.py"]
            args = parse_args()
            self.assertEqual(args.backend_port, 8000)
            self.assertEqual(args.backend_host, "127.0.0.1")
            self.assertEqual(args.bus1_id, "BUS-001")
            self.assertEqual(args.bus2_id, "BUS-002")
            self.assertEqual(args.bus1_port, 8001)
            self.assertEqual(args.bus2_port, 8002)
            self.assertEqual(args.route, "ROUTE-PUNE-FC")
            self.assertAlmostEqual(args.stagger_seconds, 6.0)
            self.assertFalse(args.no_browser)
            self.assertFalse(args.headless)
        finally:
            sys.argv = orig_argv

    def test_service_manager_shutdown_empty(self) -> None:
        import sys
        orig_argv = sys.argv
        try:
            sys.argv = ["run_project.py", "--no-browser", "--headless"]
            args = parse_args()
            mgr = ServiceManager(args)
            mgr.stop_all()
            self.assertTrue(mgr.shutdown_event.is_set())
        finally:
            sys.argv = orig_argv
