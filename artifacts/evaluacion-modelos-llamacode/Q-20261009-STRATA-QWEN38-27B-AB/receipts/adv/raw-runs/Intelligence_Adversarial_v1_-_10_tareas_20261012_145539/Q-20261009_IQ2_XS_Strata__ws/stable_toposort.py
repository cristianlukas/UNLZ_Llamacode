"""Deterministic lexicographically-smallest topological sort."""

import heapq


def stable_toposort(nodes, edges):
    """Return the lexicographically smallest valid topological order.

    - nodes: iterable of unique names.
    - edges: pairs (before, after).
    - Raises ValueError on duplicate nodes, unknown endpoints or cycles.
    """
    order = []
    for name in nodes:
        if name in order:
            raise ValueError(f"duplicate node: {name!r}")
        order.append(name)

    adjacency = {name: [] for name in order}
    indegree = {name: 0 for name in order}

    for before, after in edges:
        if before not in adjacency:
            raise ValueError(f"unknown endpoint: {before!r}")
        if after not in adjacency:
            raise ValueError(f"unknown endpoint: {after!r}")
        adjacency[before].append(after)
        indegree[after] += 1

    # Min-heap guarantees the lexicographically smallest available node
    # is emitted at every step, independent of input iteration order.
    ready = [name for name in order if indegree[name] == 0]
    heapq.heapify(ready)

    result = []
    while ready:
        name = heapq.heappop(ready)
        result.append(name)
        for neighbor in adjacency[name]:
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                heapq.heappush(ready, neighbor)

    if len(result) != len(order):
        raise ValueError("cycle detected")

    return result
