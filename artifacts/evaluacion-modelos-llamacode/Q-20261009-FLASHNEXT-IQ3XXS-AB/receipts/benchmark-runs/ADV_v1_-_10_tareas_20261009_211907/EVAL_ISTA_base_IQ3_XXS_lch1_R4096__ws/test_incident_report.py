import copy

from incident_report import build_report

# vacio
assert build_report([]) == {
    "incidents": [], "open_count": 0, "critical_open_count": 0, "services": []}

# un elemento: resuelto con redondeo hacia arriba (ceil)
one = [{
    "id": "a", "service": "api", "severity": "high",
    "started_at": "2026-01-01T00:00:00Z",
    "resolved_at": "2026-01-01T00:00:01Z",
}]
result = build_report(one)
assert result["incidents"][0]["duration_minutes"] == 1, result
assert isinstance(result["incidents"][0]["duration_minutes"], int)
assert result["open_count"] == 0 and result["critical_open_count"] == 0
assert result["services"] == ["api"]

# abiertos: duration_minutes None, open_count y critical_open_count
events = [
    {"id": "o1", "service": "api", "severity": "critical",
     "started_at": "2026-01-01T10:00:00Z", "resolved_at": None},
    {"id": "o2", "service": "db", "severity": "low",
     "started_at": "2026-01-01T11:00:00Z", "resolved_at": None},
]
result = build_report(events)
assert result["open_count"] == 2
assert result["critical_open_count"] == 1
assert all(item["duration_minutes"] is None for item in result["incidents"])
assert all(item["resolved_at"] is None for item in result["incidents"])

# severity descendente, started_at ascendente, id ascendente
events = [
    {"id": "z", "service": "zeta", "severity": "medium",
     "started_at": "2026-01-01T09:00:00Z", "resolved_at": "2026-01-01T09:30:00Z"},
    {"id": "b", "service": "api", "severity": "critical",
     "started_at": "2026-01-01T08:00:00Z", "resolved_at": "2026-01-01T08:05:00Z"},
    {"id": "a", "service": "api", "severity": "critical",
     "started_at": "2026-01-01T08:00:00Z", "resolved_at": None},
    {"id": "c", "service": "db", "severity": "high",
     "started_at": "2026-01-01T07:00:00Z", "resolved_at": "2026-01-01T07:00:00Z"},
]
result = build_report(events)
assert [item["id"] for item in result["incidents"]] == ["a", "b", "c", "z"], result
assert [item["severity"] for item in result["incidents"]] == [
    "critical", "critical", "high", "medium"]
# ceil: 30 min exactos; 0 segundos -> 0
assert result["incidents"][0]["duration_minutes"] is None
assert result["incidents"][1]["duration_minutes"] == 5
assert result["incidents"][2]["duration_minutes"] == 0
assert result["incidents"][3]["duration_minutes"] == 30
# services alfabetico sin duplicados
assert result["services"] == ["api", "db", "zeta"]
assert result["open_count"] == 1
assert result["critical_open_count"] == 1

# ceil fraccionado: 1 segundo -> 1; 61 segundos -> 2
events = [
    {"id": "s1", "service": "api", "severity": "low",
     "started_at": "2026-01-01T00:00:00Z", "resolved_at": "2026-01-01T00:01:01Z"},
]
assert build_report(events)["incidents"][0]["duration_minutes"] == 2

# timestamps con offset ISO equivalente (misma hora UTC)
events = [
    {"id": "u", "service": "api", "severity": "low",
     "started_at": "2026-01-01T00:00:00Z", "resolved_at": "2026-01-01T00:02:00Z"},
]
assert build_report(events)["incidents"][0]["duration_minutes"] == 2

# no mutacion de la entrada
events = [
    {"id": "a", "service": "api", "severity": "high",
     "started_at": "2026-01-01T00:00:00Z", "resolved_at": None},
    {"id": "b", "service": "db", "severity": "low",
     "started_at": "2026-01-01T00:00:00Z", "resolved_at": "2026-01-01T00:03:00Z"},
]
before = copy.deepcopy(events)
report = build_report(events)
report["incidents"].append({"id": "x"})
report["services"].append("mutado")
assert events == before, events

# timestamps invalidos -> ValueError
bad_time = [
    {"id": "a", "service": "api", "severity": "high",
     "started_at": "2026-01-01T00:00:00", "resolved_at": None},          # sin Z
    {"id": "b", "service": "api", "severity": "high",
     "started_at": "nope", "resolved_at": None},                        # no ISO
    {"id": "c", "service": "api", "severity": "high",
     "started_at": 12345, "resolved_at": None},                         # no string
    {"id": "d", "service": "api", "severity": "high",
     "started_at": "2026-13-01T00:00:00Z", "resolved_at": None},        # mes invalido
    {"id": "e", "service": "api", "severity": "high",
     "started_at": "2026-01-01T00:00:00Z", "resolved_at": "x"},         # resolved invalido
    {"id": "f", "service": "api", "severity": "high",
     "started_at": "2026-01-01T25:00:00Z", "resolved_at": None},        # hora invalida
]
for bad in bad_time:
    try:
        build_report([bad])
        raise AssertionError("no rechazo timestamp: {!r}".format(bad))
    except ValueError:
        pass

# eventos mal formados
bad_events = [
    [{"id": "a", "service": "api", "severity": "urgent",
      "started_at": "2026-01-01T00:00:00Z", "resolved_at": None}],      # severity invalida
    [{"id": "", "service": "api", "severity": "low",
      "started_at": "2026-01-01T00:00:00Z", "resolved_at": None}],      # id vacio
    [{"id": 7, "service": "api", "severity": "low",
      "started_at": "2026-01-01T00:00:00Z", "resolved_at": None}],      # id no string
    [{"id": "a", "service": "", "severity": "low",
      "started_at": "2026-01-01T00:00:00Z", "resolved_at": None}],      # service vacio
    [{"id": "a", "severity": "low",
      "started_at": "2026-01-01T00:00:00Z", "resolved_at": None}],      # service ausente
    ["not-a-dict"],                                                     # evento no dict
    [{"id": "a", "service": "api", "severity": "low",
      "started_at": "2026-01-01T00:00:00Z", "resolved_at": None},
     {"id": "a", "service": "api", "severity": "low",
      "started_at": "2026-01-01T00:00:00Z", "resolved_at": None}],      # id duplicado
    "abc",                                                              # events string
    None,                                                               # events None
]
for bad in bad_events:
    try:
        build_report(bad)
        raise AssertionError("no rechazo: {!r}".format(bad))
    except ValueError:
        pass

print("OK")
