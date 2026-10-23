# Q67 — auditoría del gate para reanudar Q56

Inicio: 2026-10-23T20:41:34Z
Lock: `80fe7643-2f89-4942-8b9a-0a5e2924726e`

## Pregunta

¿Cambió el estado del host desde Q66 de forma que se pueda reanudar la prueba Q56 ya preregistrada?

## Método

1. Confirmar boot, procesos/listeners de inferencia y proceso principal de Codex.
2. Si no hay inference server, consultar estado NVIDIA y reboot marker.
3. Leer el preflight/preregistro Q56 vigente; no cambiar criterios ni staging.
4. Ejecutar el canario durable y seis requests seriales de Q56 sólo si Codex está actualizado, Ubuntu reinició tras el update, NVML/módulo coinciden, `nvidia-smi` funciona, no hay inference server y todos los guards del preregistro pasan.
5. Si falta una condición, no iniciar servidor/request/GPU; cerrar con evidencia y próxima acción concreta.

Sin cambios de sistema, cierre de procesos del usuario, edición de modelos, configuración, perfiles, memoria o contexto.
