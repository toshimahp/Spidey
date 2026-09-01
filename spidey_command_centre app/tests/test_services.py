"""
tests/test_services.py

Unit tests against the service layer directly — no input(), no printing,
no terminal involved. These exercise exactly the scenarios called out in
the brief's test checklist: every service function, valid and invalid
status transitions, invalid incident IDs, invalid status updates, empty
input/empty state, multiple incidents, no active incidents, no available
mission, and the two worked examples from the spec (priority 47 / mission
score 41 for a HIGH incident with 17 people, 6 km from HQ).
"""

import unittest

from models import Incident, Severity, Status, ALLOWED_STATUS_TRANSITIONS
from incident_service import IncidentService
from priority_service import calculate_priority_score, get_incidents_by_priority
from mission_service import calculate_mission_score, get_next_mission
from dashboard_service import build_dashboard
import locations


# ---------------------------------------------------------------------
# incident_service
# ---------------------------------------------------------------------

class TestIncidentService(unittest.TestCase):
    def setUp(self):
        self.service = IncidentService()

    def test_create_incident_generates_sequential_ids(self):
        first = self.service.create_incident("Fire", "City Hospital", Severity.HIGH, 5, "test")
        second = self.service.create_incident("Robbery", "Central Mall", Severity.LOW, 0, "test")
        self.assertEqual(first.incident_id, "INC-001")
        self.assertEqual(second.incident_id, "INC-002")
        self.assertEqual(first.status, Status.REPORTED)

    def test_get_active_incidents_excludes_resolved(self):
        a = self.service.create_incident("Fire", "City Hospital", Severity.HIGH, 5, "test")
        b = self.service.create_incident("Robbery", "Central Mall", Severity.LOW, 0, "test")
        self.service.update_status(a.incident_id, Status.IN_PROGRESS)
        self.service.update_status(a.incident_id, Status.RESOLVED)

        active = self.service.get_active_incidents()
        self.assertIn(b, active)
        self.assertNotIn(a, active)

    def test_get_active_incidents_empty_when_no_incidents(self):
        self.assertEqual(self.service.get_active_incidents(), [])
        self.assertEqual(self.service.get_all_incidents(), [])

    def test_get_incident_by_id_found_and_not_found(self):
        created = self.service.create_incident("Fire", "City Hospital", Severity.HIGH, 5, "test")
        self.assertEqual(self.service.get_incident_by_id(created.incident_id), created)
        self.assertEqual(self.service.get_incident_by_id("  inc-001  "), created)  # case/space tolerant
        self.assertIsNone(self.service.get_incident_by_id("INC-999"))

    def test_valid_status_transitions(self):
        incident = self.service.create_incident("Fire", "City Hospital", Severity.HIGH, 5, "test")

        success, _ = self.service.update_status(incident.incident_id, Status.IN_PROGRESS)
        self.assertTrue(success)
        self.assertEqual(incident.status, Status.IN_PROGRESS)

        success, _ = self.service.update_status(incident.incident_id, Status.RESOLVED)
        self.assertTrue(success)
        self.assertEqual(incident.status, Status.RESOLVED)

    def test_invalid_status_transition_skip_step_is_rejected(self):
        incident = self.service.create_incident("Fire", "City Hospital", Severity.HIGH, 5, "test")
        success, message = self.service.update_status(incident.incident_id, Status.RESOLVED)
        self.assertFalse(success)
        self.assertEqual(incident.status, Status.REPORTED)  # unchanged
        self.assertIn("Invalid status change", message)

    def test_invalid_status_transition_backwards_is_rejected(self):
        incident = self.service.create_incident("Fire", "City Hospital", Severity.HIGH, 5, "test")
        self.service.update_status(incident.incident_id, Status.IN_PROGRESS)
        success, _ = self.service.update_status(incident.incident_id, Status.REPORTED)
        self.assertFalse(success)
        self.assertEqual(incident.status, Status.IN_PROGRESS)

    def test_resolved_incident_cannot_change_further(self):
        incident = self.service.create_incident("Fire", "City Hospital", Severity.HIGH, 5, "test")
        self.service.update_status(incident.incident_id, Status.IN_PROGRESS)
        self.service.update_status(incident.incident_id, Status.RESOLVED)
        self.assertEqual(ALLOWED_STATUS_TRANSITIONS[Status.RESOLVED], set())

        success, _ = self.service.update_status(incident.incident_id, Status.IN_PROGRESS)
        self.assertFalse(success)

    def test_update_status_same_status_is_rejected(self):
        incident = self.service.create_incident("Fire", "City Hospital", Severity.HIGH, 5, "test")
        success, message = self.service.update_status(incident.incident_id, Status.REPORTED)
        self.assertFalse(success)
        self.assertIn("already", message)

    def test_update_status_unknown_id_is_rejected_not_crashed(self):
        success, message = self.service.update_status("INC-999", Status.IN_PROGRESS)
        self.assertFalse(success)
        self.assertIn("No incident found", message)

    def test_find_duplicate_matches_same_type_and_location(self):
        first = self.service.create_incident("Fire", "City Hospital", Severity.LOW, 1, "a")
        duplicate = self.service.find_duplicate("Fire", "City Hospital")
        self.assertEqual(duplicate, first)

    def test_find_duplicate_ignores_resolved_incidents(self):
        first = self.service.create_incident("Fire", "City Hospital", Severity.LOW, 1, "a")
        self.service.update_status(first.incident_id, Status.IN_PROGRESS)
        self.service.update_status(first.incident_id, Status.RESOLVED)
        self.assertIsNone(self.service.find_duplicate("Fire", "City Hospital"))

    def test_find_duplicate_returns_none_when_no_match(self):
        self.service.create_incident("Fire", "City Hospital", Severity.LOW, 1, "a")
        self.assertIsNone(self.service.find_duplicate("Robbery", "City Hospital"))
        self.assertIsNone(self.service.find_duplicate("Fire", "Central Mall"))


# ---------------------------------------------------------------------
# priority_service
# ---------------------------------------------------------------------

class TestPriorityService(unittest.TestCase):
    def test_worked_example_high_severity_17_people(self):
        # Spec worked example: HIGH + 17 people -> 30 + 17 = 47
        incident = Incident("INC-014", "Fire", "City Hospital", Severity.HIGH, 17, "test")
        self.assertEqual(calculate_priority_score(incident), 47)

    def test_people_affected_is_capped_at_20_points(self):
        incident = Incident("INC-001", "Fire", "City Hospital", Severity.LOW, 500, "test")
        # LOW = 10, capped people contribution = 20 -> 30, not 10 + 500
        self.assertEqual(calculate_priority_score(incident), 30)

    def test_get_incidents_by_priority_orders_highest_first(self):
        low = Incident("INC-001", "Fire", "A", Severity.LOW, 0, "test")
        critical = Incident("INC-002", "Fire", "B", Severity.CRITICAL, 0, "test")
        ranked = get_incidents_by_priority([low, critical])
        self.assertEqual(ranked[0][0], critical)
        self.assertEqual(ranked[1][0], low)

    def test_get_incidents_by_priority_empty_list(self):
        self.assertEqual(get_incidents_by_priority([]), [])


# ---------------------------------------------------------------------
# mission_service
# ---------------------------------------------------------------------

class TestMissionService(unittest.TestCase):
    def test_worked_example_priority_47_distance_6_score_41(self):
        self.assertEqual(calculate_mission_score(47, 6), 41)

    def test_score_never_goes_negative(self):
        self.assertEqual(calculate_mission_score(5, 50), 0)

    def test_no_available_mission_when_no_reported_incidents(self):
        in_progress = Incident("INC-001", "Fire", "City Hospital", Severity.HIGH, 5, "t",
                                status=Status.IN_PROGRESS)
        resolved = Incident("INC-002", "Fire", "Central Mall", Severity.HIGH, 5, "t",
                             status=Status.RESOLVED)
        self.assertIsNone(get_next_mission([in_progress, resolved]))

    def test_no_available_mission_when_no_incidents_at_all(self):
        self.assertIsNone(get_next_mission([]))

    def test_picks_highest_mission_score_among_reported(self):
        near_low = Incident("INC-001", "Fire", "City Hospital", Severity.LOW, 0, "t")  # distance 6
        far_critical = Incident("INC-002", "Fire", "Metro Station", Severity.CRITICAL, 0, "t")

        best = get_next_mission([near_low, far_critical])
        self.assertIsNotNone(best)
        self.assertEqual(best["incident"], far_critical)
        self.assertEqual(best["route"][0], locations.HQ_NAME)
        self.assertEqual(best["route"][-1], "Metro Station")

    def test_worked_example_end_to_end(self):
        incident = Incident("INC-014", "Fire", "City Hospital", Severity.HIGH, 17, "t")
        best = get_next_mission([incident])
        self.assertEqual(best["priority_score"], 47)
        self.assertEqual(best["distance_km"], 6)
        self.assertEqual(best["mission_score"], 41)
        self.assertEqual(best["route"], ["Queens Street", "City Hospital"])


# ---------------------------------------------------------------------
# dashboard_service
# ---------------------------------------------------------------------

class TestDashboardService(unittest.TestCase):
    def test_empty_dashboard(self):
        summary = build_dashboard([])
        self.assertEqual(summary["total_incidents"], 0)
        self.assertEqual(summary["active_incidents"], 0)
        self.assertEqual(summary["critical_incidents"], 0)
        self.assertEqual(summary["in_progress_incidents"], 0)
        self.assertEqual(summary["resolved_incidents"], 0)

    def test_dashboard_counts_mixed_statuses(self):
        incidents = [
            Incident("INC-001", "Fire", "A", Severity.CRITICAL, 0, "t", status=Status.REPORTED),
            Incident("INC-002", "Fire", "B", Severity.LOW, 0, "t", status=Status.IN_PROGRESS),
            Incident("INC-003", "Fire", "C", Severity.HIGH, 0, "t", status=Status.RESOLVED),
        ]
        summary = build_dashboard(incidents)
        self.assertEqual(summary["total_incidents"], 3)
        self.assertEqual(summary["active_incidents"], 2)  # not resolved
        self.assertEqual(summary["critical_incidents"], 1)
        self.assertEqual(summary["in_progress_incidents"], 1)
        self.assertEqual(summary["resolved_incidents"], 1)


# ---------------------------------------------------------------------
# locations (road-network routing)
# ---------------------------------------------------------------------

class TestLocations(unittest.TestCase):
    def test_is_valid_location(self):
        self.assertTrue(locations.is_valid_location("City Hospital"))
        self.assertFalse(locations.is_valid_location("Gotham"))

    def test_match_location_name_case_insensitive(self):
        self.assertEqual(locations.match_location_name("city hospital"), "City Hospital")
        self.assertEqual(locations.match_location_name("  CITY HOSPITAL  "), "City Hospital")
        self.assertIsNone(locations.match_location_name("Gotham"))

    def test_shortest_path_matches_worked_example(self):
        distance, route = locations.shortest_path("Queens Street", "City Hospital")
        self.assertEqual(distance, 6)
        self.assertEqual(route, ["Queens Street", "City Hospital"])

    def test_shortest_path_multi_hop(self):
        distance, route = locations.shortest_path("Queens Street", "Metro Station")
        self.assertEqual(route[0], "Queens Street")
        self.assertEqual(route[-1], "Metro Station")
        self.assertGreater(len(route), 2)  # genuinely multi-hop, not a straight line
        self.assertGreater(distance, 0)

    def test_shortest_path_same_start_and_end(self):
        distance, route = locations.shortest_path("Queens Street", "Queens Street")
        self.assertEqual(distance, 0)
        self.assertEqual(route, ["Queens Street"])

    def test_shortest_path_unreachable_location_returns_none(self):
        # A location with no roads registered at all is unreachable.
        locations.CITY_MAP.setdefault("Isolated Rooftop", {})
        try:
            self.assertIsNone(locations.shortest_path("Queens Street", "Isolated Rooftop"))
        finally:
            del locations.CITY_MAP["Isolated Rooftop"]


if __name__ == "__main__":
    unittest.main()
