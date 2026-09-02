"""
tests/test_services.py

Unit tests for the business-logic layer. These deliberately test the
service modules directly (no input(), no print()) so they run fast and
don't depend on the terminal at all.

Run with:  python -m unittest discover -s tests
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from models import Severity, Status
from incident_service import IncidentService
from priority_service import calculate_priority_score, get_incidents_by_priority
from mission_service import calculate_mission_score, get_next_mission
from dashboard_service import build_dashboard
from locations import calculate_distance_km, build_route, HQ_NAME


def make_incident(service, severity=Severity.MEDIUM, people=5, location="City Hospital"):
    return service.create_incident(
        incident_type="Robbery",
        location=location,
        severity=severity,
        people_affected=people,
        description="Test incident",
    )


class IncidentServiceTests(unittest.TestCase):
    def test_create_incident_generates_sequential_ids(self):
        service = IncidentService()
        first = make_incident(service)
        second = make_incident(service)
        self.assertEqual(first.incident_id, "INC-001")
        self.assertEqual(second.incident_id, "INC-002")

    def test_new_incident_starts_reported(self):
        service = IncidentService()
        incident = make_incident(service)
        self.assertEqual(incident.status, Status.REPORTED)

    def test_active_incidents_excludes_resolved(self):
        service = IncidentService()
        incident = make_incident(service)
        service.update_status(incident.incident_id, Status.IN_PROGRESS)
        service.update_status(incident.incident_id, Status.RESOLVED)

        other = make_incident(service)

        active = service.get_active_incidents()
        self.assertIn(other, active)
        self.assertNotIn(incident, active)

    def test_active_incidents_empty_when_none_reported(self):
        service = IncidentService()
        self.assertEqual(service.get_active_incidents(), [])

    def test_lookup_unknown_incident_returns_none(self):
        service = IncidentService()
        self.assertIsNone(service.get_incident_by_id("INC-999"))

    def test_lookup_is_case_and_whitespace_tolerant(self):
        service = IncidentService()
        incident = make_incident(service)
        found = service.get_incident_by_id(f" {incident.incident_id.lower()} ")
        self.assertEqual(found, incident)

    def test_valid_status_progression(self):
        service = IncidentService()
        incident = make_incident(service)

        ok1, _ = service.update_status(incident.incident_id, Status.IN_PROGRESS)
        ok2, _ = service.update_status(incident.incident_id, Status.RESOLVED)

        self.assertTrue(ok1)
        self.assertTrue(ok2)
        self.assertEqual(incident.status, Status.RESOLVED)

    def test_cannot_skip_from_reported_to_resolved(self):
        service = IncidentService()
        incident = make_incident(service)

        success, message = service.update_status(incident.incident_id, Status.RESOLVED)

        self.assertFalse(success)
        self.assertEqual(incident.status, Status.REPORTED)
        self.assertIn("Invalid status change", message)

    def test_cannot_move_backwards(self):
        service = IncidentService()
        incident = make_incident(service)
        service.update_status(incident.incident_id, Status.IN_PROGRESS)

        success, _ = service.update_status(incident.incident_id, Status.REPORTED)

        self.assertFalse(success)
        self.assertEqual(incident.status, Status.IN_PROGRESS)

    def test_cannot_change_status_of_resolved_incident(self):
        service = IncidentService()
        incident = make_incident(service)
        service.update_status(incident.incident_id, Status.IN_PROGRESS)
        service.update_status(incident.incident_id, Status.RESOLVED)

        success, _ = service.update_status(incident.incident_id, Status.IN_PROGRESS)

        self.assertFalse(success)

    def test_update_unknown_incident_fails_cleanly(self):
        service = IncidentService()
        success, message = service.update_status("INC-999", Status.IN_PROGRESS)
        self.assertFalse(success)
        self.assertIn("No incident found", message)

    def test_setting_same_status_is_rejected(self):
        service = IncidentService()
        incident = make_incident(service)
        success, _ = service.update_status(incident.incident_id, Status.REPORTED)
        self.assertFalse(success)


class PriorityServiceTests(unittest.TestCase):
    def test_higher_severity_scores_higher(self):
        service = IncidentService()
        low = make_incident(service, severity=Severity.LOW, people=0)
        critical = make_incident(service, severity=Severity.CRITICAL, people=0)
        self.assertGreater(calculate_priority_score(critical), calculate_priority_score(low))

    def test_people_affected_is_capped(self):
        service = IncidentService()
        incident_a = make_incident(service, severity=Severity.LOW, people=20)
        incident_b = make_incident(service, severity=Severity.LOW, people=2000)
        self.assertEqual(
            calculate_priority_score(incident_a), calculate_priority_score(incident_b)
        )

    def test_ordering_is_highest_priority_first(self):
        service = IncidentService()
        low = make_incident(service, severity=Severity.LOW, people=0)
        high = make_incident(service, severity=Severity.CRITICAL, people=10)

        ordered = get_incidents_by_priority([low, high])

        self.assertEqual(ordered[0][0], high)
        self.assertEqual(ordered[1][0], low)

    def test_ordering_empty_list_does_not_crash(self):
        self.assertEqual(get_incidents_by_priority([]), [])


class MissionServiceTests(unittest.TestCase):
    def test_mission_score_matches_example_in_spec(self):
        # Spec example: priority 47, distance 6 km -> score 41.
        self.assertEqual(calculate_mission_score(47, 6), 41)

    def test_mission_score_never_goes_negative(self):
        self.assertEqual(calculate_mission_score(5, 50), 0)

    def test_next_mission_none_when_no_active_incidents(self):
        self.assertIsNone(get_next_mission([]))

    def test_next_mission_ignores_in_progress_incidents(self):
        service = IncidentService()
        incident = make_incident(service, severity=Severity.CRITICAL, people=20)
        service.update_status(incident.incident_id, Status.IN_PROGRESS)

        mission = get_next_mission(service.get_active_incidents())
        self.assertIsNone(mission)

    def test_next_mission_picks_the_best_scoring_candidate(self):
        service = IncidentService()
        make_incident(service, severity=Severity.LOW, people=0, location="Harbor Bridge")
        best = make_incident(
            service, severity=Severity.CRITICAL, people=20, location="City Hospital"
        )

        mission = get_next_mission(service.get_active_incidents())

        self.assertEqual(mission["incident"], best)
        self.assertEqual(mission["route"], [HQ_NAME, "City Hospital"])

    def test_next_mission_with_single_incident(self):
        service = IncidentService()
        only = make_incident(service)
        mission = get_next_mission(service.get_active_incidents())
        self.assertEqual(mission["incident"], only)


class DashboardServiceTests(unittest.TestCase):
    def test_dashboard_counts_are_correct(self):
        service = IncidentService()
        make_incident(service, severity=Severity.CRITICAL)
        in_progress = make_incident(service, severity=Severity.LOW)
        service.update_status(in_progress.incident_id, Status.IN_PROGRESS)
        resolved = make_incident(service, severity=Severity.MEDIUM)
        service.update_status(resolved.incident_id, Status.IN_PROGRESS)
        service.update_status(resolved.incident_id, Status.RESOLVED)

        summary = build_dashboard(service.get_all_incidents())

        self.assertEqual(summary["total_incidents"], 3)
        self.assertEqual(summary["active_incidents"], 2)
        self.assertEqual(summary["critical_incidents"], 1)
        self.assertEqual(summary["in_progress_incidents"], 1)
        self.assertEqual(summary["resolved_incidents"], 1)

    def test_dashboard_with_no_incidents_does_not_crash(self):
        summary = build_dashboard([])
        self.assertEqual(summary["total_incidents"], 0)
        self.assertEqual(summary["active_incidents"], 0)


class LocationTests(unittest.TestCase):
    def test_known_location_distance(self):
        self.assertEqual(calculate_distance_km("City Hospital"), 6)

    def test_unknown_location_is_deterministic(self):
        first = calculate_distance_km("Some New Alley")
        second = calculate_distance_km("Some New Alley")
        self.assertEqual(first, second)

    def test_route_starts_at_hq(self):
        route = build_route("City Hospital")
        self.assertEqual(route[0], HQ_NAME)
        self.assertEqual(route[-1], "City Hospital")


if __name__ == "__main__":
    unittest.main()
