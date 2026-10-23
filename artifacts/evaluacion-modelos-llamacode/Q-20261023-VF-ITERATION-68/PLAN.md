# Q68 — Recertificar post-reinicio y reanudar Q56

- **Estado:** activa; Q56 no inició servidor ni requests todavía.
- **Lock token:** `0bbd4847-1a31-436c-a45e-785a230d9c8f`.
- **Alcance:** revisar el estado de Codex/NVIDIA tras el reinicio, interpretar la captura enviada, corregir mediante enmienda preregistrada los guardas estáticos que impedirían Q56, verificar en CPU y Sheets, y continuar sólo la matriz predefinida si todos los gates vuelven a pasar.
- **No cambiar:** modelo, perfiles, prompts, fixtures, seeds, contexto, orden de seis requests, criterio de puntuación. Preservar ASTRA, SOL, Flash-Next de producción, PeritoSoft, modelo original en cuarentena y staging.

## Estado observado

- Boot Ubuntu: `2026-10-23 18:17:11`; módulo NVIDIA 615.71.09; NVML 615.71.09; `nvidia-smi` exit 0; sin marcador de reinicio pendiente.
- Codex 26.1016.61520, PID 7127, ejecutable `/usr/lib/chatgpt/ChatGPT`, iniciado 18:18:12 y vivo al recheck. No hay nuevo artefacto Crashpad posterior al reboot; esto no prueba la causa de cierres anteriores.
- No se hallaron servidores de inferencia; puertos 8352 y 35751 libres. MemAvailable 116.2 GiB; PSI memory some/full 0; ambas RTX 3090 tienen >22 GiB libres; staging C: conserva 44.7 GiB (>40 GiB).
- La captura corresponde a LinuxGameHub, no a Codex. Se instaló una extensión NVIDIA Flatpak de usuario que faltaba y se verificó la biblioteca desde el sandbox. Tras el mensaje del usuario indicando que se encarga de LinuxGameHub, no se harán más acciones sobre esa app.

## Siguiente paso

1. Ejecutar la prueba CPU del helper de normalización A2 y el preflight fresco de Q56; registrar recibos.
2. Sincronizar y leer de vuelta Evaluaciones LlamaCode!C286/G286:J286, Accionables!D3/H3:N3 e Inventario de modelos!C11/R11.
3. Si el canario `systemd --user` demuestra el cgroup y límites preregistrados, iniciar el runner Q56 sólo como servicio durable, con GPU serial y seis requests de una en una.
4. Si falla cualquier gate o el runner aborta, no retry; guardar resultado, limpiar sólo proceso/servicio propio y dejar condición concreta.
