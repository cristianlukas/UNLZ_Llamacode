# Q66 — Recheck posterior al diagnóstico Q65

Inicio: 2026-10-23T20:39:27Z
Lock: `6d6aa2b1-8731-4086-bf7d-392fe3a59309`

## Preguntas

1. ¿El proceso principal de Codex se cerró y abrió desde el paquete actualizado, eliminando la imagen `/proc/<pid>/exe` marcada `(deleted)`?
2. ¿Ubuntu se reinició tras instalar NVIDIA 615.71.09 y ahora el módulo cargado coincide con NVML?
3. ¿Está Q56 habilitada para continuar con su preregistro existente?

## Alcance y orden

- Primero leer sólo hora de boot y procesos/listeners para excluir inference servers.
- Revisar el proceso principal y renderer de Codex sin leer contenido de usuario.
- Sólo después del chequeo de servidores consultar `nvidia-smi` y `/proc/driver/nvidia/version`.
- No matar procesos, cerrar la GUI ni reiniciar el equipo desde esta tarea.
- No modificar memoria/contexto, perfiles, modelos, staging ni el preregistro Q56.
- Ejecutar Q56 en serie sólo si el proceso Codex está actualizado, Ubuntu reinició tras el update, NVML/módulo coinciden, no hay servidor de inferencia ajeno y cada gate de Q56 vuelve a pasar. Ante cualquier fallo, documentarlo y detenerse sin iniciar inferencia.
