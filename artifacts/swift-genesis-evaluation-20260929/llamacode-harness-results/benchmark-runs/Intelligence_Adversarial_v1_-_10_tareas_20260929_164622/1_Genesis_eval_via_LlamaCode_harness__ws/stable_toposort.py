import heapq


def stable_toposort(nodes, edges):
    node_list = list(nodes)
    if len(set(node_list)) != len(node_list):
        raise ValueError("duplicate nodes")

    node_set = set(node_list)
    in_degree = {n: 0 for n in node_list}
    adjacency = {n: [] for n in node_list}

    for before, after in edges:
        if before not in node_set or after not in node_set:
            raise ValueError("edge references unknown node")
        adjacency[before].append(after)
        in_degree[after] += 1

    heap = [n for n in node_list if in_degree[n] == 0]
    heapq.heapify(heap)

    result = []
    while heap:
        node = heapq.heappop(heap)
        result.append(node)
        for nxt in adjacency[node]:
            in_degree[nxt] -= 1
            if in_degree[nxt] == 0:
                heapq.heappush(heap, nxt)

    if len(result) != len(node_list):
        raise ValueError("cycle detected")

    return result
