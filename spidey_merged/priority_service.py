"""
priority_service.py

Business logic for scoring and ordering incidents by response priority.

Design note / assumption:
The brief doesn't hand us an exact formula, so this uses a simple,
transparent, documented one:

    priority_score = severity_weight + min(people_affected, 20)

Where severity_weight is:
    LOW = 10, MEDIUM = 20, HIGH = 30, CRITICAL = 40

People affected contributes up to a cap of 20 points, so a single very
large number can't drown out severity, but still meaningfully raises
priority. Everything here is a pure function of an Incident, easy to
unit test and easy to explain.
"""

from models import Severity

SEVERITY_WEIGHTS = {
    Severity.LOW: 10,
    Severity.MEDIUM: 20,
    Severity.HIGH: 30,
    Severity.CRITICAL: 40,
}

PEOPLE_AFFECTED_CAP = 20


def calculate_priority_score(incident) -> int:
    """Return the priority score for a single incident."""
    severity_component = SEVERITY_WEIGHTS[incident.severity]
    people_component = min(incident.people_affected, PEOPLE_AFFECTED_CAP)
    return severity_component + people_component


def get_incidents_by_priority(incidents):
    """
    Return (incident, priority_score) pairs sorted highest priority first.
    Ties are broken by earliest reported_at (older incidents first).
    """
    scored = [(incident, calculate_priority_score(incident)) for incident in incidents]
    scored.sort(key=lambda pair: (-pair[1], pair[0].reported_at))
    return scored
