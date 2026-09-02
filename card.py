from datetime import datetime

SEVERITY_POINTS = {
    "LOW": 10,
    "MEDIUM": 20,
    "HIGH": 30,
    "CRITICAL": 40
}

LOCATION_POINTS = {
    "SCHOOL": 4,
    "HOSPITAL": 4,
    "RESIDENTIAL": 3,
    "PUBLIC": 2,
    "STREET": 1
}

incidents = []

def calculate_score(incident):
    severity_score = SEVERITY_POINTS[incident["severity"]]
    people_score = incident["people"] * 2
    location_score = LOCATION_POINTS[incident["location"]]

    return severity_score + people_score + location_score


def get_active_incidents(incidents):
    active_incidents = []

    for incident in incidents:
        if incident["status"] != "RESOLVED":
            active_incidents.append(incident)

    return active_incidents


def rank_incidents(incidents):
    for incident in incidents:
        incident["score"] = calculate_score(incident)

    incidents.sort(
        key=lambda incident: (
            -incident["score"],
            -incident["people"],
            incident["created_at"]
        )
    )

    return incidents


def display_priority_list(incidents):
    print("\n==============================")
    print("       RESPONSE PRIORITY")
    print("==============================")

    if not incidents:
        print("No active incidents.")
        return

    for position, incident in enumerate(incidents, start=1):
        print(
            f"{position}. "
            f"{incident['id']} "
            f"{incident['severity']} "
            f"Score: {incident['score']}"
        )

    print("\nNEXT RESPONSE:")
    print(incidents[0]["id"])


def add_incident(incidents):
    """Take one incident from the user."""
    incident_id = input("Incident ID: ").upper()
    severity = input("Severity (LOW/MEDIUM/HIGH/CRITICAL): ").upper()
    people = int(input("People affected: "))
    location = input(
        "Location (SCHOOL/HOSPITAL/RESIDENTIAL/PUBLIC/STREET): "
    ).upper()
    status = input("Status (ACTIVE/RESOLVED): ").upper()

    incident = {
        "id": incident_id,
        "severity": severity,
        "people": people,
        "location": location,
        "status": status,
        "created_at": datetime.now()
    }

    incidents.append(incident)
    print("Incident added successfully.")


def main():
    incidents = []

    while True:
        print("\n===== SPIDER-MAN RESPONSE SYSTEM =====")
        print("1. Add incident")
        print("2. Show response priority")
        print("3. Exit")

        choice = input("Enter your choice: ")

        if choice == "1":
            add_incident(incidents)

        elif choice == "2":
            active_incidents = get_active_incidents(incidents)
            ranked_incidents = rank_incidents(active_incidents)
            display_priority_list(ranked_incidents)

        elif choice == "3":
            print("Exiting...")
            break

        else:
            print("Invalid choice.")


if __name__ == "__main__":
    main()