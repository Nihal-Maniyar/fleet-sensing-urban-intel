# Automated Test Suites

This directory contains cross-component integration and end-to-end tests. Component-specific unit tests live next to their respective packages (`backend/tests` and `data-demo-simulator/tests`).

## Test Organization

```text
tests/
├── README.md                      # Test suite documentation
├── test_database.py               # Database schema, operations, spatial queries & idempotency (10 tests)
└── test_integration_pipeline.py  # End-to-end integration: Simulator -> Ingestion -> Replay -> Ticket (4 tests)

backend/tests/
├── conftest.py                    # TestClient fixtures
└── test_api.py                    # FastAPI endpoints, validation, duplicate rejection (9 tests)

data-demo-simulator/tests/
├── test_cli.py                    # Simulator CLI & transport modes (3 tests)
├── test_contract.py               # v1 contract strict compliance (10 tests)
├── test_gps.py                    # GPS noise, road-aligned snapping & Pune routes (6 tests)
├── test_scenarios.py              # 5 deterministic scenarios validation (5 tests)
└── test_sqlite_wal.py             # SQLite WAL mode outbox & idempotent replay (4 tests)
```

## Running Tests

Run the complete test suite (51 tests) across all packages using pytest inside the virtual environment:

```bash
pytest -v
```

Or run individual suites:

```bash
# Integration tests
pytest tests/test_integration_pipeline.py -v

# Database tests
pytest tests/test_database.py -v

# Backend API tests
pytest backend/tests -v

# Simulator tests
pytest data-demo-simulator/tests -v
```
