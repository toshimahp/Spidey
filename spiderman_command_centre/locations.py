"""
locations.py

Everything related to "where is this incident and how far is it from base".

Design note / assumption:
The brief forbids databases, APIs and external services, and says all
required information exists only while the program is running. There's no
real mapping API available to us, so distance is modelled with a simple,
deterministic, in-memory coordinate system:

- Spider-Man's base of operations ("HQ") sits at (0, 0).
- A handful of well-known city locations have fixed coordinates.
- Any other location the user types in is assigned a deterministic
  pseudo-random coordinate (seeded from its own name), so the *same*
  location name always produces the *same* distance for the rest of
  that run — without ever touching a file, database or network.

Distance is straight-line distance in kilometres, rounded to the nearest
whole km (matches the "6 km" style shown in the spec).
"""

import hashlib
import math

HQ_NAME = "Queens Street"
HQ_COORDINATES = (0.0, 0.0)

# Known demo locations so the system feels alive out of the box.
_KNOWN_LOCATIONS = {
    HQ_NAME: HQ_COORDINATES,
    "City Hospital": (6.0, 0.0),
    "Downtown Bank": (3.0, 4.0),
    "Central Park": (-4.0, 3.0),
    "Harbor Bridge": (8.0, -6.0),
    "Old Warehouse District": (-5.0, -5.0),
    "Midtown Station": (2.0, -3.0),
}

# In-memory cache for locations we invent coordinates for on the fly.
# Lives only for the duration of the program run (no persistence).
_generated_locations = {}


def _generate_coordinates(location_name: str):
    """
    Deterministically invent coordinates for an unknown location, based on
    a hash of its name, so the distance for a given name is stable for the
    rest of this run.
    """
    digest = hashlib.sha256(location_name.strip().lower().encode()).hexdigest()
    # Take two chunks of the hash and map them onto a -15..15 km grid.
    x_raw = int(digest[0:8], 16)
    y_raw = int(digest[8:16], 16)
    x = (x_raw % 3000) / 100.0 - 15.0
    y = (y_raw % 3000) / 100.0 - 15.0
    return (x, y)


def get_coordinates(location_name: str):
    """Return (x, y) km coordinates for a location, known or invented."""
    normalised = location_name.strip()
    if normalised in _KNOWN_LOCATIONS:
        return _KNOWN_LOCATIONS[normalised]
    if normalised in _generated_locations:
        return _generated_locations[normalised]

    coordinates = _generate_coordinates(normalised)
    _generated_locations[normalised] = coordinates
    return coordinates


def calculate_distance_km(location_name: str) -> int:
    """Straight-line distance from HQ to a location, in whole kilometres."""
    x1, y1 = HQ_COORDINATES
    x2, y2 = get_coordinates(location_name)
    distance = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return round(distance)


def get_known_location_names():
    """
    Return the names of well-known locations (excluding HQ itself), for
    use in a selection menu. Keeps the menu decision-driven instead of
    requiring the operator to type a location by hand every time.
    """
    return [name for name in _KNOWN_LOCATIONS if name != HQ_NAME]


def build_route(location_name: str):
    """Return the route Spider-Man takes: HQ -> incident location."""
    return [HQ_NAME, location_name.strip()]
