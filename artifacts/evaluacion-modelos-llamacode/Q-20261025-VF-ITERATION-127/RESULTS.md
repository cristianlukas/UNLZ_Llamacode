# Q127 · Traza real de memoria de SOL en dual RTX 3090

## Resultado

La solicitud de SOL completó correctamente. La prueba usó las dos RTX 3090, el perfil Qwen3.8-27B AutoRound INT4/W4A8 de Q34 y una sola solicitud prompt-copy de 24.319 tokens de entrada y 256 de salida. El tiempo end-to-end de esa solicitud fue 14,95 s; no es un benchmark de velocidad ni una comparación de modelos.

El monitor AMD05 no abortó y la traza tuvo 157 muestras. Durante esta carga el host conservó al menos 99,973 GiB disponibles, PSI global `some/full avg10` llegó como máximo a 0,9%, el árbol del worker llegó a 12,421 GiB de RSS y el pico cgroup fue 15,577 GiB. La VRAM pico reportada fue 24.080 MiB en GPU0 y 23.972 MiB en GPU1; la temperatura máxima fue 63 °C. El cgroup no usó swap y sus contadores OOM/OOM-kill permanecieron en cero; el contador global OOM tampoco cambió. Hubo cero warnings y cero muestras con una razón de aborto.

Esto es coherente con el historial que el usuario destacó: ASTRA DEFAULT 1M completó 1.001.463 tokens con RSS máximo de 51,306 GiB y mínimo de 58,698 GiB disponibles; SOL Q34 finalizó sus 30/30 solicitudes sin OOM. El uso de memoria/VRAM alto no equivale a presión crítica si el host conserva headroom y PSI global no indica contención sostenida.

## Revisión del detector

- El guard de campañas Q97/Q100 continúa intacto: avisa ante PSI global moderada sostenida y detiene por los hard-stops ya registrados. Q116 encontró un borde en su lógica histórica: alternar `full>=60%` y `some>=80%` puede no acumular 15 muestras porque mantiene contadores separados.
- El candidato AMD05 combina `full>=60% OR some>=80%` con `MemAvailable<48 GiB` durante 15 muestras, y conserva los cortes inmediatos por `MemAvailable<32 GiB` u OOM. No detiene por RSS aislado. Q126 validó el borde sintético 4/4; Q127 lo ejecutó a través de Q121 durante una carga real de SOL y no generó falso corte.
- Q127 no alcanzó PSI severa junto con poco headroom. Por lo tanto valida el camino normal y la telemetría durante SOL; no demuestra sensibilidad real del hard-stop bajo presión crítica. AMD05 queda candidato y no se integra a Q97/Q100 ni al producto con esta evidencia solamente.
- Esta prueba no modifica límites RAM/swap/contexto ni perfiles ASTRA, SOL, Flash-Next o PeritoSoft. No reproduce ni atribuye los cierres de Codex.

## Limpieza y corrección del runner

`docker compose down` devolvió 0 y el contenedor `q127-sol-memory` desapareció. El resumen inicial del runner quedó como `FAILED` porque su comprobación de puerto intentó `bind()` y confundió dos conexiones TCP `TIME_WAIT` de la solicitud con un listener. La inspección de las 05:11:06 UTC mostró cero sockets `LISTEN`, dos `TIME_WAIT`, ningún contenedor Q127 y ningún proceso de inferencia Q127.

La enmienda A02 cambió sólo la comprobación del runner a `ss -H -ltn`: ahora sólo un socket en escucha bloquea el puerto. A03 corrigió el `sys.path` del harness CPU que primero intentó importar el runner por `importlib` sin añadir su carpeta `scripts/`; ese intento falló antes de probar el puerto, no inició modelo ni GPU. La regresión corregida pasó: el puerto real 18117 fue aceptado sin listener, un listener loopback temporal fue rechazado y el puerto volvió a aceptarse al cerrar el socket. La comprobación final confirma contenedor/proceso ausente y cero listeners en 18117. No se repitió inferencia.

## Decisión y alcance restante

Conservar ASTRA DEFAULT 1M y SOL sin límites de RSS artificiales. No bajar RAM disponible, swap ni contexto. Mantener AMD05 sin integrar hasta revisar explícitamente el gap de PSI alternante en la política de producción y contar con una prueba justificada de la respuesta bajo presión real; no crear presión artificial en el host. La causa de los cierres de Codex continúa sin atribución.

## Recibos

- Plan y configuración: `PLAN.md`, `receipts/preregistration.json`.
- Gates: `receipts/attempt01-static-syntax-and-pins.json`, `receipts/q121-verify-only.json`, `receipts/sheet-prereg-readback.json`, `receipts/preflight.json`.
- Solicitud/trace/cleanup original: `attempt01/receipts/sol-request.json`, `attempt01/runs/memory-trace.jsonl`, `attempt01/receipts/compose-stop.json`, `attempt01/receipts/final-summary.json`.
- Correcciones y reconciliación: `receipts/amendment02-port-listener-check-preregistration.json`, `receipts/attempt02-regression-harness-import-failure.json`, `receipts/amendment03-regression-import-fix-preregistration.json`, `receipts/attempt02-port-listener-regression.json`, `receipts/result-analysis.json`.
- Registro canónico: `WORK_QUEUE.md`; Google Sheets: `Evaluaciones LlamaCode!A348:J348` y `Accionables!A2:N2`.
