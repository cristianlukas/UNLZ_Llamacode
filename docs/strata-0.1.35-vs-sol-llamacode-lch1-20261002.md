# Strata 0.1.35 vs SOL: LlamaCode LC-H1

Corrida agentiva de LlamaCode realizada el 2026-10-02. Ambos modelos usaron el daemon headless, el agente `agent-maximo`, el mismo HarnessSpec, los mismos prompts, seed 4242, 1800 s por suite y un máximo de dos reparaciones automáticas. SOL se sirvió con el perfil vLLM TP2 P2P MTP4 local; Strata con 0.1.35 IQ3_S sobre dos RTX 3090. Cada suite se ejecutó una vez por modelo.

## Resultados

| Suite | Strata primera → final | SOL primera → final | Reparaciones | Tiempo Strata | Tiempo SOL |
|---|---:|---:|---:|---:|---:|
| HumanEval/0 | 0/1 → 1/1 | 0/1 → 1/1 | 1 / 1 | 19.1 s | 12.1 s |
| HumanEval/20 | 19/20 → 20/20 | 19/20 → 20/20 | 1 / 1 | 695.1 s | 220.2 s |
| BigCodeBench-Hard/8 | 3/8 → 8/8 | 2/8 → 8/8 | 1 / 1 | 480.1 s | 466.5 s |

Puntaje de primera pasada combinado: **Strata 22/29 (75.9%)**, SOL 21/29 (72.4%). Después de reparación: **29/29 para ambos**.
Tiempo total de las tres suites: Strata 1194.4 s, SOL 698.7 s. En HumanEval 20 SOL fue 3.16× más rápido; en BCB el tiempo quedó prácticamente empatado.
En BCB, Strata usó 52 llamadas, con 52/52 exitosas y 10 redundantes. SOL usó 56 llamadas, 54/56 exitosas y 12 redundantes.

## Lectura

- Strata queda ligeramente por encima en primera pasada: +1 tarea de BCB (3/8 vs 2/8), y +1 punto combinado en 29 tareas (22 vs 21).
- No hay diferencia en el resultado final: ambos alcanzaron 29/29 con una reparación en cada suite.
- SOL fue claramente más rápido en HumanEval 20; el tiempo total favorece a SOL por aproximadamente 1.71×.
- Con una sola pasada por suite, esto respalda una ventaja pequeña de Strata en primera respuesta de BCB y paridad tras reparación. No demuestra una ventaja final estable ni una generalización estadística.

La puntuación 1/8 del chequeo directo anterior no era una comparación del agente de LlamaCode: fue una única respuesta por problema, sin el loop de herramientas y reparaciones. No debe cotejarse directamente con LC-H1. Esta corrida es la comparación válida para la afirmación sobre resultados agentivos.

## Reproducción y evidencia

El manifiesto, las definiciones exactas de las suites, las configuraciones de perfiles y los seis directorios completos están en [`artifacts/strata-v0135-vs-sol-llamacode-lch1-20261002`](../artifacts/strata-v0135-vs-sol-llamacode-lch1-20261002/). Cada directorio incluye metadata, comparación agregada y resultado JSON por perfil con puntajes, aceptación por tarea y métricas. Los workspaces se conservaron en el directorio aislado local y se omitieron del artefacto versionado porque un workspace de BCB incluye archivos de prueba con nombres tipo `private_key`.
