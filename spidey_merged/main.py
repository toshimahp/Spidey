"""
main.py

The Spider-Man Command Centre's entry point.

This module is ORCHESTRATION ONLY:
  1. Identify the requested operation (read menu choice)
  2. Collect any required input
  3. Perform the operation (delegate to a service)
  4. Display the result clearly (delegate to display.py)
  5. Return to the main menu

It never computes a priority score, decides a status transition, or
formats a distance itself — that logic lives in the service modules.
The application never crashes on bad input; every input path is
validated by cli_utils before it reaches a service.

Everything is menu-driven and decision-based: wherever there's a fixed
set of sensible answers (incident type, location, severity, description,
which incident to act on, what status to move it to, whether to confirm
or exit) the operator picks a number from a list rather than typing
free text. Free text only remains where a menu genuinely can't cover it
(an "Other" type/location, a custom description, or an exact headcount).
"""

from models import Severity, Status, ALLOWED_STATUS_TRANSITIONS
from incident_service import IncidentService
from priority_service import get_incidents_by_priority
from mission_service import get_next_mission
from dashboard_service import build_dashboard
import locations
import cli_utils
import display

MENU_CHOICES = {"1", "2", "3", "4", "5", "6", "7"}

OTHER_TYPE_OR_LOCATION = "Other (type manually)"
CUSTOM_DESCRIPTION = "Custom (type your own)"

# Merged from two teammates' incident-type lists (deduplicated, order kept).
INCIDENT_TYPE_OPTIONS = [
    "Fire",
    "Robbery",
    "Assault",
    "Hostage Situation",
    "Bombing Threat",
    "Vehicle Collision",
    "Chemical Spill",
    "Accident",
    "Medical Emergency",
    "Missing Person",
    "Suspicious Activity",
    OTHER_TYPE_OR_LOCATION,
]

DESCRIPTION_PRESET_OPTIONS = [
    "Situation ongoing, details unclear",
    "Multiple witnesses reporting activity",
    "Suspect(s) still on scene",
    "Structure or vehicle involved, response required",
    "Civilians require immediate assistance",
    CUSTOM_DESCRIPTION,
]


def _choose_incident_type():
    incident_type = cli_utils.prompt_choice(
        "Incident type:", INCIDENT_TYPE_OPTIONS, allow_cancel=True
    )
    if incident_type is None:
        return None
    if incident_type == OTHER_TYPE_OR_LOCATION:
        return cli_utils.prompt_free_text("Enter incident type: ")
    return incident_type


def _choose_location():
    location_options = locations.get_known_location_names() + [OTHER_TYPE_OR_LOCATION]
    location = cli_utils.prompt_choice("Location:", location_options, allow_cancel=True)
    if location is None:
        return None
    if location == OTHER_TYPE_OR_LOCATION:
        # Locations now have to sit on the road network (needed for real
        # routing/distance), so a typed-in name is matched against it
        # case-insensitively instead of being accepted as-is.
        while True:
            typed = cli_utils.prompt_free_text("Enter location: ")
            matched = locations.match_location_name(typed)
            if matched is not None:
                return matched
            print(f"'{typed}' isn't on the map. Known locations:")
            for name in locations.get_known_location_names():
                print(f"  - {name}")
            print()
    return location


def _choose_severity():
    severity_labels = [severity.value for severity in Severity]
    chosen_label = cli_utils.prompt_choice(
        "Severity:", severity_labels, allow_cancel=False
    )
    return Severity(chosen_label)


def _choose_description():
    description = cli_utils.prompt_choice(
        "Description:", DESCRIPTION_PRESET_OPTIONS, allow_cancel=False
    )
    if description == CUSTOM_DESCRIPTION:
        return cli_utils.prompt_free_text("Enter description: ")
    return description


def handle_report_incident(incident_service: IncidentService):
    incident_type = _choose_incident_type()
    if incident_type is None:
        print("Report cancelled.")
        return

    location = _choose_location()
    if location is None:
        print("Report cancelled.")
        return

    # Duplicate check (same type + location, still active): merged in from
    # the intake teammate's flow. Warn, don't auto-reject — the operator
    # decides whether it's really a repeat report or a second, distinct
    # incident at the same spot.
    duplicate = incident_service.find_duplicate(incident_type, location)
    if duplicate is not None:
        display.print_duplicate_warning(duplicate)
        proceed = cli_utils.prompt_choice(
            "Continue logging this as a new incident anyway?",
            ["Yes, continue", "No, cancel"],
            allow_cancel=False,
        )
        if proceed == "No, cancel":
            print("Report cancelled.")
            return

    severity = _choose_severity()
    people_affected = cli_utils.prompt_non_negative_int("People affected (exact number): ")
    description = _choose_description()

    display.print_incident_review(incident_type, location, severity, people_affected, description)
    confirmation = cli_utils.prompt_choice(
        "Confirm this report:",
        ["Confirm and log incident", "Cancel"],
        allow_cancel=False,
    )
    if confirmation == "Cancel":
        print("Report cancelled. Nothing was logged.")
        return

    incident = incident_service.create_incident(
        incident_type=incident_type,
        location=location,
        severity=severity,
        people_affected=people_affected,
        description=description,
    )
    display.print_incident_created(incident)


def handle_view_active_incidents(incident_service: IncidentService):
    active_incidents = incident_service.get_active_incidents()
    display.print_active_incidents(active_incidents)


def handle_view_response_priority(incident_service: IncidentService):
    active_incidents = incident_service.get_active_incidents()
    scored_incidents = get_incidents_by_priority(active_incidents)
    display.print_priority_list(scored_incidents)


def handle_get_next_mission(incident_service: IncidentService):
    active_incidents = incident_service.get_active_incidents()
    mission = get_next_mission(active_incidents)
    display.print_next_mission(mission)


def _format_incident_option(incident) -> str:
    return (
        f"{incident.incident_id} | {incident.incident_type} | "
        f"{incident.location} | currently {incident.status.value}"
    )


def handle_update_incident(incident_service: IncidentService):
    # Only non-resolved incidents can ever be updated, so that's the
    # only thing offered — no way to even select something invalid.
    updatable_incidents = incident_service.get_active_incidents()
    if not updatable_incidents:
        print("There are no incidents available to update right now.")
        return

    incident = cli_utils.prompt_choice(
        "Select an incident to update:",
        updatable_incidents,
        formatter=_format_incident_option,
        allow_cancel=True,
    )
    if incident is None:
        print("Update cancelled.")
        return

    display.print_incident_lookup_result(incident)

    # Only the statuses this incident is actually allowed to move to are
    # ever shown, so an invalid transition can't be selected in the
    # first place. incident_service.update_status still re-validates
    # this as a safety net, in case this list and the service's rules
    # ever drift apart.
    allowed_next_statuses = sorted(
        ALLOWED_STATUS_TRANSITIONS[incident.status], key=lambda status: status.value
    )
    if not allowed_next_statuses:
        print(f"Incident {incident.incident_id} is RESOLVED and cannot be changed further.")
        return

    status_labels = [status.value for status in allowed_next_statuses]
    chosen_label = cli_utils.prompt_choice(
        "Select new status:", status_labels, allow_cancel=True
    )
    if chosen_label is None:
        print("Update cancelled.")
        return
    new_status = Status(chosen_label)

    success, message = incident_service.update_status(incident.incident_id, new_status)
    display.print_update_result(success, message)


def handle_view_dashboard(incident_service: IncidentService):
    all_incidents = incident_service.get_all_incidents()
    summary = build_dashboard(all_incidents)
    display.print_dashboard(summary)


def run():
    incident_service = IncidentService()

    handlers = {
        "1": handle_report_incident,
        "2": handle_view_active_incidents,
        "3": handle_view_response_priority,
        "4": handle_get_next_mission,
        "5": handle_update_incident,
        "6": handle_view_dashboard,
    }

    while True:
        display.print_main_menu()
        try:
            choice = cli_utils.prompt_menu_choice("Choose an option: ", MENU_CHOICES)
        except cli_utils.SessionEnded:
            display.print_goodbye()
            break

        if choice == "7":
            try:
                confirmation = cli_utils.prompt_choice(
                    "Are you sure you want to exit?",
                    ["Yes, exit", "No, stay in the Command Centre"],
                    allow_cancel=False,
                )
            except cli_utils.SessionEnded:
                display.print_goodbye()
                break

            if confirmation == "Yes, exit":
                display.print_goodbye()
                break
            continue

        handler = handlers[choice]
        try:
            handler(incident_service)
        except cli_utils.SessionEnded:
            display.print_goodbye()
            break
        except Exception as error:  # noqa: BLE001 - last line of defence
            # The application must never crash, even on an unexpected error.
            print(f"X Something went wrong handling that request: {error}")
            print("Returning to the main menu.")


if __name__ == "__main__":
    run()
