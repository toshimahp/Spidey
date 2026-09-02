"""
models.py

Pure data shapes for the Spider-Man Command Centre.
No business logic, no I/O, no printing — just what an Incident *is*.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class Severity(Enum):
    """Severity of a reported incident, lowest to highest."""
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

    @classmethod
    def from_menu_choice(cls, choice: str):
        """Map a 1-4 menu choice to a Severity. Returns None if invalid."""
        mapping = {
            "1": cls.LOW,
            "2": cls.MEDIUM,
            "3": cls.HIGH,
            "4": cls.CRITICAL,
        }
        return mapping.get(choice)


class Status(Enum):
    """Lifecycle status of an incident."""
    REPORTED = "REPORTED"
    IN_PROGRESS = "IN_PROGRESS"
    RESOLVED = "RESOLVED"

    @classmethod
    def from_menu_choice(cls, choice: str):
        mapping = {
            "1": cls.REPORTED,
            "2": cls.IN_PROGRESS,
            "3": cls.RESOLVED,
        }
        return mapping.get(choice)


# The only status changes Spider-Man's system allows.
# REPORTED -> IN_PROGRESS -> RESOLVED. No skipping steps, no going backwards,
# nothing changes once RESOLVED.
ALLOWED_STATUS_TRANSITIONS = {
    Status.REPORTED: {Status.IN_PROGRESS},
    Status.IN_PROGRESS: {Status.RESOLVED},
    Status.RESOLVED: set(),
}


@dataclass
class Incident:
    """A single incident tracked by the response system."""
    incident_id: str
    incident_type: str
    location: str
    severity: Severity
    people_affected: int
    description: str
    status: Status = Status.REPORTED
    reported_at: datetime = field(default_factory=datetime.now)

    def is_active(self) -> bool:
        """An incident is 'active' as long as it isn't resolved."""
        return self.status != Status.RESOLVED
