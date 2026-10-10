"""select_jobs: planificador voraz por prioridad/deadline con capacidad y dependencias.

Criterio de elegibilidad (por paso):
  - deadline > now (no vencido)
  - cost entero positivo y dentro de la capacidad restante
  - todas sus depends estan en los ids seleccionados
Criterio de eleccion entre candidatos elegibles:
  priority descendente, deadline ascendente, id ascendente.
Despues de seleccionar un job se reevaluan dependencias y capacidad.
Jobs con dependencias ciclicas nunca son elegibles, pero no bloquean a los demas.
No se muta la entrada.
"""


def _field_error(job):
    """Devuelve un mensaje de error para un job mal formado, o None si es valido."""
    if not isinstance(job, dict):
        return "job debe ser un dict"

    job_id = job.get("id")
    if not isinstance(job_id, str) or job_id == "":
        return "id debe ser un string no vacio"

    priority = job.get("priority")
    if isinstance(priority, bool) or not isinstance(priority, int):
        return "priority debe ser entero"

    deadline = job.get("deadline")
    if isinstance(deadline, bool) or not isinstance(deadline, (int, float)):
        return "deadline debe ser un numero"

    cost = job.get("cost")
    if isinstance(cost, bool) or not isinstance(cost, int) or cost <= 0:
        return "cost debe ser entero positivo"

    depends = job.get("depends", [])
    if not isinstance(depends, list) or any(
        not isinstance(dep, str) or dep == "" for dep in depends
    ):
        return "depends debe ser una lista de ids string"

    return None


def select_jobs(jobs, now, capacity):
    if not isinstance(jobs, list):
        raise ValueError("jobs debe ser una lista de dicts")
    if isinstance(capacity, bool) or not isinstance(capacity, int) or capacity < 0:
        raise ValueError("capacity debe ser un entero >= 0")

    entries = []
    seen_ids = set()
    for index, job in enumerate(jobs):
        error = _field_error(job)
        if error is not None:
            raise ValueError("job invalido en la posicion {}: {}".format(index, error))
        job_id = job["id"]
        if job_id in seen_ids:
            raise ValueError("id duplicado: {!r}".format(job_id))
        seen_ids.add(job_id)
        entries.append(
            {
                "id": job_id,
                "priority": job["priority"],
                "deadline": job["deadline"],
                "cost": job["cost"],
                "depends": list(job.get("depends", [])),
            }
        )

    if isinstance(now, bool) or not isinstance(now, (int, float)):
        raise ValueError("now debe ser un numero")
    if capacity < 0:
        raise ValueError("capacity debe ser un entero >= 0")

    remaining = list(entries)
    selected = []
    selected_ids = set()
    used = 0

    while True:
        candidates = [
            job
            for job in remaining
            if job["deadline"] > now
            and used + job["cost"] <= capacity
            and all(dep in selected_ids for dep in job["depends"])
        ]
        if not candidates:
            break

        best = min(
            candidates,
            key=lambda job: (-job["priority"], job["deadline"], job["id"]),
        )

        selected.append(best["id"])
        selected_ids.add(best["id"])
        used += best["cost"]
        remaining = [job for job in remaining if job is not best]

    return selected
