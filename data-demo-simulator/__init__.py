"""Data/Test/Demo Simulator for Fleet Sensing Urban Intelligence.

Provides deterministic, contract-valid synthetic sensing events without
computer vision dependencies for testing, backend ingestion, fleet fusion,
and demo fallback.
"""

from .events.evidence import ensure_evidence_image
from .events.generator import EventGenerator
from .events.schema import Event
from .events.storage import SQLiteOutbox
from .scenarios import (
    SCENARIOS,
    BaseEmitter,
    BaseScenario,
    ConnectivityOutageScenario,
    DiverseEventsScenario,
    DualBusPotholeScenario,
    FileEmitter,
    HTTPEmitter,
    MasterDemoScenario,
    MQTTEmitter,
    ResolutionVerificationScenario,
    SQLiteEmitter,
    StdoutEmitter,
)

__all__ = [
    "Event",
    "EventGenerator",
    "SQLiteOutbox",
    "ensure_evidence_image",
    "BaseScenario",
    "BaseEmitter",
    "StdoutEmitter",
    "FileEmitter",
    "SQLiteEmitter",
    "HTTPEmitter",
    "MQTTEmitter",
    "DualBusPotholeScenario",
    "ConnectivityOutageScenario",
    "DiverseEventsScenario",
    "ResolutionVerificationScenario",
    "MasterDemoScenario",
    "SCENARIOS",
]
