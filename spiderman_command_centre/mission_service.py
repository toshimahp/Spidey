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
"""

from models import Status
from priority_service import calculate_priority_score
from locations import calculate_distance_km, build_route


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

    best_incident = None
    best_score = None
    best_priority = None
    best_distance = None

    for incident in candidates:
        priority_score = calculate_priority_score(incident)
        distance_km = calculate_distance_km(incident.location)
        mission_score = calculate_mission_score(priority_score, distance_km)

        if best_score is None or mission_score > best_score:
            best_incident = incident
            best_score = mission_score
            best_priority = priority_score
            best_distance = distance_km

    return {
        "incident": best_incident,
        "priority_score": best_priority,
        "distance_km": best_distance,
        "mission_score": best_score,
        "route": build_route(best_incident.location),
    }
