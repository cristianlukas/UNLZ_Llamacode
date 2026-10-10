from user_query import BASE_SQL, build_user_query

BASE = "SELECT id, name, email, active FROM users"

# vacio / sin filtros: consulta base intacta
assert build_user_query({}) == (BASE, [])
assert build_user_query() == (BASE, [])
assert build_user_query(None) == (BASE, [])
assert BASE_SQL == BASE

# un elemento: name LIKE con % + valor + %
sql, params = build_user_query({"name": "ana"})
assert sql == BASE + " WHERE name LIKE ?", sql
assert params == ["%ana%"], params

# email LIKE
sql, params = build_user_query({"email": "x@y.z"})
assert sql == BASE + " WHERE email LIKE ?", sql
assert params == ["%x@y.z%"], params

# active: igualdad con bool
sql, params = build_user_query({"active": True})
assert sql == BASE + " WHERE active = ?", sql
assert params == [True], params
sql, params = build_user_query({"active": False})
assert sql == BASE + " WHERE active = ?", sql
assert params == [False], params

# los tres campos: placeholders y params en el mismo orden name, email, active
sql, params = build_user_query({"email": "e", "active": True, "name": "n"})
assert sql == BASE + " WHERE name LIKE ? AND email LIKE ? AND active = ?", sql
assert params == ["%n%", "%e%", True], params
assert sql.count("?") == len(params) == 3

# orden de clausulas no depende del orden del dict de entrada
first = build_user_query({"name": "a", "email": "b", "active": False})
second = build_user_query({"active": False, "email": "b", "name": "a"})
assert first == second, (first, second)

# valores con caracteres peligrosos: nunca se interpolan en el SQL
sql, params = build_user_query({"name": "a' OR 1=1 --"})
assert sql == BASE + " WHERE name LIKE ?", sql
assert "OR 1=1" not in sql
assert params == ["%a' OR 1=1 --%"], params

sql, params = build_user_query({"name": "x;y"})
assert sql == BASE + " WHERE name LIKE ?", sql
assert ";" not in sql

# vacio como valor de busqueda: sigue siendo placeholder
sql, params = build_user_query({"name": ""})
assert sql == BASE + " WHERE name LIKE ?", sql
assert params == ["%%"], params

# campos desconocidos
for bad in ({"rol": "admin"}, {"Name": "x"}, {"active ": True}, {"id": 1}):
    try:
        build_user_query(bad)
        raise AssertionError("no rechazo campos desconocidos: {!r}".format(bad))
    except ValueError as exc:
        assert "desconocidos" in str(exc), str(exc)

# tipos incorrectos
bad_types = [
    {"name": 123},
    {"name": None},
    {"name": ["a"]},
    {"email": 5},
    {"email": None},
    {"active": "yes"},
    {"active": 1},
    {"active": 0},
    {"active": None},
    {"name": b"bytes"},
]
for bad in bad_types:
    try:
        build_user_query(bad)
        raise AssertionError("no rechazo tipo invalido: {!r}".format(bad))
    except ValueError:
        pass

# strings con NUL
for bad in ({"name": "a\x00b"}, {"email": "\x00"}, {"name": "x\x00y"}):
    try:
        build_user_query(bad)
        raise AssertionError("no rechazo NUL: {!r}".format(bad))
    except ValueError as exc:
        assert "NUL" in str(exc), str(exc)

# filters de tipo incorrecto
for bad in ("name", 7, ["name"], b"x"):
    try:
        build_user_query(bad)
        raise AssertionError("no rechazo filters={!r}".format(bad))
    except ValueError:
        pass

print("OK")
