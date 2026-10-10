import json

from jsonl_audit import summarize_jsonl

# vacio: sin lineas
assert summarize_jsonl([]) == {
    "count": 0, "by_level": {}, "total_duration_ms": 0,
    "p95_duration_ms": None, "invalid_lines": 0}

# lineas vacias o de solo espacios: ignoradas (no cuentan como invalidas)
assert summarize_jsonl(["", "   ", "\t", "\n", " \t\r\n"]) == {
    "count": 0, "by_level": {}, "total_duration_ms": 0,
    "p95_duration_ms": None, "invalid_lines": 0}

# un elemento: camino principal
one = ['{"id": "a", "level": "info", "duration_ms": 10}']
assert summarize_jsonl(one) == {
    "count": 1, "by_level": {"info": 1}, "total_duration_ms": 10,
    "p95_duration_ms": 10, "invalid_lines": 0}

# by_level alfabetico y total entero
lines = [
    '{"id": "b", "level": "warn", "duration_ms": 5}',
    '{"id": "c", "level": "warn", "duration_ms": 5}',
    '{"id": "d", "level": "error", "duration_ms": 1}',
]
result = summarize_jsonl(lines)
assert result == {
    "count": 3, "by_level": {"error": 1, "warn": 2}, "total_duration_ms": 11,
    "p95_duration_ms": 5, "invalid_lines": 0}
assert list(result["by_level"]) == sorted(result["by_level"])
assert isinstance(result["total_duration_ms"], int)
assert isinstance(result["p95_duration_ms"], int)

# p95 nearest-rank sobre duraciones validas ordenadas
durations = list(range(1, 101))  # 1..100
lines = [json.dumps({"id": str(i), "level": "info", "duration_ms": d})
         for i, d in enumerate(durations)]
assert summarize_jsonl(lines)["p95_duration_ms"] == 95

# n=10 -> rank ceil(9.5)=10 -> valor 10
lines = [json.dumps({"id": str(i), "level": "info", "duration_ms": i}) for i in range(1, 11)]
assert summarize_jsonl(lines)["p95_duration_ms"] == 10

# n=20 -> rank ceil(19)=19
lines = [json.dumps({"id": str(i), "level": "info", "duration_ms": i}) for i in range(1, 21)]
assert summarize_jsonl(lines)["p95_duration_ms"] == 19

# JSON valido pero tipos incorrectos: invalida completa, no suma
bad_typed = [
    '{"id": "a", "level": "info", "duration_ms": "10"}',
    '{"id": "a", "level": 5, "duration_ms": 10}',
    '{"id": 7.5, "level": "info", "duration_ms": 10}',
    '{"id": "a", "level": "info", "duration_ms": 1.5}',
    '{"id": "a", "level": "info", "duration_ms": true}',
    '{"id": "a", "level": "info", "duration_ms": null}',
    '{"id": "", "level": "info", "duration_ms": 10}',
    '{"id": "a", "level": "", "duration_ms": 10}',
    '{"id": "a", "duration_ms": 10}',
    '{"level": "info", "duration_ms": 10}',
    '{"id": "a", "level": "info"}',
    '[1, 2, 3]',
    '"solo string"',
    '42',
    'null',
    'no es json',
    '{',
]
result = summarize_jsonl(bad_typed)
assert result["count"] == 0
assert result["by_level"] == {}
assert result["total_duration_ms"] == 0
assert result["p95_duration_ms"] is None
assert result["invalid_lines"] == len(bad_typed), result

# mezcla: validos + invalidos (los invalidos no suman)
mixed = [
    '{"id": "a", "level": "info", "duration_ms": 10}',
    '   ',
    'broken{',
    '{"id": "b", "level": "warn", "duration_ms": 20}',
    '{"id": "c", "level": "warn", "duration_ms": "x"}',
    '{"id": "d", "level": "warn", "duration_ms": 30}',
]
assert summarize_jsonl(mixed) == {
    "count": 3, "by_level": {"info": 1, "warn": 2}, "total_duration_ms": 60,
    "p95_duration_ms": 30, "invalid_lines": 2}

# iterable no-list (generador) y bytes
def gen():
    yield '{"id": "a", "level": "info", "duration_ms": 1}'
    yield b'{"id": "b", "level": "info", "duration_ms": 2}'
assert summarize_jsonl(gen())["count"] == 2

# no muta la entrada
payload = ['{"id": "a", "level": "info", "duration_ms": 1}', "bad"]
snapshot = list(payload)
summarize_jsonl(payload)
assert payload == snapshot, payload

# lines como string: rechazado (iterar un string char a char no tiene sentido)
for bad_input in ("abc", b"abc"):
    try:
        summarize_jsonl(bad_input)
        raise AssertionError("no rechazo {!r}".format(bad_input))
    except ValueError:
        pass

print("OK")
