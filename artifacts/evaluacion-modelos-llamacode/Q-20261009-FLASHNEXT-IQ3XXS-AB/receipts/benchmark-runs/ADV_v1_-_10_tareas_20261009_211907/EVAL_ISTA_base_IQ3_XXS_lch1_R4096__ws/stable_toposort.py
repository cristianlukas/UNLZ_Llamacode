"""stable_toposort: orden topologico lexicograficamente menor (Kahn con heap)."""

import heapq


def stable_toposort(nodes, edges):
    """Devuelve el orden topologico lexicograficamente menor disponible en cada paso.

    nodes: iterable de nombres unicos.
    edges: pares (before, after).
    ValueError: nodos repetidos, endpoints inexistentes o ciclo.
    """
    names = []
    seen = set()
    for name in nodes:
        if name in seen:
            raise ValueError("nodo repetido: {!r}".format(name))
        seen.add(name)
        names.append(name)

    # Sucesores por clave: orden determinista, sin depender del orden de un set/dict.
    successors = {name: [] for name in names}
    indegree = {name: 0 for name in names}

    for edge in edges:
        try:
            before, after = edge
        except (TypeError, ValueError):
            raise ValueError("arista invalida: {!r}".format(edge))
        if before not in seen:
            raise ValueError("endpoint inexistente: {!r}".format(before))
        if after not in seen:
            raise ValueError("endpoint inexistente: {!r}".format(after))
        successors[before].append(after)
        indegree[after] += 1

    # Cola determinista: heap sobre los nombres disponibles (lexicografico).
    ready = [name for name in names if indegree[name] == 0]
    heapq.heapify(ready)

    order = []
    while ready:
        current = heapq.heappop(ready)
        order.append(current)
        for nxt in successors[current]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                heapq.heappush(ready, nxt)

    if len(order) != len(names):
        raise ValueError("el grafo tiene un ciclo")

    return order
