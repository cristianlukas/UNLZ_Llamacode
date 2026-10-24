# Q108 · Resultados de auditoría del guard de memoria

**Estado:** PASS CPU-only, 15/15 comprobaciones.
**Lock:** Q-20261024-VF-ITERATION-108 (19dc403c-9b1f-4f4f-8227-b38b24edcdb1).

## Respuesta sobre ASTRA y SOL

Tu evidencia histórica es consistente con el guard actual. ASTRA DEFAULT/Flash-Next completó el caso de 1M tokens; los registros muestran aproximadamente 51.14–51.15 GiB de RSS y ninguna razón de corte. El replay Q102 usa 55.728 GiB de MemAvailable; la revisión histórica Q97 conserva Q14 con 55.64 GiB y Q35 con tres semillas completas y 64.98/65.06 GiB mínimos. SOL Q34 terminó TP=2 con ambas RTX 3090 y sin OOM. SOL no tiene una serie PSI continua en ese recibo, así que no lo uso para calibrar PSI.

En Q97/Q98/Q99/Q100, PSI global moderada produjo avisos y las corridas continuaron; Q100 acabó las seis corridas con MemAvailable mínimo 69.386 GiB y OOM global/cgroup=0. El guard no trata RAM ocupada, RSS alto ni PSI moderada como condición de corte.

## Hallazgo y corrección de borde

La preocupación tiene un fundamento histórico: los umbrales anteriores de Q91/Q93 detuvieron candidatos cuando PSI full llegó a 51.48%/52.34%, aunque había 101.014/92.073 GiB disponibles y no hubo OOM. Ese registro es evidencia de presión/stalls y de un umbral demasiado sensible; no evidencia que ASTRA o SOL causaran un crash. Los umbrales actuales se recalibraron después.

También encontré un borde que las pruebas Q102/Q103 no cubrían: las copias antiguas del guard podían tratar PSI ausente/malformada y el contador oom_kill ausente como cero. Q108 reprodujo ese fail-open y agregó un core candidato que exige ambas métricas PSI válidas y el contador OOM. Si falta telemetría, el candidato recibe una razón explícita y el helper sólo señaliza el PID que se le entrega. Los thresholds existentes no cambian: corte por MemAvailable <32 GiB, nuevo OOM o PSI global severa durante 15 muestras; la PSI moderada sólo avisa.

Q102 replay histórico: 19/19. Q103 smoke de 56.013 GiB RSS: MemAvailable mínimo 53.386 GiB, sin warning, stop ni OOM. Estos registros más Q108 (15/15) sostienen el comportamiento observado, pero no prometen inmunidad a cualquier crash.

El guard es un límite para candidatos de evaluación. No limita memoria/VRAM de ASTRA o SOL y no predice todos los cierres de Codex, driver NVIDIA, kernel o GUI. Las pruebas Q108 fueron CPU-only; no iniciaron modelo/servidor ni asignaron memoria artificial. ASTRA DEFAULT 1M, SOL, Flash-Next y PeritoSoft quedaron intactos.

## Continuación de la cola

El accionable Q99 decía que faltaba la integración E2E. Q100 ya la ejecutó en LlamaAgentBackend: serial terminó 3/3 seeds y 6/6 tareas correctas; parallel2 terminó 1/3 seeds y 2/6 tareas correctas, con etiquetas finales invertidas en dos seeds. Q105 encontró 34/34 checks de forensics, pero faltan IDs de correlación para atribuir la inversión a un componente. Decisión: no adoptar parallel2; mantener serial y cerrar el accionable como completado/no-go. Reabrir sólo con instrumentación preregistrada de IDs.

No hay otro benchmark de modelo habilitado ahora: NInfer y Job Objects requieren una sesión Windows nativa; HyperQwen espera un cambio material reproducible en parser/runtime; autorización tenant requiere una API/fixture concreta; el fixture de orden requiere fuente primaria. Los 58 materiales del lote tienen resultado; los restantes están bloqueados con estas condiciones o sin prueba técnica aplicable.

Hubo dos fallos de aserción del propio auditor durante la iteración: primero, una búsqueda textual en inglés cuando el recibo estaba en español/estructurado; luego, un test que seguía esperando el estado obsoleto de Q99 después de que ya se había reconciliado. Se corrigieron para validar los recibos estructurados y el estado final; el rerun pasó 15/15. Q108 también leyó en vivo una muestra de `/proc`: 110.042 GiB disponibles, PSI some/full=0%, OOM=0 y decisión continuar, sin señales ni carga. Los parsers y la integración de decisión pasan fixtures; el core debe usarse desde el launcher de la próxima evaluación elegible.

## Artefactos

- PLAN.md y runner/test_q108_guard_audit.py
- runner/q108_guard_core.py (candidato estricto para evaluaciones futuras; no reemplaza artefactos históricos)
- receipts/q108-audit.json
- receipts/q108-sheet-preregistration.json
