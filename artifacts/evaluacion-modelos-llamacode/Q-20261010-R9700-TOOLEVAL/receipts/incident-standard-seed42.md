# Incidente de infraestructura: SOL estándar seed 42

- UTC de diagnóstico: 2026-10-12T20:45:17+00:00
- Runner 2.7.0, commit c483eef867d75d9dd04c7d370fe553f96a49d672; SOL local AutoRound INT4, vLLM 0.27.1, TP2 sobre dos RTX 3090, MTP4.
- La ejecución recorrió 47 de 69 escenarios con respuesta normal: 38 pass, 4 partial, 5 fail funcionales; 80/94 puntos en ese subconjunto. TC-48 a TC-69 (22 escenarios) recibieron HTTP 500 y no produjeron inferencia. Por tanto, la corrida completa está invalidada por infraestructura y el 85/100 agregado del runner **no es score comparable**.
- El log del servidor muestra a las 20:43:57 UTC un `CUDA error: device-side assert triggered` en Worker_TP0 durante `gpu_model_runner.synchronize_input_prep()` / `num_accepted_tokens_event.synchronize()`, seguido de terminación del engine y HTTP 500 repetidos. `docker inspect` informó `OOMKilled=false`. No atribuyo esos 22 casos a calidad.
- Evidencia: `../raw/sol-standard-seed42.json`, `../logs/sol-standard-seed42.log`, `../logs/sol-vllm-first-load-seed42.log`.
- Contenedor propio `llamacode-q9700-sol-vllm` y su red de Compose detenidos/eliminados para liberar VRAM. GPUs regresaron a memoria de escritorio; no se tocó ningún proceso ajeno.
- Acción: reiniciar exactamente el mismo perfil aislado (`pull_policy: never`, pesos existentes y Compose original intacto), probar TC-48 en una corrida aislada con la misma huella. Si responde normalmente, repetir la etapa completa 69 escenarios/seed 42. Si el assert vuelve, registrar bloqueo estable del perfil/runtime y continuar con ASTRA/Q4.
