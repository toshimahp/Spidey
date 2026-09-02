"""
locations.py

Everything related to "where is this incident and how far is it from base".

Merge note:
This used to invent straight-line distances from a hashed coordinate for
any typed-in location. It's been replaced with the real road network one
of the team built for the mission planner: a small undirected, weighted
graph of actual neighbourhood locations and roads (CITY_MAP), with
Dijkstra's algorithm finding the true shortest route and distance between
any two points on it. This is strictly more realistic and it's what
produces the multi-stop routes you now see in "Next Mission" (e.g.
Queens Street -> Midtown School -> Park Avenue), not just a straight
HQ -> destination hop.

Trade-off this brings: a location must now exist on the road network to
be routable at all. Free-typed ("Other") locations are validated against
the map (case-insensitively) instead of being accepted as-is.

No database, no APIs, no GPS — CITY_MAP below is the only source of
truth, built entirely in memory when this module loads.
"""

import heapq
from typing import Dict, List, Optional, Tuple

HQ_NAME = "Queens Street"

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


def is_valid_location(name: str) -> bool:
    """A location is valid only if it exists on the city map."""
    return name in CITY_MAP


def match_location_name(value: str) -> Optional[str]:
    """
    Case-insensitive lookup: return the canonically-cased location name
    matching `value`, or None if it isn't on the map. Used to validate
    free-typed ("Other") location entries without forcing exact casing.
    """
    cleaned = value.strip()
    for known in CITY_MAP:
        if cleaned.lower() == known.lower():
            return known
    return None


def shortest_path(start: str, end: str) -> Optional[Tuple[int, List[str]]]:
    """
    Return (distance_km, route) for the shortest path between two
    locations on the road network, or None if unreachable.

    If start == end, distance is 0 and the route is a single-location list.
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


def calculate_distance_km(location_name: str) -> Optional[int]:
    """Shortest-path distance from HQ to a location, in whole kilometres."""
    result = shortest_path(HQ_NAME, location_name)
    return None if result is None else result[0]


def build_route(location_name: str) -> List[str]:
    """The real shortest route Spider-Man takes: HQ -> ... -> destination."""
    result = shortest_path(HQ_NAME, location_name)
    if result is None:
        return [HQ_NAME, location_name.strip()]
    return result[1]


def get_known_location_names():
    """
    Return the names of every location on the map except HQ itself, for
    use in a selection menu. Keeps the menu decision-driven instead of
    requiring the operator to type a location by hand every time.
    """
    return sorted(name for name in CITY_MAP if name != HQ_NAME)
