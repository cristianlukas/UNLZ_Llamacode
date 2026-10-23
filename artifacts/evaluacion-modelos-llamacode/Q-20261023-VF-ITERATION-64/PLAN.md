# Q64 — preflight post-update y puerta de reanudación Q56

**Inicio UTC:** 2026-10-23T16:49:54Z
**Lock:** `6cb3dfb8-8b77-428d-9847-388210fdebda`

## Pregunta de decisión

¿Ubuntu arrancó después de la actualización NVIDIA y quedaron alineados el módulo activo, NVML y `nvidia-smi`? Si sí, ¿están libres los recursos de inferencia y continúa íntegro el staging verificado de Q56?

## Procedimiento registrado antes del preflight

1. Capturar hora, último arranque, kernel y versión del módulo NVIDIA cargado; contrastar con `modinfo` y `nvidia-smi`.
2. Verificar el estado del marcador `/var/run/reboot-required`.
3. Buscar procesos y listeners de inference servers (llama.cpp, Strata, NInfer, vLLM/Ollama) antes de reservar la GPU.
4. Si los gates pasan, confirmar el manifiesto/hash del staging Q56 y continuar con el canario y las seis solicitudes seriales de su preregistro existente. No duplicar ni alterar fixtures.
5. Si un gate falla, no iniciar server/request/GPU; registrar condición y dejar Q56 pendiente.

## Protecciones

No reiniciar el equipo desde esta tarea, no descargar/reemplazar módulos en caliente, no instalar paquetes, no modificar límites de memoria, no tocar GUI, modelos productivos, ASTRA, SOL, Flash-Next productivo, PeritoSoft ni origen de cuarentena.
