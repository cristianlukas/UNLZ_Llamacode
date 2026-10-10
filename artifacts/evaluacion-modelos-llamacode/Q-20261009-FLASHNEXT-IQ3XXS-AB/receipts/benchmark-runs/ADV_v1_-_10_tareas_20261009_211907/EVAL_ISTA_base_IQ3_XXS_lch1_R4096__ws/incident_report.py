"""build_report: informe deterministico de incidentes.

Orden: severity descendente (critical > high > medium > low), started_at ascendente,
id ascendente. duration_minutes: entero redondeado hacia arriba para resueltos,
None para abiertos. No muta la entrada. Timestamps invalidos -> ValueError.
Solo biblioteca estandar.
"""

import math
from datetime import datetime, timezone

sev_order = ("critical", "high", "medium", "low")


def sev_rank(value):
    return sev_order.index(value)


def parse_utc(text, field, ident):
    if not isinstance(text, str):
        raise ValueError("%s invalido para id %r: debe ser string ISO UTC con Z" % (field, ident))
    if not text.endswith("Z"):
        raise ValueError("%s invalido para id %r: falta el sufijo Z: %r" % (field, ident, text))
    try:
        stamp = datetime.fromisoformat(text[:-1] + "+00:00")
    except ValueError:
        raise ValueError("%s invalido para id %r: no es ISO valido: %r" % (field, ident, text))
    return stamp.astimezone(timezone.utc)


def check_event(event, index):
    if not isinstance(event, dict):
        raise ValueError("evento invalido en la posicion %d: debe ser un dict" % index)

    ident = event.get("id")
    if not isinstance(ident, str) or ident == "":
        raise ValueError("evento invalido en la posicion %d: id debe ser string no vacio" % index)

    svc = event.get("service")
    if not isinstance(svc, str) or svc == "":
        raise ValueError("evento invalido para id %r: service debe ser string no vacio" % ident)

    sev = event.get("severity")
    if sev not in sev_order:
        raise ValueError("evento invalido para id %r: severity invalida: %r" % (ident, sev))

    start = parse_utc(event.get("started_at"), "started_at", ident)

    raw = event.get("resolved_at", None)
    end = None if raw is None else parse_utc(raw, "resolved_at", ident)

    return {
        "id": ident,
        "service": svc,
        "severity": sev,
        "started_at": start,
        "resolved_at": end,
    }


def iso_z(stamp):
    return stamp.isoformat().replace("+00:00", "Z")


def build_report(events):
    if isinstance(events, (str, bytes)) or not isinstance(events, list):
        raise ValueError("events debe ser una lista de dicts")

    rows = [check_event(event, index) for index, event in enumerate(events)]

    used = set()
    for row in rows:
        if row["id"] in used:
            raise ValueError("id duplicado: %r" % row["id"])
        used.add(row["id"])

    rows.sort(key=lambda row: (sev_rank(row["severity"]), row["started_at"], row["id"]))

    incidents = []
    opens = 0
    critical_opens = 0

    for row in rows:
        end = row["resolved_at"]
        if end is None:
            minutes = None
            opens += 1
            if row["severity"] == "critical":
                critical_opens += 1
        else:
            seconds = (end - row["started_at"]).total_seconds()
            minutes = int(math.ceil(seconds / 60.0))

        incidents.append({
            "id": row["id"],
            "service": row["service"],
            "severity": row["severity"],
            "started_at": iso_z(row["started_at"]),
            "resolved_at": iso_z(end) if end is not None else None,
            "duration_minutes": minutes,
            "open": end is None,
        })

    return {
        "incidents": incidents,
        "open_count": opens,
        "critical_open_count": critical_opens,
        "services": sorted({row["service"] for row in rows}),
    }
