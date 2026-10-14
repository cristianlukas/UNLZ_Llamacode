"""Deterministic incident report from ISO-8601 UTC events."""

import math
from datetime import datetime, timezone

SEVERITIES = ("critical", "high", "medium", "low")


def _parse_iso_utc(value, field, event_id):
    if not isinstance(value, str):
        raise ValueError(f"invalid {field} timestamp on event {event_id!r}")
    if not value.endswith("Z"):
        raise ValueError(f"invalid {field} timestamp on event {event_id!r}: must end with 'Z'")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        raise ValueError(f"invalid {field} timestamp on event {event_id!r}: {value!r}")
    return parsed.replace(tzinfo=timezone.utc)


def build_report(events):
    """Build a deterministic incident report.

    Each event has: service, severity in {critical, high, medium, low},
    started_at (ISO UTC with 'Z'), resolved_at (ISO UTC with 'Z' or None),
    and id.

    Returns a dict with:
      - 'incidents': sorted by severity desc, started_at asc, id asc; each
        entry has id, service, severity, started_at, resolved_at and
        duration_minutes (int, rounded up; None for open incidents);
      - 'open_count': number of unresolved incidents;
      - 'critical_open_count': open incidents with severity 'critical';
      - 'services': alphabetically sorted list of services.

    Raises ValueError on invalid timestamps or unknown severity. The input is
    not mutated. Standard library only.
    """
    incidents = []
    open_count = 0
    critical_open_count = 0
    services = set()

    for event in events:
        if not isinstance(event, dict):
            raise ValueError("each event must be a dict")
        event_id = event.get("id")
        severity = event.get("severity")
        if severity not in SEVERITIES:
            raise ValueError(f"invalid severity on event {event_id!r}: {severity!r}")

        started = _parse_iso_utc(event.get("started_at"), "started_at", event_id)
        resolved_raw = event.get("resolved_at")
        resolved = None
        if resolved_raw is not None:
            resolved = _parse_iso_utc(resolved_raw, "resolved_at", event_id)
            if resolved < started:
                raise ValueError(
                    f"resolved_at before started_at on event {event_id!r}"
                )

        service = event.get("service")
        if not isinstance(service, str):
            raise ValueError(f"invalid service on event {event_id!r}")
        services.add(service)

        if resolved is None:
            duration = None
            open_count += 1
            if severity == "critical":
                critical_open_count += 1
        else:
            seconds = (resolved - started).total_seconds()
            duration = int(math.ceil(seconds / 60))

        incidents.append({
            "id": event_id,
            "service": service,
            "severity": severity,
            "started_at": event["started_at"],
            "resolved_at": resolved_raw,
            "duration_minutes": duration,
        })

    incidents.sort(key=lambda item: (
        SEVERITIES.index(item["severity"]),
        item["started_at"],
        str(item["id"]),
    ))

    return {
        "incidents": incidents,
        "open_count": open_count,
        "critical_open_count": critical_open_count,
        "services": sorted(services),
    }
