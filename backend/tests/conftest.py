"""Pytest fixtures for FastAPI backend test suite."""

import sys
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.main import (
    app,
    events_by_id,
    incidents_by_id,
    observations_by_id,
    tickets_by_id,
)


@pytest.fixture(autouse=True)
def clean_storage():
    """Reset prototype in-memory state between tests."""
    events_by_id.clear()
    observations_by_id.clear()
    incidents_by_id.clear()
    tickets_by_id.clear()
    yield
    events_by_id.clear()
    observations_by_id.clear()
    incidents_by_id.clear()
    tickets_by_id.clear()


@pytest.fixture
def client():
    """TestClient instance for making API calls."""
    with TestClient(app) as test_client:
        yield test_client
