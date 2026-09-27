# FLEET SENSING URBAN INTELLIGENCE
## SIH 2026 Prototype — Master Development Context

You are working on the repository:

    fleet-sensing-urban-intel

This is a software prototype for SIH 2026.

The project is:

AI-Powered Mobile Urban Intelligence Platform Using Public Transport Fleet

The team is building a prototype that turns public buses into mobile
urban sensing units.

IMPORTANT:
This is a PROTOTYPE.

Prioritize:
- Working end-to-end functionality
- Simple architecture
- Clear interfaces
- Reliable integration
- Easy development
- Easy testing
- Reliable demonstration

Do NOT over-engineer this into a production enterprise platform.

============================================================
1. PROJECT VISION
============================================================

Public transport buses are mobile sensing platforms.

A bus camera/video feed is processed using Edge AI.

The system:

Camera/Video
    ↓
Edge AI
    ↓
Object Detection
    ↓
ByteTrack Tracking
    ↓
Event Generation
    ↓
Evidence Image
    ↓
GPS + Timestamp
    ↓
Central Platform
    ↓
Fleet Fusion
    ↓
Verified Incident
    ↓
Civic Ticket
    ↓
GIS Dashboard
    ↓
Authority Action
    ↓
Resolution Verification

The main story is:

    DETECT
      ↓
    LOCATE
      ↓
    VERIFY
      ↓
    FUSE
      ↓
    DISPATCH
      ↓
    RESOLVE

============================================================
2. PROTOTYPE OBJECTIVE
============================================================

The prototype must demonstrate that:

1. A bus can process a camera/video feed.
2. Edge AI detects relevant objects/events.
3. ByteTrack tracks detected objects.
4. The system generates meaningful events.
5. Each important event contains visual evidence.
6. Events contain coordinates and timestamps.
7. Multiple buses can operate simultaneously.
8. Observations from multiple buses can be fused.
9. Fleet Fusion can generate a verified incident.
10. A civic ticket can be generated.
11. The incident/ticket appears on a GIS dashboard.
12. Authorities can manage the ticket lifecycle.
13. Resolution can be supported using before/after evidence.
14. The entire system can also work using a backup simulator.

============================================================
3. TWO SIMULATORS
============================================================

There are TWO DIFFERENT simulators.

Do not combine them conceptually.

------------------------------------------------------------
3.1 ACTUAL BUS SIMULATOR
------------------------------------------------------------

The Actual Bus Simulator represents ONE BUS.

One running simulator instance = one bus.

Example:

    Simulator instance 1 → BUS-001
    Simulator instance 2 → BUS-002
    Simulator instance 3 → BUS-003

Multiple instances must be able to run simultaneously.

INPUT:

- Bus ID
- Camera feed OR uploaded video file
- Route/location information as required

PROCESSING:

    Video
      ↓
    Edge AI
      ↓
    YOLO
      ↓
    ByteTrack
      ↓
    Event Engine
      ↓
    Evidence Image
      ↓
    GPS + Timestamp
      ↓
    Event / Observation
      ↓
    MQTT/API
      ↓
    Central System

The Actual Bus Simulator must ACTUALLY run the Edge AI pipeline.

It is NOT merely a fake event generator.

The simulator UI should display:

- Current video feed
- Object detections
- Bounding boxes
- Labels
- Confidence
- ByteTrack tracking IDs
- Bus ID
- GPS/location
- Event information
- Connection status

The simulator should make it visually obvious that Edge AI is running.

------------------------------------------------------------
3.2 DATA / TEST / DEMO SIMULATOR
------------------------------------------------------------

The Data/Test/Demo Simulator is separate.

It exists for:

- Independent development
- Testing
- Integration testing
- Fleet Fusion testing
- Dashboard development
- Predictable test scenarios
- Demo backup

Every team member should be able to use it.

It can generate:

- Buses
- Routes
- GPS
- Events
- Observations
- Confidence values
- Timestamps
- Multiple-bus scenarios
- Network conditions

Example:

    BUS-001 → POTHOLE
    BUS-002 → POTHOLE
    BUS-003 → POTHOLE

with nearby coordinates and compatible timestamps.

The backup simulator must use the SAME event/observation contracts
as the Actual Bus Simulator.

The central backend must not need a separate architecture for the
backup simulator.

Conceptually:

    ACTUAL BUS SIMULATOR
             OR
    DATA/TEST/DEMO SIMULATOR
             ↓
       SAME CONTRACT
             ↓
          BACKEND
             ↓
        FLEET FUSION
             ↓
         DASHBOARD

During the final demo there must be a way to switch/toggle between:

    Actual Bus Simulator

and

    Data/Test/Demo Simulator

If the Actual Bus Simulator fails, the backup simulator must be usable
without changing the backend/dashboard architecture.

============================================================
4. EVENT / OBSERVATION / INCIDENT DISTINCTION
============================================================

These terms MUST NOT be treated as interchangeable.

EVENT:

A relevant observation generated by one bus/Edge system.

OBSERVATION:

The complete evidence associated with an event.

An observation may contain:

- Event information
- Bus ID
- Coordinates
- Timestamp
- Confidence
- Evidence image
- Other metadata

INCIDENT:

A real-world issue created from one or more related observations.

Example:

    BUS-001 → observation
    BUS-002 → observation
    BUS-003 → observation

             ↓

        FLEET FUSION

             ↓

        ONE INCIDENT

============================================================
5. EVIDENCE IMAGE
============================================================

Evidence image is a REQUIRED part of important visual events.

When Edge AI generates an event, it must generate an evidence image
showing the relevant detected object/event marked appropriately.

Example:

    Video frame
        ↓
    Detection
        ↓
    Bounding box / label
        ↓
    Evidence image

The evidence image is associated with the event/observation.

The evidence image is later used by:

- Fleet Fusion
- Incident review
- Civic ticket
- GIS dashboard
- Resolution verification

Do not remove evidence generation just to simplify integration.

============================================================
6. AI PIPELINE
============================================================

Initial pipeline:

    Video
      ↓
    OpenCV / frame processing
      ↓
    YOLO
      ↓
    Object Detection
      ↓
    ByteTrack
      ↓
    Object Tracking
      ↓
    Event Engine
      ↓
    Evidence Image
      ↓
    GPS + Timestamp
      ↓
    Event / Observation

Important:

Detection != Event

YOLO detecting an object does not automatically mean a civic event
has occurred.

The Event Engine determines when a detection/tracking result becomes
a relevant urban event.

============================================================
7. INITIAL EVENT TYPES
============================================================

The prototype should focus on a limited number of meaningful events.

Initial candidates:

- POTHOLE
- GARBAGE
- TRAFFIC_OBSTRUCTION
- PEDESTRIAN_RISK

Do not continuously expand event classes.

Implement the minimum needed for a convincing prototype.

Pothole should be the PRIMARY demonstration scenario.

============================================================
8. LOCATION / GIS REQUIREMENT
============================================================

Location accuracy is important.

The main demo MUST use realistic road-aligned coordinates.

Do NOT use arbitrary random latitude/longitude points for the primary
demonstration.

Routes should correspond to real roads.

Pune roads may be used as the primary demonstration environment.

Requirements:

- Routes should follow actual roads.
- GPS points should remain on/near the road geometry.
- Incidents should appear at realistic road locations.
- Google Maps links should point to the stored incident coordinates.

The system should visually demonstrate credible urban spatial intelligence.

============================================================
9. COMMON NAMING CONVENTION
============================================================

This is a HARD RULE.

Common names must remain identical across:

- AI
- Edge
- Simulators
- Backend
- Database
- Fleet Fusion
- Dashboard
- Tests

Use:

    BUS-001
    BUS-002
    BUS-003

Events:

    EVT-000001

Observations:

    OBS-000001

Incidents:

    INC-000001

Tickets:

    POT-2026-000001

Work orders:

    WO-2026-000001

Do not independently invent alternate formats.

For example, do NOT use:

    bus001
    BUS_001
    bus_id_001
    Bus-1

if the agreed identifier is:

    BUS-001

============================================================
10. COMMON DATA FIELD NAMES
============================================================

Use these exact names unless the team explicitly changes the contract:

    bus_id
    event_id
    observation_id
    incident_id
    ticket_id
    workorder_id

    event_type
    confidence

    latitude
    longitude

    timestamp

    evidence_image

Do NOT independently create alternatives such as:

    gps_lat
    lat_value
    gps_longitude
    bus_identifier
    event_image

Consistency is more important than individual developer preference.

============================================================
11. EVENT CONTRACT
============================================================

Example:

{
  "event_id": "EVT-000001",
  "bus_id": "BUS-001",
  "event_type": "POTHOLE",
  "confidence": 0.91,
  "latitude": 18.5204,
  "longitude": 73.8567,
  "timestamp": "2026-09-21T10:30:00Z",
  "evidence_image": "runtime/evidence/EVT-000001.jpg"
}

The exact final schema should be documented in:

    docs/api-contract.md

============================================================
12. FLEET FUSION
============================================================

Fleet Fusion combines observations from multiple buses.

Potential inputs:

- Event type
- Coordinates
- Timestamp
- Confidence
- Bus ID
- Evidence image
- Other event metadata

Concept:

    BUS-001
       ↓
    Observation A

    BUS-002
       ↓
    Observation B

    BUS-003
       ↓
    Observation C

          ↓

      FLEET FUSION

          ↓

     ONE INCIDENT

Fusion should consider:

- Spatial proximity
- Temporal proximity
- Event compatibility
- Confidence
- Evidence/context

The implementation should remain simple and configurable.

Do not introduce unnecessary ML complexity into Fleet Fusion.

============================================================
13. CIVIC TICKETS
============================================================

The prototype contains:

    Automated Civic Dispatch & Lifecycle Management

When an event/incident reaches the agreed confidence threshold,
the system can generate a civic ticket.

The exact threshold and exact trigger point must be centrally defined.

Do not independently implement different threshold logic in different
modules.

Ticket ID format:

    POT-YYYY-XXXXXX

Example:

    POT-2026-000001

Tickets should contain:

- Ticket ID
- Incident ID
- Issue type
- Confidence
- Latitude
- Longitude
- Road/location
- Evidence image
- Google Maps navigation link
- Estimated repair SLA
- Status
- Timestamps

============================================================
14. TICKET LIFECYCLE
============================================================

The official prototype lifecycle is:

    Reported
        ↓
    Acknowledged
        ↓
    In Progress
        ↓
    Resolved

Do not create alternative status names.

============================================================
15. AUTOMATED DISPATCH
============================================================

Ticket/dispatch information should contain:

- Unique ticket ID
- Photo evidence
- Road coordinates
- Google Maps navigation link
- Estimated repair SLA
- Current lifecycle status

The Google Maps navigation URL should be generated from the stored
coordinates.

============================================================
16. RESOLUTION VERIFICATION
============================================================

The prototype should support:

    Before repair evidence
            ↓
          Repair
            ↓
    After repair proof
            ↓
       Validation
            ↓
         Resolved

The dashboard should be able to show the relevant before/after evidence.

============================================================
17. TECHNOLOGY STACK
============================================================

Use the following stack unless a documented decision changes it.

------------------------------------------------------------
AI / COMPUTER VISION
------------------------------------------------------------

Python
OpenCV
YOLO
Ultralytics
PyTorch
ByteTrack
ONNX

TensorRT may be added later for edge optimization.

Do not make TensorRT mandatory for the initial prototype.

------------------------------------------------------------
EDGE
------------------------------------------------------------

Python
OpenCV
MQTT
Paho MQTT
SQLite where local buffering is required

------------------------------------------------------------
COMMUNICATION
------------------------------------------------------------

MQTT
Mosquitto

------------------------------------------------------------
BACKEND
------------------------------------------------------------

Python
FastAPI
Pydantic
SQLAlchemy
Uvicorn

------------------------------------------------------------
DATABASE
------------------------------------------------------------

PostgreSQL
PostGIS

TimescaleDB is NOT required for the initial prototype.

------------------------------------------------------------
FLEET FUSION
------------------------------------------------------------

Python
NumPy
scikit-learn where useful
PostGIS spatial queries

------------------------------------------------------------
FRONTEND / GIS
------------------------------------------------------------

React
JavaScript
Vite
Leaflet
OpenStreetMap

------------------------------------------------------------
DEVOPS
------------------------------------------------------------

Git
GitHub
Docker
Docker Compose
GitHub Actions

============================================================
18. FINAL REPOSITORY STRUCTURE
============================================================

Create this prototype-focused structure:

fleet-sensing-urban-intel/
│
├── README.md
├── AGENTS.md
├── .gitignore
├── .env.example
├── docker-compose.yml
│
├── docs/
│   ├── architecture.md
│   ├── prototype-scope.md
│   ├── api-contract.md
│   ├── data-flow.md
│   ├── database.md
│   ├── ai-pipeline.md
│   ├── fleet-fusion.md
│   ├── simulators.md
│   ├── ticket-lifecycle.md
│   └── development.md
│
├── ai/
│   ├── models/
│   ├── datasets/
│   ├── training/
│   └── inference/
│
├── edge/
│   ├── camera/
│   ├── detection/
│   ├── tracking/
│   ├── events/
│   ├── gps/
│   ├── mqtt/
│   ├── storage/
│   └── main.py
│
├── bus-simulator/
│   ├── camera/
│   ├── ui/
│   ├── edge/
│   ├── config/
│   └── main.py
│
├── data-demo-simulator/
│   ├── buses/
│   ├── routes/
│   ├── gps/
│   ├── events/
│   ├── scenarios/
│   └── main.py
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── services/
│   │   ├── db/
│   │   └── main.py
│   └── tests/
│
├── fusion/
│   ├── clustering.py
│   ├── confidence.py
│   ├── incident.py
│   └── resolution.py
│
├── dashboard/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── utils/
│   ├── package.json
│   └── vite.config.js
│
├── database/
│   ├── schema.sql
│   ├── seed.sql
│   └── migrations/
│
├── tests/
│   ├── integration/
│   └── e2e/
│
├── scripts/
│
└── .github/
    ├── workflows/
    │   ├── ci.yml
    │   └── build.yml
    ├── ISSUE_TEMPLATE/
    │   ├── feature.md
    │   ├── bug.md
    │   └── task.md
    └── pull_request_template.md

Do not create dozens of empty production-oriented folders.

Keep the repository focused on the prototype.

============================================================
19. DOCUMENTATION
============================================================

Create and maintain:

docs/architecture.md
docs/prototype-scope.md
docs/api-contract.md
docs/data-flow.md
docs/database.md
docs/ai-pipeline.md
docs/fleet-fusion.md
docs/simulators.md
docs/ticket-lifecycle.md
docs/development.md

Documentation must describe the ACTUAL implementation.

Do not document features as implemented if they do not exist.

============================================================
20. AGENTS.MD
============================================================

Create a root AGENTS.md.

It must tell AI coding agents:

- Read README first.
- Read relevant docs before coding.
- Follow architecture.
- Follow naming conventions.
- Do not change API contracts without approval.
- Do not change database schema casually.
- Do not add unnecessary dependencies.
- Do not modify unrelated files.
- Add tests.
- Preserve existing tests.
- Never commit secrets.
- Human must review AI-generated code.
- Report files changed.
- Report tests run.
- Report limitations.
- Do not redesign the project.

The root AGENTS.md is the primary instruction file for coding agents.

============================================================
21. README.MD
============================================================

Create a concise root README containing:

- Project name
- SIH problem
- Project purpose
- Architecture summary
- Main components
- Two simulators
- Technology stack
- Repository structure
- Development setup
- Git workflow
- Demo flow

Do not put the entire technical specification in README.

Detailed information belongs in docs/.

============================================================
22. .ENV.EXAMPLE
============================================================

Create a root .env.example containing placeholders for:

Application:
    APP_NAME
    APP_ENV
    DEBUG

Backend:
    API_HOST
    API_PORT

Database:
    POSTGRES_DB
    POSTGRES_USER
    POSTGRES_PASSWORD
    POSTGRES_HOST
    POSTGRES_PORT
    DATABASE_URL

MQTT:
    MQTT_HOST
    MQTT_PORT
    MQTT_USERNAME
    MQTT_PASSWORD
    MQTT_TOPIC_PREFIX

Frontend:
    VITE_API_URL

AI:
    MODEL_PATH
    MODEL_CONFIDENCE_THRESHOLD
    TRACKER_TYPE

Event:
    EVENT_CONFIDENCE_THRESHOLD

Fleet Fusion:
    FUSION_DISTANCE_METERS
    FUSION_TIME_WINDOW_SECONDS

Tickets:
    TICKET_CONFIDENCE_THRESHOLD
    TICKET_ID_PREFIX

Maps:
    MAP_PROVIDER
    DEFAULT_MAP_LATITUDE
    DEFAULT_MAP_LONGITUDE
    DEFAULT_MAP_ZOOM
    GOOGLE_MAPS_BASE_URL

Simulator:
    SIMULATOR_MODE
    BUS_ID
    VIDEO_SOURCE
    SIMULATOR_MQTT_ENABLED

Storage:
    EVIDENCE_STORAGE_PATH

Logging:
    LOG_LEVEL

Never put real credentials in .env.example.

============================================================
23. .GITIGNORE
============================================================

Ignore at minimum:

.env
.env.*
!.env.example

Python cache
Virtual environments
Node modules
Build output
IDE files
OS files
Logs
Temporary files
Runtime evidence
Local databases
Large AI model artifacts

Do not accidentally ignore source files.

============================================================
24. DOCKER COMPOSE
============================================================

Initial Docker Compose should provide shared infrastructure:

- PostgreSQL + PostGIS
- MQTT/Mosquitto

Later add:

- Backend
- Dashboard
- Data/Test/Demo Simulator

Do not containerize everything unnecessarily on day one.

============================================================
25. GITHUB ACTIONS / CI
============================================================

Initial CI should be simple.

On pull requests to:

- develop
- main

and pushes to:

- develop
- main

run:

1. Checkout
2. Setup Python
3. Install dependencies
4. Run tests

When the dashboard exists, also:

1. Setup Node
2. npm ci
3. npm run build

Later add:

- Integration tests
- Docker build checks
- End-to-end tests

Do not make CI excessively complicated initially.

============================================================
26. GIT WORKFLOW
============================================================

Branches:

    main
    develop
    feature/*
    fix/*
    docs/*
    test/*

Never work directly on main/develop.

Normal workflow:

    GitHub Issue
        ↓
    Create branch from develop
        ↓
    Code
        ↓
    Test
        ↓
    Commit
        ↓
    Push
        ↓
    Pull Request → develop
        ↓
    CI
        ↓
    Human review
        ↓
    Merge

main is stable/release-ready.

develop is the team integration branch.

============================================================
27. COMMIT FORMAT
============================================================

Use:

    type(scope): description

Examples:

    feat(ai): add pothole detection
    feat(edge): generate evidence image
    feat(simulator): add multi-bus support
    feat(fusion): add spatial clustering
    feat(api): add incident endpoint
    feat(gis): add incident markers

    fix(edge): correct event timestamp
    fix(gis): correct road coordinates

    test(fusion): add duplicate observation test

    docs(api): update event schema

============================================================
28. PULL REQUEST RULES
============================================================

Every PR must:

- Target develop unless specifically releasing to main.
- Solve one focused task.
- Reference a GitHub Issue.
- Pass CI.
- Avoid unrelated changes.
- Preserve API contracts.
- Follow naming conventions.
- Include tests where appropriate.
- Be reviewed by another human.

The author cannot approve their own PR.

============================================================
29. TEAM OWNERSHIP
============================================================

There are 6 members divided into 3 groups.

------------------------------------------------------------
GROUP 1 — EDGE AI + BUS SIMULATOR
------------------------------------------------------------

Member 1:
AI/ML

Responsibilities:
- YOLO
- OpenCV
- Detection
- Model inference
- AI evaluation
- Evidence generation support

Member 2:
Edge/Bus Simulator

Responsibilities:
- Actual Bus Simulator
- Video input
- Bus ID
- GPS
- ByteTrack integration
- Event packaging
- MQTT
- Local/offline behavior

Group 1 owns:

    Video
      ↓
    AI
      ↓
    Tracking
      ↓
    Event
      ↓
    Evidence
      ↓
    GPS
      ↓
    MQTT

------------------------------------------------------------
GROUP 2 — BACKEND + FLEET FUSION
------------------------------------------------------------

Member 3:
Backend

Responsibilities:
- FastAPI
- APIs
- Event ingestion
- Incident APIs
- Ticket APIs
- Dashboard APIs

Member 4:
Database + Fleet Fusion

Responsibilities:
- PostgreSQL
- PostGIS
- Database schema
- Spatial queries
- Observation grouping
- Fusion
- Incident generation
- Resolution verification

Group 2 owns:

    Event
      ↓
    API
      ↓
    Database
      ↓
    Fusion
      ↓
    Incident
      ↓
    Ticket

------------------------------------------------------------
GROUP 3 — GIS + INTEGRATION / DEVOPS
------------------------------------------------------------

Member 5:
GIS/Frontend

Responsibilities:
- React
- Leaflet
- Map
- Incidents
- Buses
- Tickets
- Evidence
- Dashboard

Member 6:
Integration/DevOps

Responsibilities:
- GitHub
- Git workflow
- GitHub Actions
- Docker
- Docker Compose
- Data/Test/Demo Simulator
- Integration testing
- Demo environment
- CI
- End-to-end integration

Group 3 owns:

    Backend API
        ↓
    React
        ↓
    GIS
        ↓
    Authority action

============================================================
30. MODULE BOUNDARIES
============================================================

Group 1 should not casually modify:

- backend
- database
- dashboard

Group 2 should not casually modify:

- AI implementation
- dashboard

Group 3 should not modify:

- AI model
- fusion algorithm
- database schema

unless an integration change has been discussed.

Use contracts/interfaces instead of directly changing another team's module.

============================================================
31. DEVELOPMENT STRATEGY
============================================================

Do NOT develop six isolated systems.

Build vertically.

FIRST VERTICAL SLICE:

    Data/Test Simulator
        ↓
    Event
        ↓
    MQTT
        ↓
    FastAPI
        ↓
    PostgreSQL
        ↓
    React
        ↓
    Map Marker

Then add:

    Actual Bus Simulator
        ↓
    YOLO
        ↓
    ByteTrack
        ↓
    Evidence

Then:

    Multiple Buses
        ↓
    Fleet Fusion
        ↓
    Incident

Then:

    Ticket
        ↓
    Lifecycle
        ↓
    Resolution

============================================================
32. FIRST IMPLEMENTATION MILESTONES
============================================================

Milestone 1:
Repository + documentation + CI

Milestone 2:
Data/Test/Demo Simulator

Milestone 3:
Backend + Database

Milestone 4:
Basic Dashboard

Milestone 5:
End-to-end simulated event flow

Milestone 6:
Actual Bus Simulator

Milestone 7:
YOLO + ByteTrack

Milestone 8:
Evidence images

Milestone 9:
Multiple buses

Milestone 10:
Fleet Fusion

Milestone 11:
Incident generation

Milestone 12:
Civic ticket lifecycle

Milestone 13:
Resolution verification

Milestone 14:
Final integrated demo

============================================================
33. FIRST END-TO-END TEST
============================================================

The first important integration test should eventually verify:

    Simulator
        ↓
    Event
        ↓
    MQTT
        ↓
    Backend
        ↓
    Database
        ↓
    API
        ↓
    Dashboard

Then:

    BUS-001
       +
    BUS-002
       +
    BUS-003
       ↓
    Fleet Fusion
       ↓
    One Incident

============================================================
34. DEMO SCENARIO
============================================================

Primary demo:

    BUS-001 detects pothole
          ↓
    Evidence image
          ↓
    GPS + timestamp
          ↓
    Event
          ↓
    BUS-002 observes same pothole
          ↓
    BUS-003 observes same pothole
          ↓
    Fleet Fusion
          ↓
    Verified incident
          ↓
    POT-2026-XXXXXX
          ↓
    GIS Dashboard
          ↓
    Google Maps navigation
          ↓
    Reported
          ↓
    Acknowledged
          ↓
    In Progress
          ↓
    Repair
          ↓
    After-repair evidence
          ↓
    Resolved

============================================================
35. DEMO FALLBACK
============================================================

The final demo must be able to switch from:

    Actual Bus Simulator

to:

    Data/Test/Demo Simulator

without changing:

- Backend
- Database
- Fleet Fusion
- Dashboard

The backup simulator is a FIRST-CLASS development component, not a
throwaway script.

============================================================
36. REFERENCE
============================================================

The team has identified the following GitHub repository as a reference
for pothole-related implementation ideas:

    https://github.com/keshavagr025/Pothole-Detection

Use it only as a reference.

Do not copy architecture blindly.

Do not assume its implementation matches this project's contracts.

Adapt useful ideas to this repository's architecture.

============================================================
37. IMPORTANT ENGINEERING RULE
============================================================

AI coding agents are implementation assistants.

They are NOT the architecture owner.

Humans decide:

- Architecture
- API contracts
- Database contracts
- Naming
- Scope
- Integration rules
- Acceptance criteria

AI may implement the approved design.

============================================================
38. TASK
============================================================

Perform task as i mention them 

Do not implement complete project just to the tasks told


Create the task cleanly so multiple developers and AI agents can
work independently.

After completing the task:

- Check the repository structure.
- Check for duplicate/conflicting files.
- Check naming consistency.
- Validate YAML.
- Validate Markdown.
- Validate configuration where possible.
- Run available tests.
- Report all files created.
- Report any assumptions.
- Report anything that still requires a human decision.
