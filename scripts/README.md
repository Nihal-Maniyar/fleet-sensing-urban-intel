# Scripts

Executable utility scripts for demonstration, testing, and development setup.

## Available Scripts

### 1. `run_demo.py` (Repeatable Demo Runner)

Executes the official target demonstration story defined in [docs/demo.md](../docs/demo.md):
- Multi-bus defect corroboration on FC Road, Pune (`BUS-001` & `BUS-002`)
- Cellular network outage, edge SQLite WAL buffering, reconnection, and idempotent replay
- Diverse urban sensing events (`POTHOLE`, `GARBAGE`, `TRAFFIC_OBSTRUCTION`, `PEDESTRIAN_RISK`)
- Incident verification & civic ticket dispatch with Google Maps directions navigation link
- Ticket status lifecycle transitions (`REPORTED` -> `ACKNOWLEDGED` -> `IN_PROGRESS` -> `RESOLVED`)
- Resolution verification with post-repair before/after visual evidence comparison

#### Usage

```bash
# Automated run with smooth delay between steps:
python3 scripts/run_demo.py --delay 0.5

# Interactive step-by-step presentation (press Enter to advance):
python3 scripts/run_demo.py --step

# Run against a live running backend server (e.g. at http://localhost:8000):
python3 scripts/run_demo.py --backend-url http://localhost:8000
```

---

### 2. `seed_demo_data.py` (Database Seeder)

Initializes PostgreSQL/PostGIS database schema and seeds representative Pune transit fleet data, registered buses, historical observations, verified incidents, and civic tickets.

#### Usage

```bash
python3 scripts/seed_demo_data.py
```
