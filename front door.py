"""
Spider-Man Neighbourhood Response System
-----------------------------------------
Incident Intake — "The Front Door"
 
A terminal-based system that receives incident reports, validates them,
and creates properly structured incidents. All data lives in memory for
the lifetime of the program (no database, no external services).
 
Flow: REPORT -> VALIDATE -> NORMALISE -> CREATE -> STORE
"""
 
from __future__ import annotations
 
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
 
 
# ---------------------------------------------------------------------------
# Reference data (the only accepted values for each field)
# ---------------------------------------------------------------------------
 
VALID_INCIDENT_TYPES = [
    "Robbery",
    "Accident",
    "Fire",
    "Medical Emergency",
    "Missing Person",
    "Suspicious Activity",
]
 
VALID_LOCATIONS = [
    "Queens Street",
    "Midtown School",
    "City Hospital",
    "Park Avenue",
    "Queens Residence",
    "Central Mall",
    "Police Station",
    "Metro Station",
]
 
VALID_SEVERITIES = ["LOW", "MEDIUM", "HIGH", "CRITICAL"]
 
STATUS_REPORTED = "REPORTED"
 
 
# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
 
@dataclass
class Incident:
    """A single, fully-validated incident."""
 
    incident_id: str
    incident_type: str
    location: str
    severity: str
    people_affected: int
    description: str
    reported_time: datetime
    status: str = STATUS_REPORTED
 
    def display(self) -> str:
        """Human-readable summary used by the terminal UI."""
        return (
            f"{self.incident_id}\n"
            f"  Type:        {self.incident_type}\n"
            f"  Location:    {self.location}\n"
            f"  Severity:    {self.severity}\n"
            f"  People:      {self.people_affected}\n"
            f"  Description: {self.description}\n"
            f"  Reported:    {self.reported_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"  Status:      {self.status}"
        )
 
 
# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
 
class ValidationError(Exception):
    """Raised when a field fails validation. Message is shown to the user."""
 
 
def _match_case_insensitive(value: str, valid_options: list[str]) -> str:
    """Return the canonically-cased option matching `value`, or raise."""
    cleaned = value.strip()
    for option in valid_options:
        if cleaned.lower() == option.lower():
            return option
    raise ValidationError(f"'{value}' is not a recognised value.")
 
 
def validate_incident_type(value: str) -> str:
    try:
        return _match_case_insensitive(value, VALID_INCIDENT_TYPES)
    except ValidationError:
        raise ValidationError("Please select a valid incident type.")
 
 
def validate_location(value: str) -> str:
    try:
        return _match_case_insensitive(value, VALID_LOCATIONS)
    except ValidationError:
        raise ValidationError("Please select a valid neighbourhood location.")
 
 
def validate_severity(value: str) -> str:
    try:
        return _match_case_insensitive(value, VALID_SEVERITIES)
    except ValidationError:
        raise ValidationError("Severity must be LOW, MEDIUM, HIGH, or CRITICAL.")
 
 
def validate_people_affected(value: str) -> int:
    cleaned = value.strip()
    try:
        number = int(cleaned)
    except ValueError:
        raise ValidationError("People affected must be a whole number.")
    if number < 0:
        raise ValidationError("People affected cannot be negative.")
    return number
 
 
def validate_description(value: str) -> str:
    cleaned = value.strip()
    if not cleaned:
        raise ValidationError("Description cannot be empty.")
    return cleaned
 
 
# ---------------------------------------------------------------------------
# Storage (in-memory only, as required)
# ---------------------------------------------------------------------------
 
class IncidentStore:
    """Holds every incident created while the program runs."""
 
    def __init__(self) -> None:
        self._incidents: dict[str, Incident] = {}
        self._next_number = 1
 
    def _generate_id(self) -> str:
        """Auto-generate a unique, sequential incident ID (INC-001, INC-002, ...)."""
        incident_id = f"INC-{self._next_number:03d}"
        self._next_number += 1
        return incident_id
 
    def find_duplicate(self, incident_type: str, location: str) -> Optional[Incident]:
        """Return an existing incident sharing the same type and location, if any."""
        for incident in self._incidents.values():
            if incident.incident_type == incident_type and incident.location == location:
                return incident
        return None
 
    def add(
        self,
        incident_type: str,
        location: str,
        severity: str,
        people_affected: int,
        description: str,
    ) -> Incident:
        """Create and store a new incident. Always starts as REPORTED."""
        incident = Incident(
            incident_id=self._generate_id(),
            incident_type=incident_type,
            location=location,
            severity=severity,
            people_affected=people_affected,
            description=description,
            reported_time=datetime.now(),
            status=STATUS_REPORTED,
        )
        self._incidents[incident.incident_id] = incident
        return incident
 
    def get(self, incident_id: str) -> Optional[Incident]:
        return self._incidents.get(incident_id.strip().upper())
 
    def all(self) -> list[Incident]:
        return list(self._incidents.values())
 
 
# ---------------------------------------------------------------------------
# Terminal I/O helpers
# ---------------------------------------------------------------------------
 
def prompt(label: str) -> str:
    return input(f"{label}: ")
 
 
def print_options(title: str, options: list[str]) -> None:
    print(f"\n{title}:")
    for option in options:
        print(f"  - {option}")
 
 
def get_validated_field(label: str, validator, options: Optional[list[str]] = None):
    """
    Repeatedly prompt for a field until `validator` accepts it.
    Shows a clear error and re-prompts on invalid input instead of crashing.
    """
    while True:
        if options:
            print_options(label, options)
        raw_value = prompt(f"Enter {label.lower()}")
        try:
            return validator(raw_value)
        except ValidationError as error:
            print(f"  [INVALID {label.upper()}] {error}")
 
 
def confirm(question: str) -> bool:
    answer = input(f"{question} (y/n): ").strip().lower()
    return answer in ("y", "yes")
 
 
# ---------------------------------------------------------------------------
# Workflow: REPORT -> VALIDATE -> NORMALISE -> CREATE -> STORE
# ---------------------------------------------------------------------------
 
def report_incident(store: IncidentStore) -> None:
    print("\n=== INCOMING INCIDENT REPORT ===")
 
    # 1. Incident type & 2. Location (validated + normalised as they're entered)
    incident_type = get_validated_field("Incident Type", validate_incident_type, VALID_INCIDENT_TYPES)
    location = get_validated_field("Location", validate_location, VALID_LOCATIONS)
 
    # Duplicate check: same type + same location. Warn, never auto-reject.
    duplicate = store.find_duplicate(incident_type, location)
    if duplicate is not None:
        print(
            f"\n[!] POSSIBLE DUPLICATE — matches {duplicate.incident_id} "
            f"({duplicate.incident_type} at {duplicate.location})."
        )
        if not confirm("Continue anyway?"):
            print("Report discarded.")
            return
 
    # 3-5. Remaining fields
    severity = get_validated_field("Severity", validate_severity, VALID_SEVERITIES)
    people_affected = get_validated_field("People Affected", validate_people_affected)
    description = get_validated_field("Description", validate_description)
 
    # CREATE + STORE
    incident = store.add(incident_type, location, severity, people_affected, description)
 
    print("\n[OK] INCIDENT CREATED")
    print(incident.display())
 
 
def retrieve_incident(store: IncidentStore) -> None:
    incident_id = prompt("\nEnter incident ID to retrieve")
    incident = store.get(incident_id)
    if incident is None:
        print(f"[NOT FOUND] No incident with ID '{incident_id}'.")
        return
    print("\n" + incident.display())
 
 
def list_incidents(store: IncidentStore) -> None:
    incidents = store.all()
    if not incidents:
        print("\nNo incidents recorded yet.")
        return
    print(f"\n=== {len(incidents)} INCIDENT(S) ON FILE ===")
    for incident in incidents:
        print(
            f"{incident.incident_id}  {incident.incident_type:<20} "
            f"{incident.location:<18} {incident.severity:<8} {incident.status}"
        )
 
 
# ---------------------------------------------------------------------------
# Main menu
# ---------------------------------------------------------------------------
 
MENU = """
=== SPIDER-MAN NEIGHBOURHOOD RESPONSE SYSTEM — INCIDENT INTAKE ===
1. Report a new incident
2. Retrieve an incident by ID
3. List all incidents
4. Exit
"""
 
 
def main() -> None:
    store = IncidentStore()
    actions = {
        "1": report_incident,
        "2": retrieve_incident,
        "3": list_incidents,
    }
 
    while True:
        print(MENU)
        choice = prompt("Select an option").strip()
        if choice == "4":
            print("Shutting down Incident Intake. Stay safe out there.")
            break
        action = actions.get(choice)
        if action is None:
            print("Invalid option. Please choose 1-4.")
            continue
        action(store)
 
 
if __name__ == "__main__":
    main()