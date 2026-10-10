import copy

from scheduler import select_jobs

# vacio / capacidad cero
assert select_jobs([], 0, 10) == []
assert select_jobs([{"id": "a", "priority": 5, "deadline": 100, "cost": 1}], 0, 0) == []

# un elemento: vencido (deadline <= now) excluido
assert select_jobs([{"id": "a", "priority": 5, "deadline": 10, "cost": 1}], 10, 10) == []
assert select_jobs([{"id": "a", "priority": 5, "deadline": 11, "cost": 1}], 10, 10) == ["a"]

# priority descendente, deadline ascendente, id ascendente
jobs = [
    {"id": "a", "priority": 1, "deadline": 5, "cost": 1},
    {"id": "b", "priority": 2, "deadline": 7, "cost": 1},
    {"id": "c", "priority": 2, "deadline": 7, "cost": 1},
    {"id": "d", "priority": 3, "deadline": 3, "cost": 1},
]
assert select_jobs(jobs, 0, 10) == ["d", "b", "c", "a"]

# capacity total: respeta el limite y reevalua tras cada seleccion
jobs = [
    {"id": "x", "priority": 9, "deadline": 100, "cost": 6},
    {"id": "y", "priority": 8, "deadline": 100, "cost": 6},
    {"id": "z", "priority": 7, "deadline": 100, "cost": 3},
]
assert select_jobs(jobs, 0, 9) == ["x", "z"]

# dependencias faltantes / no seleccionadas
jobs = [
    {"id": "a", "priority": 9, "deadline": 100, "cost": 1},
    {"id": "b", "priority": 5, "deadline": 100, "cost": 1, "depends": ["a"]},
    {"id": "c", "priority": 5, "deadline": 100, "cost": 1, "depends": ["noexiste"]},
]
assert select_jobs(jobs, 0, 10) == ["a", "b"]

# dependencia vencida: su dependiente queda excluido
jobs = [
    {"id": "a", "priority": 9, "deadline": 5, "cost": 1},
    {"id": "b", "priority": 9, "deadline": 100, "cost": 1, "depends": ["a"]},
    {"id": "c", "priority": 1, "deadline": 100, "cost": 1},
]
assert select_jobs(jobs, 5, 10) == ["c"]

# reevaluacion: un job de menor priority se toma despues de liberar capacidad
jobs = [
    {"id": "big", "priority": 9, "deadline": 100, "cost": 10},
    {"id": "small", "priority": 8, "deadline": 100, "cost": 4},
    {"id": "after", "priority": 7, "deadline": 100, "cost": 4, "depends": ["small"]},
]
assert select_jobs(jobs, 0, 8) == ["small", "after"]

# ciclo: no bloquea a los demas
jobs = [
    {"id": "p", "priority": 9, "deadline": 100, "cost": 1, "depends": ["q"]},
    {"id": "q", "priority": 9, "deadline": 100, "cost": 1, "depends": ["p"]},
    {"id": "free", "priority": 1, "deadline": 100, "cost": 1},
]
assert select_jobs(jobs, 0, 10) == ["free"]

# ciclo largo + auto-dependencia
jobs = [
    {"id": "m", "priority": 9, "deadline": 100, "cost": 1, "depends": ["n"]},
    {"id": "n", "priority": 9, "deadline": 100, "cost": 1, "depends": ["o"]},
    {"id": "o", "priority": 9, "deadline": 100, "cost": 1, "depends": ["m"]},
    {"id": "self", "priority": 9, "deadline": 100, "cost": 1, "depends": ["self"]},
    {"id": "ok", "priority": 1, "deadline": 100, "cost": 1},
]
assert select_jobs(jobs, 0, 10) == ["ok"]

# sin mutacion de la entrada
payload = [
    {"id": "a", "priority": 1, "deadline": 100, "cost": 1},
    {"id": "b", "priority": 2, "deadline": 100, "cost": 1, "depends": ["a"]},
]
before = copy.deepcopy(payload)
result = select_jobs(payload, 0, 100)
assert result == ["a", "b"]
assert payload == before, payload
result.append("z")
assert payload == before, payload

# jobs mal formados: tipos invalidos
bad_jobs = [
    [{"id": 1, "priority": 1, "deadline": 1, "cost": 1}],
    [{"id": "a", "priority": 1.5, "deadline": 1, "cost": 1}],
    [{"id": "a", "priority": 1, "deadline": "x", "cost": 1}],
    [{"id": "a", "priority": 1, "deadline": 1, "cost": 0}],
    [{"id": "a", "priority": 1, "deadline": 1, "cost": -2}],
    [{"id": "a", "priority": 1, "deadline": 1, "cost": 1.0}],
    [{"id": "a", "priority": True, "deadline": 1, "cost": 1}],
    [{"id": "a", "priority": 1, "deadline": 1, "cost": 1, "depends": "a"}],
    [{"id": "a", "priority": 1, "deadline": 1, "cost": 1, "depends": [3]}],
    [{"id": "", "priority": 1, "deadline": 1, "cost": 1}],
    [{"id": "a", "priority": 1, "cost": 1}],
    [{"id": "a", "priority": 1, "deadline": 1, "cost": 1}, {"id": "a", "priority": 1, "deadline": 1, "cost": 1}],
    "not-a-list",
    None,
]
for bad in bad_jobs:
    try:
        select_jobs(bad, 0, 10)
        raise AssertionError("no rechazo: {!r}".format(bad))
    except ValueError:
        pass

for bad_capacity in (None, "10", -1, 1.5, True):
    try:
        select_jobs([{"id": "a", "priority": 1, "deadline": 100, "cost": 1}], 0, bad_capacity)
        raise AssertionError("no rechazo capacity={!r}".format(bad_capacity))
    except ValueError:
        pass

print("OK")
