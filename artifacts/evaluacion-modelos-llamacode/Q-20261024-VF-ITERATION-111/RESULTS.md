# Q111 · Auditoría del guard realmente usado por Q97/Q100

**Estado:** cerrada · 8/8 PASS · 2026-10-25T00:18:54Z

## Resultado

La revisión confirma que las corridas que realmente usaron ASTRA/SOL no estaban gobernadas por el core candidate-only Q108. Q97 implementa warning de PSI moderada tras 30 muestras seguidas de un segundo y stop severo tras 15; Q100 importa el helper Q97 y llama `guard.check_gates` desde el monitor de sus procesos. La suite Q111 ejercitó ese código real de policy: 8/8 PASS.

Q97/Q100 completaron sus cargas bajo PSI moderada sin OOM ni aborto. Q97 ASTRA terminó las 8 solicitudes de transporte, con pico global PSI 34,72%, 64 muestras de warning, mínimo 71,864 GiB disponibles y cero OOM. Q100 completó las seis tareas monitorizadas con PSI full pico 46,52%, mínimo 69,386 GiB, cero OOM y `guardAborted=false`. Las puntuaciones de calidad/concurrencia de esas campañas no se reinterpretan aquí.

El aviso inmediato detectado en Q110 corresponde al helper candidate-only Q108 y su wrapper de política. No demuestra que Q97/Q100 avisen en la primera muestra ni cambia sus hard stops. Tampoco hay evidencia para atribuir los cierres de Codex a RAM: los recibos no registran OOM correlacionable; existe un Crashpad `gpu-process` separado y no hay dump/minidump que cierre causalidad.

## Cobertura ejecutada

- Q97: warning moderado exactamente en la muestra 30; recovery reinicia el streak.
- Q97: PSI global full ≥60% y some ≥80% mantienen el hard stop en la muestra 15 (no en 14).
- Q100: delega el gate monitoreado al helper Q97.
- Separación: Q108 raw muestra el warning inmediato; Q110 wrapper reproduce 30 muestras, ambos candidate-only.
- Recibos históricos: Q97 y Q100 terminaron bajo PSI moderada, sin OOM ni aborto.
- Preflight Q111: cero procesos de inferencia conocidos y cero listeners en puertos de inferencia conocidos; ArtCraft/OpenRGB y demás listeners no se tocaron.

No se inició servidor, modelo, request, build, descarga, GPU ni memoria artificial. ASTRA Flash-Next, SOL y los pesos/perfiles de PeritoSoft permanecen intactos.

## Inbox y accionables

El inbox local contiene 58 materiales, todos asociados al lote VF-20261019-01 y con campo `analysis`; las fuentes relacionadas con concurrencia/Q97 ahora referencian el resultado Q111. Hay 28 accionables. Los no terminales siguen dependiendo de gates verificables (Windows nativo/Job Objects, fixture de tenant, workflow+holdout, caption primaria, opt-in/documentación real para OCR, o cambio material parser/runtime de HyperQwen). No se marca ninguna de esas condiciones como completada. Próximo candidato técnico para reanudar: construir un fixture local de autorización tenant para el P2.1, si el código ofrece una ruta ejecutable verificable; de lo contrario mantenerlo bloqueado con evidencia concreta.

## Evidencia

- Q111 runner: `runner/test_q111_memory_guard_integration.py`; preflight: `runner/q111_host_preflight.py`.
- Q111 receipt: `receipts/q111-integration-audit.json`, `receipts/q111-host-preflight.json`.
- Historial: Q97 `receipts/q97-memory-guard-review.json`, `receipts/q97-final-result.json`; Q100 `receipts/q100-final-result.json`.
- Sheet: `Evaluaciones LlamaCode!A332:J332`; P0 `Accionables!A2:N2`.
