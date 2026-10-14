# Plan — Q-20261014-R9700-TASKFLOW

## Objetivo

Completar la única etapa de coding/agente que el informe `Q-20261010-FLASHNEXT-Q4-P100-POST` marcó explícitamente como no ejecutada: TaskFlow ULTRA para el perfil local Flash-Next Q4 UD-Q4_K_XL. El resto de HE0/HE20/BCB8 y ADV ya tiene recibos válidos para ese fingerprint y no se repetirá.

## Perfil y control de referencia

- Candidato: Qwen3.8-Flash-Next Unsloth UD-Q4_K_XL, Strata 0.1.41, dual RTX 3090. El perfil específico TaskFlow R8192 quedó con fingerprint efectivo `2bbc5b4c7c4e34c044814f565879b61cab3d799b0557355e5662b584b053d9fa`; no es la huella LC-H1 R4096 `09d45e63…`.
- HarnessSpec LC-H1: `cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`.
- TaskFlow ULTRA: suite histórica `qwen38_taskflow_ultra_ast_vs_sol_20261006`, suite hash `f04febb440208d5bf74c01e84d78f5127e57c164fabece2acbfb346215dc0c17`.
- Muestreo/harness del launch archivado: seed 4242, thinking medio, R8192, Strata configurado con temperatura 0.60/top-p .95/top-k 20/min-p 0/repeat 1/presence 0; el recibo de LlamaCode registró `agentTemperature=0.1`. Se permitieron hasta tres reparaciones.
- Referencia histórica no emparejada: IQ2_XS TaskFlow 0/13 inicial → 13/13 tras tres reparaciones; IQ3_S/ASTRA y otros controles tienen recibos anteriores con fingerprints y condiciones parcialmente distintos. Un resultado único de Q4 será screening, no una afirmación de mejora estable.

## Protocolo y límites

1. Confirmar GPU, RAM/swap, procesos/listeners y disponibilidad del perfil/weights/runtime antes de iniciar Strata.
2. Ejecutar sólo una corrida TaskFlow ULTRA del perfil Q4 en workspace aislado, guardando primera pasada, cada reparación disponible, checks, comandos, tool calls, archivos, tiempos, fingerprint efectivo y logs.
3. Clasificar timeout, caída o transporte roto como infraestructura/incompleto, no como cero de calidad. Mantener la guarda vigente: máximo 30 minutos acumulados para este perfil.
4. Parar servicios propios y confirmar puertos/GPU al cierre. No cambiar perfiles productivos, HarnessSpec o pesos.
5. Actualizar `RESULTS.md`, el documento canónico y el cierre de cola con la evidencia y sus límites.

## Criterio de decisión

TaskFlow completa aporta evidencia exploratoria de coding/agente junto a HE0/HE20/BCB8 y ADV ya existentes. No cambia la recomendación ni promueve Q4: harían falta tres corridas válidas apareadas por perfil con verificadores independientes y el presupuesto de tiempo permitido.

## Estado final

Screening completado el 2026-10-14. Q4 obtuvo 11/13 al primer intento y 13/13
tras dos reparaciones; compilación, 30 tests generados por la tarea y self-test
pasaron. El perfil TaskFlow tuvo fingerprint efectivo
`2bbc5b4c7c4e34c044814f565879b61cab3d799b0557355e5662b584b053d9fa`. Ver
[`RESULTS.md`](RESULTS.md). Una sola corrida; no promoción.
