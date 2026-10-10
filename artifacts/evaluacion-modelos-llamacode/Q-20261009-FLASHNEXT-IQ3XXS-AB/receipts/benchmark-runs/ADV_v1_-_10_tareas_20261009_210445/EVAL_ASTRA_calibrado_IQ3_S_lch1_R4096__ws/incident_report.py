from datetime import datetime, timezone
from math import ceil
_SEV = {"critical": 0, "high": 1, "medium": 2, "low": 3}
def _parse_utc(value, event_id, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("invalid %s for event %r" % (field, event_id))
    text = value.strip()
    candidate = text[:-1] + "+00:00" if text[-1] in "Zz" else text
    try:
        moment = datetime.fromisoformat(candidate)
    except ValueError:
        raise ValueError("invalid %s for event %r: %r" % (field, event_id, value))
    if moment.tzinfo is None:
        raise ValueError("non-UTC %s for event %r" % (field, event_id))
    return moment.astimezone(timezone.utc)
def build_report(events):
    incidents = []
    open_count = 0
    critical_open = 0
    services = set()
    for event in events:
        if not isinstance(event, dict):
            raise ValueError("each event must be an object")
        event_id = event.get("id")
        if not isinstance(event_id, str) or not event_id:
            raise ValueError("event id must be a non-empty string")
        service = event.get("service")
        if not isinstance(service, str) or not service:
            raise ValueError("invalid service in event %r" % event_id)
        severity = event.get("severity")
        if severity not in _SEV:
            raise ValueError("invalid severity in event %r" % event_id)
        started_raw = event.get("started_at")
        started_at = _parse_utc(started_raw, event_id, "started_at")
        resolved_raw = event.get("resolved_at")
        if resolved_raw is None:
            duration = None
            open_count += 1
            if severity == "critical":
                critical_open += 1
        else:
            resolved_at = _parse_utc(resolved_raw, event_id, "resolved_at")
            if resolved_at < started_at:
                raise ValueError("resolved_at before started_at in event %r" % event_id)
            duration = int(ceil((resolved_at - started_at).total_seconds() / 60.0))
        services.add(service)
        incidents.append({
            "id": event_id,
            "service": service,
            "severity": severity,
            "started_at": started_raw.strip(),
            "resolved_at": resolved_raw.strip() if resolved_raw is not None else None,
            "duration_minutes": duration,
        })
    incidents.sort(key=lambda i: (_SEV[i["severity"]], i["started_at"], i["id"]))
    return {
        "incidents": incidents,
        "open_count": open_count,
        "critical_open_count": critical_open,
        "services": sorted(services),
    }