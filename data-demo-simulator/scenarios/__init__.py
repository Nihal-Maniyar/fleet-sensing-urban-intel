"""Deterministic simulation scenarios for integration, testing, and demonstrations."""

from .base import (
    BaseEmitter,
    BaseScenario,
    CompositeEmitter,
    FileEmitter,
    HTTPEmitter,
    MQTTEmitter,
    SQLiteEmitter,
    StdoutEmitter,
)
from .connectivity_outage import ConnectivityOutageScenario
from .diverse_events import DiverseEventsScenario
from .dual_bus_pothole import DualBusPotholeScenario
from .master_demo import MasterDemoScenario
from .resolution_verification import ResolutionVerificationScenario

SCENARIOS = {
    "dual_bus_pothole": DualBusPotholeScenario,
    "connectivity_outage": ConnectivityOutageScenario,
    "diverse_events": DiverseEventsScenario,
    "resolution_verification": ResolutionVerificationScenario,
    "master_demo": MasterDemoScenario,
}

__all__ = [
    "BaseEmitter",
    "BaseScenario",
    "StdoutEmitter",
    "FileEmitter",
    "SQLiteEmitter",
    "HTTPEmitter",
    "MQTTEmitter",
    "CompositeEmitter",
    "DualBusPotholeScenario",
    "ConnectivityOutageScenario",
    "DiverseEventsScenario",
    "ResolutionVerificationScenario",
    "MasterDemoScenario",
    "SCENARIOS",
]
