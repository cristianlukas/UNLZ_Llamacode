# Q106 — Resultados: detector de memoria y regresiones CPU de tools

**Estado:** PASS. Los tres casos dirigidos pasaron; el gate completo pasó 95/95 al repetirlo con el entorno correcto en Q107. **Lock:** `cb78d8ff-dcf8-460a-936f-62f50f0fb848`.

## Detector de presión de memoria

La evidencia histórica coincide con la experiencia del usuario: ASTRA DEFAULT 1M completó 10/10 con ~51,14 GiB RSS de árbol y mínimo de 55,728 GiB `MemAvailable`; PSI de memoria, swap-out y OOM permanecieron en cero. SOL completó en TP=2 con ambas RTX 3090 sin OOM (Q34), aunque ese registro no tiene PSI/RSS continuo. Q103 sostuvo ~56,013 GiB de RSS CPU durante 12 s con mínimo de 53,386 GiB disponibles, PSI avg10 máxima de 0,36%, cero avisos/stops/OOM y recuperación inmediata.

Q102 vigila presión global del host (`MemAvailable`, PSI de memoria y delta `oom_kill`), no RSS/porcentaje usado ni VRAM. Mantiene hard-stop a <32 GiB disponibles, OOM nuevo o PSI severa sostenida (15 muestras de 1 s); PSI moderada sólo avisa. ASTRA 1M y SOL no contradicen esos umbrales: RAM ocupada no equivale por sí sola a presión crítica. Se mantienen thresholds, perfiles y límites. El detector no es un monitor de VRAM/driver ni una garantía contra cualquier cierre de Codex.

Host de referencia: **2× RTX 3090 + 128 GB RAM**. Q106/Q107 fueron CPU-only, sin inferencia. No se cerró ningún proceso externo ni se cambió memoria/swap.

## Tests de tools

- Tres pruebas Qt loopback enfocadas (`toolBatchRequiresReplan_onlyTaskBatchesFanOut`, `nativeToolBatchReplansAfterFirstResult`, `nativeMixedTaskBatchDoesNotDispatchLaterTaskEarly`): **3/3 PASS**.
- La primera suite Q106 salió 94/95 porque el comando de prueba pasó `LLAMACODE_Q77_SERVER_URL=` y `LLAMACODE_Q102_SERVER_URL=`. El updater detecta la presencia del nombre aunque el valor esté vacío, crea `launcher.env` y por eso cambia el comportamiento que el test esperaba.
- Q107 confirmó el diagnóstico y repitió `scripts/tests-linux.sh Release` con esas dos variables ausentes: **95/95 PASS**. El test directo y el test CTest aislado también pasaron.
- No se modificó código ni el harness; no fue una regresión del updater ni evidencia de un crash de Codex.

## Decisión

Se valida la replanificación local de tools y queda verde la suite Linux Release. Q106 no comprueba autorización multitenant ni APIs reales de reservas/notificaciones. No habilita adopción de Qwen con tools. Mantener ASTRA/SOL en sus perfiles productivos y Q102 thresholds sin cambios.
