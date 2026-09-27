"""Pre-configured authentic Pune road-aligned routes for reproducible demonstration."""

from .route import Route, Waypoint

# Route 1: FC Road (Deccan Gymkhana to Shivajinagar Agriculture College)
FC_ROAD_ROUTE = Route(
    route_id="ROUTE-PUNE-FC",
    name="FC Road Corridor",
    description="Fergusson College Road from Deccan Gymkhana to Agriculture College",
    waypoints=[
        Waypoint(latitude=18.5158, longitude=73.8418, name="Deccan Gymkhana Bus Stop", order=1),
        Waypoint(latitude=18.5196, longitude=73.8436, name="Goodluck Chowk (Pothole Demo Hotspot)", order=2),
        Waypoint(latitude=18.5235, longitude=73.8415, name="Fergusson College Main Gate", order=3),
        Waypoint(latitude=18.5278, longitude=73.8424, name="Dnyaneshwar Paduka Chowk", order=4),
        Waypoint(latitude=18.5320, longitude=73.8450, name="Agriculture College / Shivajinagar", order=5),
    ],
)

# Route 2: JM Road (Balgandharva to Sancheti Hospital Chowk)
JM_ROAD_ROUTE = Route(
    route_id="ROUTE-PUNE-JM",
    name="JM Road Corridor",
    description="Jangali Maharaj Road north-bound transit corridor",
    waypoints=[
        Waypoint(latitude=18.5222, longitude=73.8493, name="Balgandharva Rangmandir", order=1),
        Waypoint(latitude=18.5255, longitude=73.8500, name="Sambhaji Park Crossing", order=2),
        Waypoint(latitude=18.5280, longitude=73.8510, name="Modern High School / Cafe", order=3),
        Waypoint(latitude=18.5325, longitude=73.8525, name="Sancheti Hospital Chowk", order=4),
    ],
)

# Route 3: Karve Road (Deccan Gymkhana to Paud Phata)
KARVE_ROAD_ROUTE = Route(
    route_id="ROUTE-PUNE-KARVE",
    name="Karve Road Corridor",
    description="Karve Road west-bound arterial corridor towards Kothrud",
    waypoints=[
        Waypoint(latitude=18.5135, longitude=73.8385, name="Deccan Corner / Lakdi Pul", order=1),
        Waypoint(latitude=18.5110, longitude=73.8325, name="Garware College", order=2),
        Waypoint(latitude=18.5085, longitude=73.8268, name="Nal Stop (Tunnel/Offline Test Zone)", order=3),
        Waypoint(latitude=18.5060, longitude=73.8210, name="Paud Phata", order=4),
    ],
)

# Route 4: Swargate to PMC / Shivajinagar
SHIVAJI_ROAD_ROUTE = Route(
    route_id="ROUTE-PUNE-SHIVAJI",
    name="Swargate to PMC Central Corridor",
    description="Shivaji Road crossing central Pune historical core to PMC HQ",
    waypoints=[
        Waypoint(latitude=18.5018, longitude=73.8580, name="Swargate Bus Station", order=1),
        Waypoint(latitude=18.5165, longitude=73.8562, name="Dagdusheth Ganpati / Budhwar Peth", order=2),
        Waypoint(latitude=18.5218, longitude=73.8565, name="Pune Municipal Corporation (PMC)", order=3),
        Waypoint(latitude=18.5328, longitude=73.8550, name="Shivajinagar Railway Station", order=4),
    ],
)

PUNE_ROUTES = {
    "ROUTE-PUNE-FC": FC_ROAD_ROUTE,
    "ROUTE-PUNE-JM": JM_ROAD_ROUTE,
    "ROUTE-PUNE-KARVE": KARVE_ROAD_ROUTE,
    "ROUTE-PUNE-SHIVAJI": SHIVAJI_ROAD_ROUTE,
}
