# Q117 · Resultado final

## Conclusión

El detector candidato Q117 **pasó la validación de memoria** en AMD05: ASTRA DEFAULT aceptó una request con 1.001.463 tokens, usó ambas RTX 3090 y no fue detenido por la guarda. La corrida alcanzó 51,31 GiB de RSS y mantuvo al menos 58,70 GiB disponibles; no hubo OOM global/cgroup ni swap atribuible al worker. La config, el perfil ASTRA y el guard de producción no se cambiaron. SOL Q34 sigue siendo el control histórico dual-GPU y no se repitió.

AMD04 había expuesto el error que motivó AMD05: PSI global severa por sí sola detuvo la carga cuando aún quedaban 77,07 GiB disponibles y sólo 33,85 GiB de RSS. La nueva regla CPU-only de AMD05 exige que PSI severa coincida con `MemAvailable <48 GiB` durante 15 muestras; conserva el corte inmediato `<32 GiB`, los cortes OOM/swap y el fail-closed por telemetría inválida. Los casos de AMD04 y la suite de frontera AMD05 demuestran que PSI alta con mucho headroom no detiene.

**Límite de la evidencia:** durante AMD05 la PSI global máxima fue 53,61%, por debajo del umbral severo. La conjunción de PSI severa + low headroom quedó validada con replay CPU (21/21), mientras AMD04 aporta la reproducción live del falso positivo de PSI-only. No se observó una situación real en que la nueva conjunción alcanzara el hard-stop. El cambio es candidato aislado y no se integró a Q97/Q100 ni al producto.

La request contestó HTTP 200 en 442,45 s (prefill 2.270,9 tok/s; decode 82,0 tok/s). El grader JSON original marca 0/8 porque la respuesta vino como ocho líneas numeradas. El prompt pide ocho respuestas numeradas y no requiere JSON; Q37 ya había fijado esa semántica para este mismo fixture. AMD05-R1 reutilizó el regrader semántico auditado y obtuvo **8/8**, sin ambigüedades y sin otra inferencia. Se preserva el 0/8 original únicamente como diagnóstico del parser JSON; no es un fallo de calidad ni una prueba nueva de adopción.

## Métricas AMD05

- Contexto solicitado: 1.048.576; uso medido del prompt: 1.001.463 tokens.
- Tiempo request: 442,448 s; prefill 2.270,9 tok/s; decode 82,0 tok/s; respuesta 90 tokens.
- RSS máximo del árbol: 51,306 GiB; `MemAvailable` mínimo: 58,698 GiB.
- PSI global avg10 máximo (some/full): 53,61%; guard sin abort reason.
- OOM global inicial/final: 0/0; OOM cgroup: 0; swap máximo/delta cgroup: 0 B.
- VRAM delta pico: GPU0 22.831 MiB, GPU1 22.372 MiB. Policy worker confirmada dentro de la unidad: `ManagedOOMMemoryPressure=auto`; `MemoryHigh/Max/SwapMax` permanecieron activos.
- Suite CPU AMD05: 21/21; regresiones guard histórico: 13/13; Python compile y shell syntax: PASS. La primera ejecución AMD05 CPU fue 20/21 por una aserción del test harness que buscaba un sufijo literal incorrecto; AMD05-C1 preregistró la corrección test-only y la repetición pasó 21/21.
- Regrade offline AMD05-R1: 8/8 semántico por líneas numeradas en orden; prompt y recibo comparten SHA-256; salida completada con `finish_reason=stop`; original strict JSON 0/8 preservado como diagnóstico no aplicable.
- Limpieza: supervisor y worker systemd inactivos; puerto 8350 libre; sin servidor/proceso de inferencia remanente.

## Recomendación

Mantener ASTRA DEFAULT, SOL, el perfil y el guard productivo intactos. Revisar el cambio candidato PSI+headroom antes de integrarlo en producción. AMD05 confirma recuperación semántica 8/8 a 1M en este seed, consistente con Q35/Q37; una sola corrida no cambia la recomendación de 131K por defecto. No modificar la RAM, el swap del host ni los perfiles por estos datos.

## Evidencia

- Prerregistro y alcance: `receipts/amendment-05-preregistration.json`.
- Regrade preregistrado/resultados: `receipts/amendment-05-semantic-regrade-preregistration.json`, `receipts/q117-amd05-semantic-regrade.json`; metodología existente `Q-20261022-VF-ITERATION-37/scripts/q35_semantic_regrade.py`.
- Suite/corrección CPU: `receipts/amendment-05-cpu-correction-preregistration.json`, `receipts/q117-amd05-cpu-tests.json`, `receipts/q117-cpu-guard-tests.json`.
- Preflight: `receipts/q117-preflight-attempt05.json` y `runs/astra-1m-seed-2026103-attempt05/preflight.json`.
- Run: `runs/astra-1m-seed-2026103-attempt05/receipt.json`, `runs/astra-1m-seed-2026103-attempt05/memory-monitor.jsonl`, `runs/astra-1m-seed-2026103-attempt05/systemd-unit.log`, `runs/astra-1m-seed-2026103-attempt05/server.log`.
- Resultado resumido y fingerprints: `receipts/q117-amd05-result.json`, `receipts/q117-final-summary-attempt05.json`.
