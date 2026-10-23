# Q67 — recheck de gates Q56

**Cierre:** 2026-10-23T20:43:00Z
**Estado:** bloqueada por falta de reinicio posterior a la actualización NVIDIA.

## Verificación del host

- `uptime -s` sigue siendo `2026-10-22 22:26:57`; el host Ubuntu no reinició después del update.
- El proceso principal de Codex, PID 7630, sigue usando `/usr/lib/chatgpt/ChatGPT (deleted)`. Los renderers nuevos no reiniciaron el proceso principal.
- No hay procesos con nombres/comandos reconocidos de llama.cpp, Strata, NInfer, vLLM, Ollama, SGLang o LM Studio. Los listeners visibles son ArtCraft 47413, el listener no atribuido 35751, DNS 53, CUPS 631 y OpenRGB 6742. `lsof`, `fuser` y la búsqueda de socket inode en `/proc` no atribuyeron el 35751; queda como listener desconocido, no clasificado como inferencia.
- `/proc/driver/nvidia/version` informa 610.57.04; NVML es 615.71 y `nvidia-smi` falla con exit 18 por mismatch. El marcador `/var/run/reboot-required` sigue presente.

## Decisión

No se reanuda Q56. Su gate NVIDIA falla antes de iniciar servidor o requests; tampoco se resuelve el listener 35751. No se hizo build, descarga, benchmark ni workload de GPU; `nvidia-smi` se usó sólo como consulta de estado. El staging de Q56, modelos, perfiles y datos productivos permanecen intactos.

## Condición de reanudación

Reiniciar Ubuntu después de la actualización, abrir Codex en el arranque nuevo y repetir el preflight Q56. Antes de cualquier request se exige: ejecutable principal actualizado (sin `(deleted)`), `nvidia-smi` funcional con módulo/NVML coincidentes, cero servidor de inferencia ajeno, puerto 8352 disponible, resolución del listener 35751 y todos los límites del preregistro aprobados. Después, correr el canario durable y las seis requests seriales ya preregistradas.

## Sheet

Q67 se escribió y leyó de vuelta en `Evaluaciones LlamaCode!A289:J289`; `Accionables!H2:N2` contiene el recheck. Se conservaron WRAP y alineación superior. Recibo `receipts/google-sheet-sync.json`.
