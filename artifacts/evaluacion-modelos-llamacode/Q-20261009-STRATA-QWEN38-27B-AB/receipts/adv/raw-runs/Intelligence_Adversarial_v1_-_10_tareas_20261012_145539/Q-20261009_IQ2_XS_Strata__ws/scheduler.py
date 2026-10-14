"""Greedy deadline scheduler with dependency and capacity constraints."""


def select_jobs(jobs, now, capacity):
    """Select job ids respecting deadlines, dependencies and total capacity.

    Each job is a dict with: id (str), priority (int), deadline (number),
    cost (positive int) and optional depends (list of ids).

    Rules:
    - jobs with deadline <= now are excluded (expired);
    - jobs with missing or not-selected dependencies are excluded;
    - total selected cost must not exceed capacity;
    - among eligible candidates pick priority desc, deadline asc, id asc;
    - after each selection, dependencies and remaining capacity are
      re-evaluated;
    - cyclic dependencies never block other jobs (those jobs simply stay
      unselected);
    - the input is not mutated.
    """
    entries = []
    for job in jobs:
        entries.append({
            "id": job["id"],
            "priority": job["priority"],
            "deadline": job["deadline"],
            "cost": job["cost"],
            "depends": list(job.get("depends") or []),
        })

    by_id = {entry["id"]: entry for entry in entries}
    selected = []
    chosen_ids = set()
    remaining = capacity

    while True:
        candidates = []
        for entry in entries:
            if entry["id"] in chosen_ids:
                continue
            if entry["deadline"] <= now:
                continue
            if entry["cost"] > remaining:
                continue
            if any(dep not in chosen_ids for dep in entry["depends"]):
                continue
            candidates.append(entry)

        if not candidates:
            break

        best = min(
            candidates,
            key=lambda e: (-e["priority"], e["deadline"], e["id"]),
        )
        chosen_ids.add(best["id"])
        selected.append(best["id"])
        remaining -= best["cost"]

    return selected
