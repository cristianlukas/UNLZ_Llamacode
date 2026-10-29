# Q181 — Harness²: holdout de programación representativo

## Objetivo

Completar el seguimiento `Q171-HARNESS2-REPR-HOLDOUT`: comparar los perfiles `agent-basico` y `agent-intermedio` en tareas de programación con archivos y pruebas ejecutables, después de que Q171 sólo hubiera usado un workflow sintético.

## Fixture y protocolo preregistrado

- Fixture base inmutable: `assets/benchmarks/custom/agent_efficiency_e2e_v1.json`, SHA-256 `37c5907fa9220f56446c2ea8b3ed402d475b88aaa1d15fbceffe1960fd0b3f01`. Se usan sus tres prompts y acceptance commands: parser Python, localización TypeScript/JavaScript y estadísticas C++ con pruebas. No se cambia el contenido de tareas ni sus oracles.
- Una adaptación sólo de entorno hace disponible `python` como alias de `python3` y `node` desde el runtime Node 24.22.1 empaquetado por Codex. Los acceptance commands se conservan literalmente y se validan antes de cargar el modelo.
- 3 pasadas por perfil, orden intercalado A/B, B/A, A/B; 3 tareas × 3 pasadas = 9 tareas por perfil y 18 ejecuciones de tarea en total. Cada perfil usa workspace nuevo por tarea; el benchmark controlador espera la limpieza/fin de cada llamada antes de avanzar.
- Modelo: Qwen3.8 Flash-Next RCO IQ2_XS, perfil ASTRA, mismo runtime Strata de Q171 (1M configurado, YaRN×4, KV int8, GPUs 0 y 1). Config base SHA-256 `c0a63f0ba0e0710e978c84e60c229c7380b4c994dc5cb0e92b46e35151eb2529`; copia Q181 SHA-256 `1884f0a320f18aff51ad1589380f0be2f2cbfe16729105fbc3c86839c31f59f0`, con la única diferencia de redirigir el log desde `/run/q171` hacia `/run/q181`. No se modifica ASTRA productivo ni SOL.
- Harness aislado Q171 v5, binario local `LlamaCode` SHA-256 `5282f58cb9f47ea15bc1b09c4c98b7ee069511fc6bc5641ec76f6c5070969b30`; solo perfiles clonados de sistema. Sampling conservador `temperature=0.6`; MCP apagado, privacidad activada, filesystem limitado al workspace, confirmación de acciones destructivas activa, red exterior aislada y backend loopback sin API key.
- Métricas: aceptación por tarea, tareas completas, reparaciones, regresiones, tool calls, tokens y tiempo E2E. No hay juez LLM. Se conserva el orden y resultado de cada llamada.
- Regla: Intermedio sólo se recomendará sobre Básico si no reduce la aceptación, no introduce regresiones críticas y mejora ≥10% el E2E mediano o reduce reparaciones. El resultado no cambia perfiles productivos automáticamente.

## Preflight y límites

El lock paraguas Q146 está adquirido en `WORK_QUEUE.lock`. El supervisor y su archivo unitario se montan desde Q181; logs, perfiles y workspaces usan almacenamiento Q181 separado. Preflight actual: no hay inference servers ni listeners evaluativos; dos RTX 3090 visibles, sin procesos CUDA de cómputo ajenos; MemAvailable 116.4 GB. Se registrará de nuevo inmediatamente antes del arranque, junto con hashes/runtime y espacio. La prueba usará ambas GPU en serie, sin límite artificial de RAM/swap. Se detendrá ante servidor externo, puerto ocupado, hash/config mismatch, falta de cualquiera de las dos GPU, Xid/OOM/crash, endpoint no-loopback o MemAvailable <32 GiB durante cuatro muestras consecutivas de 15 s. El readiness del engine tiene 1200 s mediante `STRATA_ENGINE_READY_S=1200` sólo en el servicio de evaluación; el primer intento alcanzó 900 s sin READY, siguió inicializando sin OOM y se cerró limpio. El servicio de prueba y la GUI quedan aislados; no se toca PeritoSoft.

## Reconciliación de otros pendientes

- La réplica Q171 NInfer preview 0.16.1/Strata 0.1.52 con >2 GiB libres no es una prueba de adopción vigente: el preview NInfer no admite la topología dual y Q178 ya midió el camino NInfer-all dual; Q179 dejó ese perfil en no-go por el fallo crítico TC-92. Se conserva el resultado histórico y no se repite una comparación de runtime que no puede cambiar la decisión actual.
- Q173 y Q176 tienen resultados posteriores completos: Q178/Q179 para Flash-Next dual y Q176 con cobertura condicionada; la fila histórica GPU1-only se conserva. Se reconciliarán sus estados de Sheet después de validar los rangos.

## Incidente de deduplicación y reanudación

Q181 alcanzó READY tras 1.054 s, completó la primera pasada para ambos perfiles y luego abortó al solicitar otra copia idéntica del workload. LlamaCode suprimió correctamente la repetición por fingerprint; el runner convirtió el estado explícito `Omitido` en excepción. El servicio cerró limpio, sin OOM ni crash de la aplicación. Las dos filas de pass 1 quedan válidas: Básico 11/11 en 76,726 s; Intermedio 11/11 en 68,071 s (n=1 cada uno, todavía sin decisión).

El amendment 02 conserva esas dos corridas y reanuda los pases 2 y 3 con los mismos perfiles. Solo cambia el ID metadata de cada tarea (`_q181_repeat_02/03`) para que la deduplicación de evaluaciones idénticas no descarte las réplicas. Texto, acceptance oracles, token budgets, permisos y configuración permanecen iguales. El resumen final combina pass 1 con las cuatro nuevas corridas y valida seis filas/3 ejecuciones por perfil.

## Resultado final · 2026-10-29

Q181 quedó completado en el intento 5. Las tres pasadas balanceadas muestran Básico 3/3 y 11/11 en cada pasada; Intermedio 2/3, con una pasada 10/11 por fallo de prueba C++ (`min`: esperado -3, obtenido -43). Medianas: Básico 76,726 s E2E y 0 reparaciones; Intermedio 86,613 s y 1 reparación. No se recomienda promover Intermedio. El motor llegó a READY en 194 s; pico cgroup ~82,5 GB, MemAvailable mínimo ~62,8 GB y OOM=0, sin límites artificiales de RAM. Init hot no se midió por separado. El servicio se limpió y los puertos quedaron libres. Detalle: `RESULTS.md` y `receipts/results.json`.
