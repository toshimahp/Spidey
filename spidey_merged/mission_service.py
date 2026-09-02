"""
mission_service.py

Business logic for recommending Spider-Man's next mission.

Design note / assumption:
A mission's score rewards high priority but penalises distance from HQ
(closer emergencies get dealt with sooner, all else being equal):

    mission_score = max(0, priority_score - distance_km)

Only undispatched incidents (status REPORTED) are considered candidates
for "next mission" — incidents already IN_PROGRESS are being handled and
wouldn't be recommended as the *next* thing to respond to.

Merge note: distance and route now come from locations.shortest_path,
the road-network (Dijkstra) routing built for the mission planner —
real multi-stop routes, not a straight HQ -> destination hop. An
incident whose location isn't reachable on the road network is skipped
as a candidate rather than crashing or being silently mis-scored.
"""

from models import Status
from priority_service import calculate_priority_score
from locations import shortest_path, HQ_NAME


def calculate_mission_score(priority_score: int, distance_km: int) -> int:
    return max(0, priority_score - distance_km)


def get_next_mission(incidents):
    """
    Pick the best next mission among REPORTED (undispatched) incidents.

    Returns a dict describing the mission, or None if there is nothing
    to recommend.
    """
    candidates = [incident for incident in incidents if incident.status == Status.REPORTED]
    if not candidates:
        return None

    best_mission = None

    for incident in candidates:
        result = shortest_path(HQ_NAME, incident.location)
        if result is None:
            # Not reachable on the road network - can't be dispatched to.
            continue
        distance_km, route = result

        priority_score = calculate_priority_score(incident)
        mission_score = calculate_mission_score(priority_score, distance_km)

        if best_mission is None or mission_score > best_mission["mission_score"]:
            best_mission = {
                "incident": incident,
                "priority_score": priority_score,
                "distance_km": distance_km,
                "mission_score": mission_score,
                "route": route,
            }

    return best_mission
