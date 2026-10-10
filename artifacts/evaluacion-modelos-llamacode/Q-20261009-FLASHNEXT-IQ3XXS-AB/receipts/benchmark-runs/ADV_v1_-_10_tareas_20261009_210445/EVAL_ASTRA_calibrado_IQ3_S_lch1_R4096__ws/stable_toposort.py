"""Deterministic topological sort: lexicographically smallest valid order."""

import heapq


def stable_toposort(nodes, edges):
    """Return a topological order of ``nodes`` given ``edges`` of (before, after).

    Among all valid orders, the lexicographically smallest one is produced at
    each step (min-heap over currently available nodes).

    Raises ValueError on duplicate node names, unknown endpoints or cycles.
    """
    # Materialize nodes deterministically and reject duplicates.
    ordered_nodes = []
    seen = set()
    for name in nodes:
        if name in seen:
            raise ValueError(f"duplicate node: {name!r}")
        seen.add(name)
        ordered_nodes.append(name)

    # Adjacency + in-degree, independent of input iteration order.
    successors = {name: [] for name in ordered_nodes}
    in_degree = {name: 0 for name in ordered_nodes}

    for edge in edges:
        try:
            before, after = edge
        except (TypeError, ValueError):
            raise ValueError(f"edge must be a pair: {edge!r}")
        if before not in seen:
            raise ValueError(f"unknown node in edge: {before!r}")
        if after not in seen:
            raise ValueError(f"unknown node in edge: {after!r}")
        successors[before].append(after)
        in_degree[after] += 1

    # Min-heap guarantees the lexicographically smallest available node.
    available = [name for name in ordered_nodes if in_degree[name] == 0]
    heapq.heapify(available)

    result = []
    while available:
        current = heapq.heappop(available)
        result.append(current)
        for nxt in successors[current]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                heapq.heappush(available, nxt)

    if len(result) != len(ordered_nodes):
        raise ValueError("cycle detected")

    return result
