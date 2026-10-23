# Q65 — diagnóstico del nuevo cierre de Codex

**Cierre:** 2026-10-23T20:38:00Z
**Estado:** diagnóstico completado; causa del cierre no demostrada. El hallazgo nuevo y más accionable es que el proceso principal de Codex seguía ejecutando una imagen antigua que el upgrade ya había reemplazado.

## Evidencia

- El upgrade de apt del 23/10 entre 11:31:22 y 11:33:29 (-03:00) actualizó el paquete `chatgpt` de `26.930.51102` a `26.1016.61520`, además de componentes de NVIDIA y escritorio.
- El proceso principal `ChatGPT` PID 7630 se inició el 22/10 a las 22:28 (-03:00) y seguía vivo al revisar el incidente. `/proc/7630/exe` apunta a `/usr/lib/chatgpt/ChatGPT (deleted)`, inode 5899627, 319.425.760 bytes. El ejecutable instalado ya es otro inode (5898276), 322.870.496 bytes. Por lo tanto, la instancia principal no se había reiniciado después del upgrade y conservaba el binario reemplazado en memoria.
- Al mismo tiempo había renderers nuevos (PIDs 3470384/3470385, iniciados 17:34:23 -03:00) y un `codex exec-server` nuevo (PID 3470773, 17:34:27). Esto es compatible con una recreación de renderer/superficie UI mientras el main Electron antiguo permanecía vivo; no demuestra qué ventana o subproceso observó el usuario.
- Crashpad no contiene un reporte nuevo posterior a esa hora. El reporte más reciente es `gpu-process` de 08:47:17 -03:00 y no hay minidumps. `coredumpctl` no está instalado. El journal de usuario/kernel consultado desde 17:15 no mostró segfault, OOM kill ni terminación de Codex; la única línea kernel reciente de NVIDIA fue generada por el `nvidia-smi` diagnóstico.
- El boot de Ubuntu sigue siendo 22/10 22:26:57 (-03:00). `nvidia-smi` continúa fallando con exit 18: userspace/NVML 615.71.09 frente a módulo cargado 610.57.04. No hay procesos o puertos identificados como servidores de inferencia. Listeners observados: ArtCraft 47413, puerto sin atribuir 35751, DNS 53, CUPS 631 y OpenRGB 6742.
- En el snapshot posterior al reporte había 110 GiB disponibles, 692 KiB de swap usada y PSI de memoria avg10/60/300 en 0. Es una medición posterior, no descarta presión en el instante del cierre.

## Conclusión y siguiente paso

El nuevo hallazgo no prueba la causa, pero sí revela que Codex no se había reiniciado completamente tras la actualización. Primero salir de Codex por completo y volverlo a abrir; comprobar que el proceso main nuevo tenga inicio posterior al upgrade y que `/proc/<pid>/exe` ya no termine en `(deleted)`. Si el cierre vuelve a ocurrir con el proceso actualizado, guardar inmediatamente Crashpad/minidump y correlacionarlo con la hora exacta.

La desalineación NVIDIA sigue siendo una segunda condición independiente: reiniciar Ubuntu y confirmar módulo/NVML alineados antes de reanudar Q56. No se cambiaron políticas de memoria/contexto ni configuración del sistema.

**Actividad:** sólo inspección local y consulta `nvidia-smi`; no se iniciaron servidores, inferencia, requests, benchmark ni workload de GPU. No se alteraron modelos, perfiles, GUI o datos.

## Sincronización

El hallazgo se actualizó y leyó de vuelta en `Accionables!H2:N2`; Q65 se añadió y leyó de vuelta en `Evaluaciones LlamaCode!A287:J287`. Las celdas existentes mantienen `WRAP`/alineación superior. Recibo `receipts/google-sheet-sync.json`.
