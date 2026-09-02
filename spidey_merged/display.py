"""
display.py

All terminal output formatting lives here. This module never decides
*what* the data is (that's the service layer) and never reads input
(that's cli_utils) — it only renders things clearly for a human operator.
Nothing here ever prints a raw Python object.

Styling note:
Colour and box-drawing are purely cosmetic and applied only in this
module. Colour is auto-disabled whenever stdout isn't an interactive
terminal (e.g. when tests capture output, or when the program is piped
to a file), so nothing here can break string-matching tests or logs —
the box-drawing characters still render either way since they're plain
unicode text, not escape codes.
"""

import sys

WIDTH = 66

# --------------------------------------------------------------------
# Theme: ANSI colour codes, auto-disabled on non-interactive streams.
# --------------------------------------------------------------------
_SUPPORTS_COLOR = sys.stdout.isatty()

_RESET = "\033[0m"
_BOLD = "\033[1m"
_DIM = "\033[2m"
_CYAN = "\033[96m"
_GREEN = "\033[92m"
_RED = "\033[91m"


def _style(code: str, text: str) -> str:
    if not _SUPPORTS_COLOR:
        return text
    return f"{code}{text}{_RESET}"


def _bold(text: str) -> str:
    return _style(_BOLD, text)


def _dim(text: str) -> str:
    return _style(_DIM, text)


def _cyan(text: str) -> str:
    return _style(_CYAN, text)


def _green(text: str) -> str:
    return _style(_GREEN, text)


def _red(text: str) -> str:
    return _style(_RED, text)


def _field(label: str, value: str, label_width: int = 10, value_color=None) -> str:
    """Render 'Label : value' with a dim label and an optionally coloured value."""
    label_text = _dim(f"{label:<{label_width}}")
    value_text = value_color(value) if value_color else value
    return f"{label_text} : {value_text}"


# --------------------------------------------------------------------
# Banners
# --------------------------------------------------------------------

def print_banner(title: str):
    """A boxed, centred section header, e.g.

        NEXT MISSION

        +----------------------------------------------------------+
        |                                                          |
        |                     NEXT MISSION                         |
        |                                                          |
        +----------------------------------------------------------+
    """
    print()
    print(_dim(title.upper()))
    print()
    top = "+" + "-" * (WIDTH - 2) + "+"

    print(_cyan(top))
    print(_cyan("|") + " " * (WIDTH - 2) + _cyan("|"))
    print(_cyan("|") + _bold(title.upper().center(WIDTH - 2)) + _cyan("|"))
    print(_cyan("|") + " " * (WIDTH - 2) + _cyan("|"))
    print(_cyan(top))
    print()


def print_main_menu():
    print_banner("SPIDER-MAN COMMAND CENTRE")
    print("1. Report Incident")
    print("2. View Active Incidents")
    print("3. View Response Priority")
    print("4. Get Next Mission")
    print("5. Update Incident")
    print("6. View Dashboard")
    print("7. Exit")
    print(_dim("-" * WIDTH))


def print_incident_review(incident_type, location, severity, people_affected, description):
    """Show a summary of what's about to be logged, before it's confirmed."""
    print_banner("REVIEW BEFORE REPORTING")
    print(_field("Type", incident_type, 12))
    print(_field("Location", location, 12))
    print(_field("Severity", severity.value, 12))
    print(_field("People", str(people_affected), 12))
    print(_field("Description", description, 12))
    print()


def print_duplicate_warning(duplicate):
    print()
    print(_style(_RED, "[!] POSSIBLE DUPLICATE"))
    print(
        f"    Matches {_cyan(duplicate.incident_id)} "
        f"({duplicate.incident_type} at {duplicate.location}), "
        f"currently {duplicate.status.value}."
    )
    print()


def print_incident_created(incident):
    print_banner("INCIDENT REPORTED")
    print(_field("Incident ID", incident.incident_id, 12, _cyan))
    print("This has been logged and added to the active incident list.")


def print_active_incidents(incidents):
    print_banner("ACTIVE INCIDENTS")
    if not incidents:
        print("There are currently no active incidents.")
        return

    header = f"{'ID':<9}{'TYPE':<16}{'LOCATION':<18}{'SEVERITY':<10}{'PEOPLE':<8}{'STATUS':<12}"
    print(_dim(header))
    print(_dim("-" * len(header)))
    for incident in incidents:
        print(
            f"{_cyan(f'{incident.incident_id:<9}')}"
            f"{incident.incident_type[:15]:<16}"
            f"{incident.location[:17]:<18}"
            f"{incident.severity.value:<10}"
            f"{incident.people_affected:<8}"
            f"{incident.status.value:<12}"
        )


def print_priority_list(scored_incidents):
    print_banner("RESPONSE PRIORITY")
    if not scored_incidents:
        print("There are currently no active incidents to prioritise.")
        return

    header = f"{'ID':<9}{'SEVERITY':<10}{'LOCATION':<20}{'PRIORITY SCORE':<15}"
    print(_dim(header))
    print(_dim("-" * len(header)))
    for incident, score in scored_incidents:
        print(
            f"{_cyan(f'{incident.incident_id:<9}')}"
            f"{incident.severity.value:<10}"
            f"{incident.location[:19]:<20}"
            f"{_green(str(score)):<15}"
        )


def print_next_mission(mission):
    print_banner("NEXT MISSION")
    if mission is None:
        print("No available mission. All incidents are either resolved or already")
        print("in progress — nothing new to dispatch to right now.")
        return

    incident = mission["incident"]
    print(_field("Incident", incident.incident_id, 9, _cyan))
    print(_field("Location", incident.location, 9))
    print(_field("Priority", str(mission["priority_score"]), 9))
    print(_field("Distance", f"{mission['distance_km']} km", 9))
    print(_field("Score", str(mission["mission_score"]), 9, _green))
    print()
    print(_dim("Route:"))
    route = mission["route"]
    for index, stop in enumerate(route):
        print(f"{stop}")
        if index < len(route) - 1:
            print(_dim("  \u2193"))  # down arrow, HQ -> destination


def print_incident_lookup_result(incident):
    print(_field("Incident ID", incident.incident_id, 12, _cyan))
    print(_field("Type", incident.incident_type, 12))
    print(_field("Location", incident.location, 12))
    print(_field("Severity", incident.severity.value, 12))
    print(_field("Status", incident.status.value, 12))


def print_update_result(success: bool, message: str):
    print_banner("UPDATE INCIDENT")
    if success:
        print(_green("OK: ") + message)
    else:
        print(_red("X: ") + message)


def print_dashboard(summary: dict):
    print_banner("OPERATIONAL DASHBOARD")
    print(_field("Active incidents", str(summary["active_incidents"]), 19))
    print(_field("Critical incidents", str(summary["critical_incidents"]), 19, _red))
    print(_field("In progress", str(summary["in_progress_incidents"]), 19))
    print(_field("Resolved", str(summary["resolved_incidents"]), 19, _green))
    print(_field("Total logged", str(summary["total_incidents"]), 19))


def print_incident_not_found(incident_id: str):
    print(_red("X ") + f"No incident found with ID '{incident_id}'.")


def print_goodbye():
    print()
    print("Command Centre shutting down. Stay safe out there.")
    print()
