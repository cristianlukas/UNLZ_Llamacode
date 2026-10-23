# Q60 — Resultado: aislamiento de workers Linux

**Estado:** auditoría Linux completada; P0 global sigue parcial por cobertura Windows pendiente.
**Lock:** `f26d05c9-7c30-4588-b24a-973afc127388`
**Cierre:** 2026-10-23T14:57:25Z

## Resultado

- La suite `python3 -m unittest tests.test_linux_eval_scope -v` pasó **4/4** en el recheck de cierre.
- El canario preregistrado P60-A1 pasó: el padre Python y su hijo `sleep` quedaron dentro de la misma unidad `background.slice`, con `oom_score_adj=900`. La unidad reportó `OOMPolicy=kill`, `KillMode=control-group`, `ManagedOOMMemoryPressure=kill`, `ManagedOOMSwap=kill` y límites `MemoryHigh/MemoryMax/MemorySwapMax=infinity`. Al detener el scope ambos procesos desaparecieron. Ver `receipts/linux-scope-canary-P60-A1.json`.
- `tools/meter_system_profiles.py` apunta a `D:/.../llama-server.exe` y `C:/...`; es una ruta de Windows y no se puede dar por cubierta con la prueba Linux. Para esa ruta y los launchers PowerShell siguen pendientes Job Objects y regresiones en Windows nativo.
- `Accionables!D2:N2` se leyó de vuelta por API y coincide con el resultado, las pruebas y la condición Windows. El recibo está en `receipts/google-sheet-p0-sync.json`; la vista visual no se pudo revisar porque CUA no tenía una superficie abierta.

## Alcance y conclusión

La prueba confirma que el scope Linux existente puede contener el ciclo de vida de un árbol de workers sin bajar los límites de memoria solicitados por los modelos. **No demuestra que toda causa del cierre de Codex esté resuelta** ni valida Job Objects de Windows; por eso el accionable global conserva estado parcial. No se modificó código ni se alteraron presupuestos de memoria, VRAM, contexto o sampling.

El chequeo de host de cierre volvió a detectar que el update instaló NVIDIA `615.71.09`, mientras este arranque conserva cargado `610.57.04`; `nvidia-smi` sigue reportando mismatch. El arranque actual es `2026-10-22 22:26:57`. No se inició ningún servidor de inferencia, request, benchmark ni trabajo de GPU. Q56 sigue bloqueada antes de inferencia hasta reiniciar Ubuntu y confirmar que NVML y el módulo cargado coincidan.

## Archivos de evidencia

- `PLAN.md` — alcance y preregistro P60-A1.
- `receipts/linux-scope-canary-P60-A1.json` — propiedades de unidad, PIDs, test unitario y resultado.
- `receipts/google-sheet-p0-sync.json` — actualización y readback de Sheet.

## Continuación

1. En Ubuntu, después del reinicio pendiente, volver a comprobar `nvidia-smi`, módulo cargado y servidores de inferencia antes de decidir si Q56 puede arrancar.
2. En una sesión Windows nativa, auditar y probar Job Objects en `meter_system_profiles.py` y los launchers PowerShell; no extrapolar el canario Linux.
