import copy
from merge_patch import apply_merge_patch

# Ejemplo clasico RFC 7396
t = {"title": "MeetingHeleading", "year": 2015,
     "author": {"firstName": "Jon", "lastName": "Smith"}}
p = {"title": "MeetingHeleading2", "category": "self-help",
     "author": {"lastName": None}, "year": 2016}
r = apply_merge_patch(t, p)
assert r == {"title": "MeetingHeleading2", "year": 2016,
             "author": {"firstName": "Jon"}, "category": "self-help"}, r

# target no-objeto + patch objeto -> se trata como {}
assert apply_merge_patch(5, {"a": 1}) == {"a": 1}
assert apply_merge_patch(None, {"a": {"b": 2}}) == {"a": {"b": 2}}

# null elimina clave (incluso anidado)
assert apply_merge_patch({"a": {"b": 1, "c": 2}}, {"a": {"b": None}}) == {"a": {"c": 2}}
assert apply_merge_patch({"a": 1, "b": 2}, {"a": None}) == {"b": 2}
assert apply_merge_patch({"a": 1}, {"a": None, "b": None}) == {}

# arrays reemplazados completos; null elimina la clave
assert apply_merge_patch({"x": [1, 2]}, {"x": [7, 8]}) == {"x": [7, 8]}
assert apply_merge_patch({"x": [1]}, {"x": None}) == {}

# entradas primitivas
assert apply_merge_patch({"a": 1}, 7) == 7
assert apply_merge_patch({"a": 1}, [1, 2]) == [1, 2]
assert apply_merge_patch([1, 2], [3]) == [3]
assert apply_merge_patch("s", "t") == "t"
assert apply_merge_patch(None, None) is None
assert apply_merge_patch({"a": 1}, {}) == {"a": 1}

# sin mutacion: target y patch intactos, resultado independiente
t2 = {"a": {"b": {"c": 1}}}
p2 = {"a": {"b": {"d": 2}}}
t2_before = copy.deepcopy(t2)
p2_before = copy.deepcopy(p2)
r2 = apply_merge_patch(t2, p2)
assert t2 == t2_before and p2 == p2_before, (t2, p2)
assert r2 == {"a": {"b": {"c": 1, "d": 2}}}
r2["a"]["b"]["c"] = 99
r2["a"]["b"]["new"] = 1
assert t2 == t2_before, t2
assert p2 == p2_before, p2

# arrays del patch tampoco quedan compartidos
p3 = {"x": [1, 2]}
r3 = apply_merge_patch({}, p3)
r3["x"].append(3)
assert p3 == {"x": [1, 2]}, p3

print("OK")
