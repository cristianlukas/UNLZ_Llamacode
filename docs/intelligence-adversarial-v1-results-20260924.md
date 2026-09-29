# ADV v1 — comparación SOL vs ASTRA

> **Corrección 2026-09-28: los puntajes de abajo están mal.** Tres graders
> contradecían su propia consigna:
>
> - `safe_path_join` y `sql_parameterization` probaban `'bad\\x00name'`, una
>   barra literal por un doble escape, en lugar de un NUL real.
> - `deadline_scheduler` esperaba elegir el job `d` (deadline 5) con `now=10`,
>   aunque el enunciado excluye `deadline <= now`.
>
> Re-puntuando los mismos artefactos con los graders corregidos (rama
> `session/adv-grader-fix`, commit `a1dd395`):
>
> | Perfil | Original | Corregido | Falla de verdad |
> |---|---:|---:|---|
> | SOL | 7/10 | **10/10** | — |
> | ASTRA | 3/10 | **5/10** | TTL, JSONL, config; 2 sin artefacto por timeout |
> | Flash-Next W4A16 (2026-09-28) | 7/10 | **10/10** | — |
>
> La conclusión SOL > ASTRA se mantiene, pero la distancia es menor. Con SOL y
> Flash-Next la suite ya no discrimina, porque los dos resuelven las 10.

Nombre completo histórico: **Intelligence Adversarial v1**.

Fecha de corte: 2026-09-24.

## Método

- 10 tareas de código con criterios ejecutables y deterministas: TTL/cache, RFC 7396, topological sort estable, seguridad de rutas, contrato de tools, scheduler con dependencias, JSONL, resolución de configuración, reporte de incidentes y SQL parametrizado. En la tabla comparativa, el resultado de SOL se identifica como **ADV 7/10**.
- Mismo agente: `agent-maximo`, variante baseline.
- Se puntuaron los artefactos de la primera pasada, sin reparación automática.
- En Linux se normalizó el comando del grader de `python` a `python3`; `python` no existe en el PATH de esta instalación y el primer resultado automático 0/10 era una falla del harness, no del modelo.

## Resultado

| Perfil | Resultado | Aprobadas | Fallidas | No ejecutadas | Observación |
|---|---:|---|---|---:|---|
| SOL — Qwen3.8 vLLM TP2/P2P/MTP4 validado | **7/10** | TTL, RFC7396, toposort, tool contract, JSONL, config, incident report | path safety, scheduler, SQL | 0 | Primera pasada completa |
| ASTRA — Flash-Next Q2_K_XL, 256K, MoE12 | **3/10** | RFC7396, toposort, tool contract | TTL, path safety, scheduler, JSONL, config | **2** | Timeout duro a 1801 s; no llegó a incident report ni SQL |

## Lectura

Con esta batería y este agente, ASTRA no resulta más inteligente que SOL: obtuvo 3/10 frente a 7/10 y además no completó las últimas dos tareas dentro del límite operativo. ASTRA sí resolvió correctamente RFC 7396, toposort y el contrato de herramientas, pero falló en más casos de estado, seguridad y configuración.

Esto mide el comportamiento agentivo completo —razonamiento, edición, pruebas y tiempo de finalización—, no sólo la calidad de una respuesta textual aislada. El timeout de ASTRA debe conservarse como parte del resultado operativo, pero no interpretarse como un fallo semántico adicional en las dos tareas que nunca alcanzó.

## Evidencia

- Suite original: [`intelligence_adversarial_v1.json`](../assets/benchmarks/custom/intelligence_adversarial_v1.json).
- Corrida SOL: `/home/cristian/.local/share/LlamaCode/LlamaCode/benchmark-runs/Intelligence_Adversarial_v1_-_10_tareas_20260923_231754/`.
- Corrida ASTRA: `/home/cristian/.local/share/LlamaCode/LlamaCode/benchmark-runs/Intelligence_Adversarial_v1_baseline_sin_20260923_233224/`.
