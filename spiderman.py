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


# Incidents are added directly instead of using input()
incidents = [
    {
        "id": "INC001",
        "severity": "HIGH",
        "people": 5,
        "location": "SCHOOL",
        "status": "ACTIVE",
        "created_at": datetime(2026, 9, 2, 10, 0)
    },
    {
        "id": "INC002",
        "severity": "CRITICAL",
        "people": 2,
        "location": "HOSPITAL",
        "status": "ACTIVE",
        "created_at": datetime(2026, 9, 2, 10, 30)
    },
    {
        "id": "INC003",
        "severity": "MEDIUM",
        "people": 8,
        "location": "PUBLIC",
        "status": "RESOLVED",
        "created_at": datetime(2026, 9, 2, 9, 30)
    },
    {
        "id": "INC004",
        "severity": "LOW",
        "people": 3,
        "location": "STREET",
        "status": "ACTIVE",
        "created_at": datetime(2026, 9, 2, 11, 0)
    }
]


active_incidents = get_active_incidents(incidents)
ranked_incidents = rank_incidents(active_incidents)
display_priority_list(ranked_incidents)