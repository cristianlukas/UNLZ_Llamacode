# Plan — Q-20261010-QWEN38-CODER-262K

## Objetivo

Verificar qué aporta el Qwen3.8-Flash-Next GSQ-RCO Coder podado del post de r/Qwen_AI a coding/agentes y tool-use en LlamaCode, y distinguir los claims de contexto/rendimiento de evidencia local. La publicación dice `Q3_XSS`, Strata, 262K, alrededor de 130 tok/s decode y 4.000 tok/s adicionales sin recibos; la tarjeta de ISTA-DASLab presenta el Coder como release distinto, poda 256/512 expertos y una variante IQ1_M. No sustituir el quant publicado por otro artefacto ni confundirlo con el ISTA IQ3_XXS sin poda ya medido.

## Candidatos y controles

- **Candidato:** el archivo/revisión exactos de `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` que coincidan con la configuración del post. Confirmar localmente presencia, variante y hashes; no descargar antes de verificar compatibilidad, tamaño y espacio.
- **Controles históricos:** Q4 UD-Q4_K_XL, ASTRA IQ3_S calibrado y SOL. Sus resultados Hard Mode anteriores se citarán como referencias de perfiles completos; no se tratarán como A/B directo si runtime/hardware/harness difieren.
- Si el quant del post no está disponible localmente, no reemplazarlo silenciosamente por IQ1_M u otro variant: cerrar como auditoría local bloqueada/inconclusa y registrar qué falta.

## Protocolo preregistrado

- Suite primaria: tool-eval-bench Hard Mode de 28 tareas, seeds 42/43/44, temperatura 0.6, mismos prompts, template, permisos, agente, timeout y reparaciones documentados en la campaña v2.8.0 cuando el runtime admita el mismo HarnessSpec.
- **Corte de interés del usuario:** máximo 30:00 de tiempo total de suite por perfil para las tres seeds. Primero ejecutar un piloto que permita estimar la duración; continuar sólo si el total proyectado, incluido el trabajo de inferencia medido de ese perfil, cabe en 30 minutos. Si no cabe, detener ese perfil y reportar el resultado del piloto como provisional, sin completar semillas costosas. No confundir descarga/preparación con tiempo de inferencia; reportar ambas por separado.
- Comparar tiempos de cada seed y total, puntajes brutos, promedio, fallos críticos de seguridad/aislamiento, TPS de los logs, TTFT y estado de transporte. Una corrida inválida por infraestructura no cuenta como cero de calidad.
- HE0/HE20/BCB8/ADV/TaskFlow sólo si son pertinentes, sus inputs están disponibles y su duración proyectada también respeta el límite. No sumar suites distintas como un score único.
- Contexto de 262K: sólo un preflight no invasivo inicialmente; no cargar contexto largo ni crear un benchmark de 262K si VRAM/RAM/swap/KV no soportan una corrida segura. La capacidad declarada no equivale a retrieval probado.
- No ejecutar GUI E2E, Ingi-Charla ni visión sin fixtures y runtime adecuados; no modificar perfiles, HarnessSpec ni defaults.

## Recursos y seguridad

- Host dual RTX 3090; no iniciar procesos ni reservar GPUs hasta revisar ocupación, RAM, swap, disco, modelos instalados y servidores existentes. Ejecutar secuencialmente, sin interferir con procesos ajenos.
- Evitar descargas. Si falta el candidato exacto, conservar el bloqueo y seguir con la siguiente tarea independiente de FIFO.
- Evidencias previstas: fuentes primarias, manifiesto de archivos/revisiones/SHA-256, perfil efectivo, versiones/runtime/argumentos, Hardware/RAM/VRAM, suite/seed, logs crudos, resultados y tiempos.

## Criterio de decisión

Un perfil sólo entra en consideración si la medición válida de las tres seeds cabe en 30 minutos totales y no presenta fallos críticos de aislamiento/seguridad. Una señal obtenida con una sola seed queda provisional. Sin mejora reproducible frente a un control comparable no se promueve ningún cambio.

## Cierre y reutilización

La ficha del publicador y Strata describen la variante disponible como IQ1_M; el post no permite determinar si su “Q3_XSS” apunta a otra revisión/quant. La auditoría local del IQ1_M ya está hecha y se reutiliza. El preflight confirmó que los pesos ya no están en las raíces locales y que GPU0 tiene ArtCraft activo; no se inició descarga ni inferencia. Esta tarea cierra como auditoría del post, no como reproducción de sus cifras. Una nueva prueba requiere reconciliar la variante exacta y cumplir el corte de 30 minutos para las tres seeds del perfil.
