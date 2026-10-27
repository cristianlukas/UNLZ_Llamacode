# Q158 · reintento del preflight Gyro-Coder-L con el runtime Vulkan oficial actual

**Estado previo:** preregistro antes de descargar la imagen, usar GPU o iniciar el CLI. Se mantiene la cola bajo el lock umbrella Q146 `2242863e-c78e-4fa9-9649-c1d1541f3919`.

## Pregunta

¿La imagen GHCR que indica hoy el publicador, ejecutada con `NVIDIA_DRIVER_CAPABILITIES=all`, enumera las dos RTX 3090 en `llama-server --list-devices` y habilita el screen Q152 de Gyro-Coder-L TQ3_0 v1.1?

## Evidencia de cambio

- El intento Q152 usó `docker.io/agentionai/agention-llama@sha256:ddcba819dfa58332e408aa734d3cde13572331a57683abd3afb1e0a620f543d6`; NVML veía las tarjetas, Vulkan no creaba instancia y `--list-devices` devolvía ninguno.
- La guía oficial actual ahora prescribe `ghcr.io/agentionai/agention-llama:server` para NVIDIA con `--gpus all -e NVIDIA_DRIVER_CAPABILITIES=all`. Q152 montó el ICD, `libXext`, `/dev/dri` y `libvulkan`, pero no registró esa variable ni probó el registro GHCR.
- Manifiesto `linux/amd64` inspeccionado antes de descargar: `sha256:0f0547624f92df823ef7bdbfc1e497a3674cebeaaaefb2c59012ba1716799fc6`; capas comprimidas ≈167 MB.
- Fuentes primarias: https://www.agention.ai/models/gyro/ y https://huggingface.co/agentionai/Qwen3.8-Flash-Next-Gyro-Coder-GGUF .

## Procedimiento preregistrado

1. Descargar solo la imagen, fijada por el digest GHCR anterior.
2. Ejecutar el binario `llama-server --list-devices` con `--gpus all`, `NVIDIA_DRIVER_CAPABILITIES=all`, red deshabilitada y sin volumen de modelos, puertos ni endpoint. No se inicia un servidor HTTP ni se descarga el GGUF.
3. Gate PASS solamente si el CLI lista ambas NVIDIA GeForce RTX 3090; si no, marcar bloqueado y retirar solo la imagen fijada cuando no tenga consumidores.
4. Si pasa, reanudar Q152 con su TQ3_0 v1.1 exacto y screen BCB-Hard-8 seed 4242. Antes de bajar el modelo de 83.975.624.672 B, verificar espacio; después validar carga, distribución en ambas GPUs y contrato del runner. Sin fallback de CPU o GPU única.

## Preflight del host antes de la imagen

- No había procesos/containers/listeners de PeritoSoft o inferencia; no se terminó ningún proceso.
- GPUs: dos RTX 3090, 0% compute; ArtCraft usa 207 MiB gráficos en GPU0 y se conserva.
- Espacio libre: raíz Docker 9.447.530.496 B; D/NVMe 496.142.651.392 B. Imagen remota ≈167 MB; candidato no descargado.
- No se modifica RAM/swap, driver, modelos conservados, perfiles ASTRA/SOL ni datos/configuración PeritoSoft.

## Interpretación

Este preflight solo prueba detección de dispositivos y configuración de contenedor. No es resultado de calidad, velocidad, compatibilidad de inferencia ni evidencia de superioridad de Gyro-Coder-L.
