# Strata 0.1.35 vs SOL: LlamaCode LC-H1

Corrida agentiva de LlamaCode realizada el 2026-10-02. Ambos modelos usaron el daemon headless, el agente `agent-maximo`, el mismo HarnessSpec, los mismos prompts, seed 4242, 1800 s por suite y un máximo de dos reparaciones automáticas. SOL se sirvió con el perfil vLLM TP2 P2P MTP4 local; Strata con 0.1.35 IQ3_S sobre dos RTX 3090. Cada suite se ejecutó una vez por modelo.

## Resultados

| Suite | Strata primera → final | SOL primera → final | Reparaciones | Tiempo Strata | Tiempo SOL |
|---|---:|---:|---:|---:|---:|
| HumanEval/0 | 0/1 → 1/1 | 0/1 → 1/1 | 1 / 1 | 19.1 s | 12.1 s |
| HumanEval/20 | 19/20 → 20/20 | 19/20 → 20/20 | 1 / 1 | 695.1 s | 220.2 s |
| BigCodeBench-Hard/8 | 3/8 → 8/8 | 2/8 → 8/8 | 1 / 1 | 480.1 s | 466.5 s |
| Intelligence Adversarial v1/10 | 7/10 → 10/10 | 6/10 → 8/10 | 1 / 2 | 468.4 s | 729.5 s |

Puntaje de primera pasada combinado: **Strata 29/39 (74.4%)**, SOL 27/39 (69.2%). Después de reparación: **Strata 39/39; SOL 37/39**.
Tiempo total de las cuatro suites: Strata 1662.8 s, SOL 1428.2 s. En HumanEval 20 SOL fue 3.16× más rápido; en BCB el tiempo quedó prácticamente empatado. En Adversarial, Strata terminó en 468.4 s frente a 729.5 s de SOL.
En BCB, Strata usó 52 llamadas, con 52/52 exitosas y 10 redundantes. SOL usó 56 llamadas, 54/56 exitosas y 12 redundantes.

## Lectura

- En las primeras tres suites, ambos llegaron a 29/29 tras una reparación en cada una; Strata aventajó a SOL por un punto en primera pasada (22/29 vs. 21/29).
- Al añadir Adversarial, Strata queda dos tareas arriba tanto en primera pasada (29/39 vs. 27/39) como en el resultado final (39/39 vs. 37/39).
- SOL fue claramente más rápido en HumanEval 20. Sumando las cuatro suites, SOL tomó 1428.2 s frente a 1662.8 s de Strata, alrededor de 1.16× menos tiempo.
- Cada suite corrió una vez por modelo; el resultado favorece a Strata en estos casos, pero no demuestra estabilidad estadística ni generalización.

## Suite adversarial

En `Intelligence Adversarial v1 - 10 tareas`, Strata terminó con 10/10 frente a 8/10 de SOL. La primera pasada fue 7/10 y 6/10 respectivamente. Strata necesitó una reparación; SOL usó las dos permitidas y quedaron sin pasar `deadline_scheduler` y `jsonl_audit`. Strata usó 32 llamadas de herramienta (30 exitosas, 2 fallidas, 1 redundante); SOL usó 104 (89 exitosas, 15 fallidas, 73 redundantes).

Ambas corridas tienen el mismo `HarnessSpec` (`sha256:cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`), perfil de agente, seed, suite y límite de timeout. En esta suite `thinkingEnabled` fue `false` en ambos resultados. Una corrida por modelo no permite afirmar estabilidad estadística, pero en esta suite el resultado final y el tiempo favorecen a Strata.

La puntuación 1/8 del chequeo directo anterior no era una comparación del agente de LlamaCode: fue una única respuesta por problema, sin el loop de herramientas y reparaciones. No debe cotejarse directamente con LC-H1. Esta corrida es la comparación válida para la afirmación sobre resultados agentivos.

## Reproducción y evidencia

El manifiesto, las definiciones exactas de las suites, las configuraciones de perfiles y los ocho directorios completos están en [`artifacts/strata-v0135-vs-sol-llamacode-lch1-20261002`](../artifacts/strata-v0135-vs-sol-llamacode-lch1-20261002/). Cada directorio incluye metadata, comparación agregada y resultado JSON por perfil con puntajes, aceptación por tarea y métricas. Los workspaces se conservaron en el directorio aislado local y se omitieron del artefacto versionado porque un workspace de BCB incluye archivos de prueba con nombres tipo `private_key`.
