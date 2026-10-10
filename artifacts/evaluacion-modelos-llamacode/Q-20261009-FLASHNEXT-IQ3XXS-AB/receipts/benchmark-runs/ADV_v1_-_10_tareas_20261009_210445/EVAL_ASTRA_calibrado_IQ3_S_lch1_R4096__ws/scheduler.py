def select_jobs(jobs, now, capacity):
    selected = []
    selected_ids = set()
    remaining = capacity

    known_ids = set()
    for job in jobs:
        if isinstance(job, dict) and isinstance(job.get("id"), str):
            known_ids.add(job["id"])

    pending = list(jobs)
    progressed = True
    while progressed:
        progressed = False
        best = None
        best_key = None
        for job in pending:
            if not isinstance(job, dict):
                continue
            job_id = job.get("id")
            if not isinstance(job_id, str) or job_id in selected_ids:
                continue
            deadline = job.get("deadline")
            if not isinstance(deadline, (int, float)) or isinstance(deadline, bool):
                continue
            if deadline <= now:
                continue
            cost = job.get("cost")
            if not isinstance(cost, int) or isinstance(cost, bool) or cost <= 0:
                continue
            if cost > remaining:
                continue
            priority = job.get("priority")
            if not isinstance(priority, int) or isinstance(priority, bool):
                continue
            deps = job.get("depends", [])
            if deps is None:
                deps = []
            if not isinstance(deps, list):
                continue
            if any(
                not isinstance(dep, str) or dep not in known_ids or dep not in selected_ids
                for dep in deps
            ):
                continue
            key = (-priority, deadline, job_id)
            if best is None or key < best_key:
                best = job
                best_key = key
        if best is not None:
            selected.append(best["id"])
            selected_ids.add(best["id"])
            remaining -= best["cost"]
            pending = [j for j in pending if j is not best]
            progressed = True

    return selected
