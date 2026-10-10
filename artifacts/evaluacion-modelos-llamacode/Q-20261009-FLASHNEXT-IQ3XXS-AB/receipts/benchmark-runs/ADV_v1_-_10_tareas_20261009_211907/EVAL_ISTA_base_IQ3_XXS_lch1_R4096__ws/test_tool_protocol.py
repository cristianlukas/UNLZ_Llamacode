import copy

from tool_protocol import parse_tool_call

# camino principal: read_file y write_file normalizados
r1 = parse_tool_call({"method": "read_file", "args": {"path": "src/a.py"}})
assert r1 == {"method": "read_file", "args": {"path": "src/a.py"}}, r1

r2 = parse_tool_call({"method": "write_file", "args": {"path": "out.txt", "content": "hola"}})
assert r2 == {"method": "write_file", "args": {"path": "out.txt", "content": "hola"}}, r2

# dict nuevo: no muta payload y no comparte args
payload = {"method": "write_file", "args": {"path": "a", "content": "c"}}
before = copy.deepcopy(payload)
out = parse_tool_call(payload)
out["args"]["content"] = "mutado"
out["method"] = "otro"
assert payload == before, payload
assert out is not payload and out["args"] is not payload["args"]

# path relativo con '.' aceptado
assert parse_tool_call({"method": "read_file", "args": {"path": "./a/b"}}) == {
    "method": "read_file", "args": {"path": "./a/b"}}

invalid = [
    # payload no dict
    "read_file",
    None,
    42,
    [],
    [{"method": "read_file"}],
    # method ausente / desconocido / mal tipo
    {"method": "delete_file", "args": {"path": "a"}},
    {"method": "READ_FILE", "args": {"path": "a"}},
    {"args": {"path": "a"}},
    {"method": 1, "args": {"path": "a"}},
    # args ausente / mal tipo
    {"method": "read_file"},
    {"method": "read_file", "args": "src/a.py"},
    {"method": "read_file", "args": ["a"]},
    {"method": "write_file", "args": None},
    # campos requeridos ausentes
    {"method": "read_file", "args": {}},
    {"method": "write_file", "args": {"path": "a"}},
    {"method": "write_file", "args": {"content": "c"}},
    # args de tipo incorrecto
    {"method": "read_file", "args": {"path": 123}},
    {"method": "read_file", "args": {"path": None}},
    {"method": "read_file", "args": {"path": ["a"]}},
    {"method": "write_file", "args": {"path": "a", "content": 5}},
    {"method": "write_file", "args": {"path": "a", "content": None}},
    {"method": "write_file", "args": {"path": "a", "content": b"bytes"}},
    # rutas absolutas
    {"method": "read_file", "args": {"path": "/etc/passwd"}},
    {"method": "write_file", "args": {"path": "/tmp/x", "content": "c"}},
    # traversal con ..
    {"method": "read_file", "args": {"path": "../secret"}},
    {"method": "read_file", "args": {"path": "a/../b"}},
    {"method": "read_file", "args": {"path": ".."}},
    {"method": "write_file", "args": {"path": "a/../../etc/passwd", "content": "c"}},
    # NUL
    {"method": "read_file", "args": {"path": "a\x00b"}},
    {"method": "write_file", "args": {"path": "a", "content": "ok"}, "extra": 1},
    # campos extra en request o args
    {"method": "read_file", "args": {"path": "a"}, "id": 7},
    {"method": "read_file", "args": {"path": "a", "mode": "r"}},
    {"method": "write_file", "args": {"path": "a", "content": "c", "overwrite": True}},
    {"method": "read_file", "args": {"path": "a", "content": "no"}},
]

for bad in invalid:
    try:
        parse_tool_call(bad)
        raise AssertionError("no rechazo: {!r}".format(bad))
    except ValueError as exc:
        assert "tool call invalido" in str(exc), str(exc)

print("OK ({} casos invalidos)".format(len(invalid)))
