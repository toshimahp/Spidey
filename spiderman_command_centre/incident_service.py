"""
incident_service.py

Business logic for creating, storing, retrieving and updating incidents.
No printing, no input() calls — this module only knows about data and rules.
"""

from models import Incident, Status, ALLOWED_STATUS_TRANSITIONS


class IncidentService:
    """Owns the in-memory collection of incidents for this run."""

    def __init__(self):
        self._incidents = {}
        self._next_id_number = 1

    def _generate_incident_id(self) -> str:
        incident_id = f"INC-{self._next_id_number:03d}"
        self._next_id_number += 1
        return incident_id

    def create_incident(self, incident_type: str, location: str, severity,
                         people_affected: int, description: str) -> Incident:
        """Create, store and return a new incident."""
        incident_id = self._generate_incident_id()
        incident = Incident(
            incident_id=incident_id,
            incident_type=incident_type,
            location=location,
            severity=severity,
            people_affected=people_affected,
            description=description,
        )
        self._incidents[incident_id] = incident
        return incident

    def get_all_incidents(self):
        return list(self._incidents.values())

    def get_active_incidents(self):
        """Active = anything not yet RESOLVED."""
        return [incident for incident in self._incidents.values() if incident.is_active()]

    def get_incident_by_id(self, incident_id: str):
        return self._incidents.get(incident_id.strip().upper())

    def update_status(self, incident_id: str, new_status: Status):
        """
        Attempt to move an incident to new_status.

        Returns a tuple (success: bool, message: str) so the caller
        (the CLI layer) can decide how to display the outcome, without
        this layer knowing anything about the terminal.
        """
        incident = self.get_incident_by_id(incident_id)
        if incident is None:
            return False, f"No incident found with ID '{incident_id}'."

        if new_status == incident.status:
            return False, (
                f"Incident {incident.incident_id} is already {incident.status.value}."
            )

        allowed_next_statuses = ALLOWED_STATUS_TRANSITIONS[incident.status]
        if new_status not in allowed_next_statuses:
            return False, (
                f"Invalid status change: cannot move incident {incident.incident_id} "
                f"from {incident.status.value} to {new_status.value}."
            )

        incident.status = new_status
        return True, f"Incident {incident.incident_id} updated to {new_status.value}."
