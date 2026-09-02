"""
dashboard_service.py

Business logic that summarises the current state of all incidents for
the operational dashboard. Pure aggregation, no printing.
"""

from models import Status, Severity


def build_dashboard(incidents):
    """Return a dict of summary counts for the dashboard view."""
    active = [i for i in incidents if i.is_active()]
    critical = [i for i in active if i.severity == Severity.CRITICAL]
    in_progress = [i for i in incidents if i.status == Status.IN_PROGRESS]
    resolved = [i for i in incidents if i.status == Status.RESOLVED]

    return {
        "total_incidents": len(incidents),
        "active_incidents": len(active),
        "critical_incidents": len(critical),
        "in_progress_incidents": len(in_progress),
        "resolved_incidents": len(resolved),
    }
