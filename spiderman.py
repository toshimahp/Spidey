"""
Spider-Man Neighbourhood Mission Planner
=========================================
Determines which incident Spider-Man should respond to, given his
current location and a list of active incidents.

Mission Score = Priority - Distance

Tie-breakers (when scores are equal):
    1. Higher priority wins
    2. If still equal, shorter distance wins
    3. If still equal, the older incident wins

No classes, no "self", no input() - every function takes its data as
parameters and returns a result. See run_mission_planner() at the bottom
and the __main__ block for how to call it with hardcoded arguments.

No database, no APIs, no GPS, no external map services. All location
and road data comes from CITY_MAP below.
"""

from typing import Dict, List, Optional, Tuple
import heapq

# ---------------------------------------------------------------------------
# 1. THE CITY MAP - the only source of truth for locations & roads
# ---------------------------------------------------------------------------

# Undirected, weighted graph: location -> {neighbour: distance_km}
CITY_MAP: Dict[str, Dict[str, int]] = {}


def add_road(a: str, b: str, distance: int) -> None:
    """Register a two-way road between two locations."""
    CITY_MAP.setdefault(a, {})[b] = distance
    CITY_MAP.setdefault(b, {})[a] = distance


_ROADS = [
    ("Queens Street", "Midtown School", 4),
    ("Queens Street", "City Hospital", 6),
    ("Queens Street", "Queens Residence", 3),
    ("Midtown School", "Park Avenue", 3),
    ("Midtown School", "City Hospital", 5),
    ("Park Avenue", "Queens Residence", 2),
    ("Park Avenue", "Central Mall", 4),
    ("City Hospital", "Police Station", 5),
    ("Central Mall", "Police Station", 2),
    ("Central Mall", "Metro Station", 3),
    ("Police Station", "Metro Station", 4),
]

for _a, _b, _d in _ROADS:
    add_road(_a, _b, _d)


# ---------------------------------------------------------------------------
# 2. LOCATION VALIDATION
# ---------------------------------------------------------------------------

def is_valid_location(name: str) -> bool:
    """A location is valid only if it exists on the city map."""
    return name in CITY_MAP


# ---------------------------------------------------------------------------
# 3. SHORTEST DISTANCE + ROUTE (Dijkstra)
# ---------------------------------------------------------------------------

def shortest_path(start: str, end: str) -> Optional[Tuple[int, List[str]]]:
    """
    Return (distance, route) for the shortest path between two locations,
    or None if the destination is unreachable.

    If start == end, distance is 0 and the route is a single-location list
    (Spider-Man is already there).
    """
    if start == end:
        return 0, [start]

    distances: Dict[str, int] = {start: 0}
    previous: Dict[str, str] = {}
    visited = set()
    queue: List[Tuple[int, str]] = [(0, start)]

    while queue:
        current_dist, current = heapq.heappop(queue)
        if current in visited:
            continue
        visited.add(current)

        if current == end:
            break

        for neighbour, road_dist in CITY_MAP.get(current, {}).items():
            new_dist = current_dist + road_dist
            if neighbour not in distances or new_dist < distances[neighbour]:
                distances[neighbour] = new_dist
                previous[neighbour] = current
                heapq.heappush(queue, (new_dist, neighbour))

    if end not in distances:
        return None  # unreachable

    route = [end]
    while route[-1] != start:
        route.append(previous[route[-1]])
    route.reverse()
    return distances[end], route


# ---------------------------------------------------------------------------
# 4. INCIDENTS + MISSION SCORING
#    Plain dictionaries, not classes:
#
#    incident = {
#        "incident_id": str,
#        "location": str,
#        "priority": int,
#        "order": int,   # position in the input list, for "older incident wins"
#    }
#
#    mission = {
#        "incident": incident,
#        "distance": int,
#        "route": [str, ...],
#        "score": int,
#    }
# ---------------------------------------------------------------------------

def make_incident(incident_id: str, location: str, priority: int, order: int) -> dict:
    return {
        "incident_id": incident_id,
        "location": location,
        "priority": priority,
        "order": order,
    }


def build_incidents(raw_incidents: List[Tuple[str, str, int]]) -> List[dict]:
    """
    Turn a plain parameter list of (incident_id, location, priority) tuples
    into incident dicts, assigning "order" from their position in the list.
    """
    return [
        make_incident(incident_id, location, priority, order)
        for order, (incident_id, location, priority) in enumerate(raw_incidents)
    ]


def evaluate_mission(spiderman_location: str, incident: dict) -> Optional[dict]:
    """Build a mission dict for one incident. Returns None if unreachable."""
    result = shortest_path(spiderman_location, incident["location"])
    if result is None:
        return None
    distance, route = result
    score = incident["priority"] - distance
    return {
        "incident": incident,
        "distance": distance,
        "route": route,
        "score": score,
    }


def mission_sort_key(mission: dict) -> Tuple[int, int, int, int]:
    """
    Sort key for ranking missions best -> worst.
    Best = highest score, then highest priority, then shortest distance,
    then oldest incident (lowest 'order').
    """
    incident = mission["incident"]
    return (
        -mission["score"],
        -incident["priority"],
        mission["distance"],
        incident["order"],
    )


def recommend_mission(
    spiderman_location: str, incidents: List[dict]
) -> Tuple[Optional[dict], List[dict], List[dict]]:
    """
    Evaluate every incident and return:
        - the best mission (or None if nothing is reachable)
        - all reachable missions, sorted best -> worst
        - incidents that could not be reached
    """
    reachable: List[dict] = []
    unreachable: List[dict] = []

    for incident in incidents:
        mission = evaluate_mission(spiderman_location, incident)
        if mission is None:
            unreachable.append(incident)
        else:
            reachable.append(mission)

    reachable.sort(key=mission_sort_key)
    best = reachable[0] if reachable else None
    return best, reachable, unreachable


# ---------------------------------------------------------------------------
# 5. REPORTING (still parameter-driven - no input(), just formatting)
# ---------------------------------------------------------------------------

def format_mission_report(
    spiderman_location: str,
    best: Optional[dict],
    reachable: List[dict],
    unreachable: List[dict],
) -> str:
    """Build the human-readable mission report as a single string."""
    lines = []
    lines.append("=" * 60)
    lines.append("MISSION REPORT")
    lines.append("=" * 60)
    lines.append(f"Spider-Man's location: {spiderman_location}")

    for mission in reachable:
        incident = mission["incident"]
        marker = "  <-- RECOMMENDED" if mission is best else ""
        lines.append(
            f"{incident['incident_id']} ({incident['location']}): "
            f"priority {incident['priority']}, distance {mission['distance']} km, "
            f"score {mission['score']}{marker}"
        )
        lines.append(f"    route: {' -> '.join(mission['route'])}")

    for incident in unreachable:
        lines.append(
            f"{incident['incident_id']} ({incident['location']}): "
            f"UNREACHABLE from {spiderman_location}"
        )

    if best:
        lines.append(f"\nGo to {best['incident']['location']} for {best['incident']['incident_id']}.")
    else:
        lines.append("\nNo reachable incidents. Stand by.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 6. ENTRY POINT - everything comes in as parameters
# ---------------------------------------------------------------------------

def run_mission_planner(
    spiderman_location: str,
    raw_incidents: List[Tuple[str, str, int]],
) -> str:
    """
    Run the full mission planner from parameters alone.

    spiderman_location: name of Spider-Man's current location
    raw_incidents: list of (incident_id, location, priority) tuples

    Returns the mission report as a string. Invalid locations are reported
    without crashing.
    """
    if not is_valid_location(spiderman_location):
        return f"'{spiderman_location}' is not a valid location. The application must not crash."

    incidents = build_incidents(raw_incidents)

    valid_incidents = []
    invalid_reports = []
    for incident in incidents:
        if is_valid_location(incident["location"]):
            valid_incidents.append(incident)
        else:
            invalid_reports.append(
                f"{incident['incident_id']} ({incident['location']}): INVALID LOCATION"
            )

    best, reachable, unreachable = recommend_mission(spiderman_location, valid_incidents)
    report = format_mission_report(spiderman_location, best, reachable, unreachable)

    if invalid_reports:
        report += "\n" + "\n".join(invalid_reports)

    return report


if __name__ == "__main__":
    # Example call using the worked example from the mission brief.
    # Everything is passed in as parameters - nothing is read from input().
    report = run_mission_planner(
        spiderman_location="Queens Street",
        raw_incidents=[
            ("INC-014", "City Hospital", 47),
            ("INC-009", "Midtown School", 42),
        ],
    )
    print(report)