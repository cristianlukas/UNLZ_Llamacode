import copy

from config_resolver import resolve_config

# forma exacta: valor tal cual (preserva tipo del valor de env)
assert resolve_config({"token": "$TOKEN"}, {"TOKEN": "abc"}) == {"token": "abc"}
assert resolve_config({"port": "$PORT"}, {"PORT": 8080}) == {"port": 8080}
assert resolve_config({"flag": "$FLAG"}, {"FLAG": True}) == {"flag": True}
assert resolve_config({"none": "$NONE"}, {"NONE": None}) == {"none": None}
assert resolve_config({"lst": "$L"}, {"L": [1, 2]}) == {"lst": [1, 2]}

# interpolacion dentro del texto (todas las variables)
assert resolve_config("hola $NAME", {"NAME": "mundo"}) == "hola mundo"
assert resolve_config("$A-$B", {"A": "1", "B": "2"}) == "1-2"
assert resolve_config({"url": "http://$HOST:$PORT/x"}, {"HOST": "h", "PORT": 9}) == {
    "url": "http://h:9/x"}
assert resolve_config("$A$A$A", {"A": "z"}) == "zzz"

# vacio
assert resolve_config({}, {}) == {}
assert resolve_config([], {}) == []
assert resolve_config("", {}) == ""

# tipos no string preservados
config = {"n": 5, "f": 1.5, "b": True, "nil": None, "arr": [1, 2]}
result = resolve_config(config, {})
assert result == {"n": 5, "f": 1.5, "b": True, "nil": None, "arr": [1, 2]}
assert isinstance(result["n"], int) and not isinstance(result["b"], str)

# recursion dicts y listas
config = {
    "db": {"host": "$HOST", "ports": [8001, 8002]},
    "tags": ["t$IDX", "plain"],
    "nested": {"deep": {"name": "$NAME"}},
    "list_of_dicts": [{"k": "$K"}],
}
env = {"HOST": "localhost", "IDX": "1", "NAME": "n", "K": "v"}
assert resolve_config(config, env) == {
    "db": {"host": "localhost", "ports": [8001, 8002]},
    "tags": ["t1", "plain"],
    "nested": {"deep": {"name": "n"}},
    "list_of_dicts": [{"k": "v"}],
}

# '$' sin nombre valido: no se expande
assert resolve_config("$", {}) == "$"
assert resolve_config("coste $100", {}) == "coste $100"
assert resolve_config("a$1", {}) == "a$1"
assert resolve_config("100$", {}) == "100$"
assert resolve_config("$-x", {}) == "$-x"
assert resolve_config("$$A", {"A": "v"}) == "$v"
assert resolve_config("$_ok", {"_ok": "v"}) == "v"

# KeyError: primera variable ausente
try:
    resolve_config({"a": "$A", "b": "$B"}, {"A": "x"})
    raise AssertionError("no lanzo KeyError")
except KeyError as exc:
    assert "B" in str(exc), str(exc)

try:
    resolve_config(["$MISSING"], {})
    raise AssertionError("no lanzo KeyError")
except KeyError as exc:
    assert "MISSING" in str(exc), str(exc)

# no muta config ni env; copia profunda independiente
config = {"a": {"b": ["x"]}, "c": "$VAR", "d": ["keep"]}
env = {"VAR": "V"}
config_before = copy.deepcopy(config)
env_before = copy.deepcopy(env)
result = resolve_config(config, env)
assert config == config_before, config
assert env == env_before, env
result["a"]["b"].append("mutado")
result["d"].append("mutado")
assert config == config_before, config

# env es un dict de variables
for bad_env in (None, "X", [], 1):
    try:
        resolve_config({"a": "x"}, bad_env)
        raise AssertionError("no rechazo env={!r}".format(bad_env))
    except ValueError:
        pass

print("OK")
