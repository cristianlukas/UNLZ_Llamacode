# Q38 · Reanudación iterativa VF-20261019-01

Fecha: 2026-10-22 16:26 UTC
Lock: `Q-20261022-VF-ITERATION-38`

## Resultado de esta iteración

No se ejecutó inferencia, benchmark de modelo, build ni prueba GPU. El host de
esta sesión tras el reinicio continúa siendo Ubuntu 24.04; no expone
`powershell.exe`, `pwsh` o `cmd.exe`. El preflight encontró cero procesos de
inferencia y ningún listener de evaluación. Se preservaron servidores y modelos.

### P0 · aislamiento de workers

La inspección estática encontró dos niveles distintos:

- `src/core/agent/HarnessSandbox.cpp` implementa Job Objects en Windows y
  `systemd-run --user --scope`/bubblewrap en Linux para los workers que la app
  lanza mediante ese módulo. El backend Linux genérico de este módulo aplica
  `MemoryMax`, `TasksMax` y `CPUQuota` cuando se piden; no configura por sí solo
  `MemorySwapMax` ni `OOMPolicy=kill`.
- La regresión de Q36/Q37 y el worker Q35 quedaron aislados bajo unidades del
  system manager en `background.slice`, con `MemoryMax`, `MemorySwapMax`,
  `OOMPolicy=kill` y `KillMode=control-group`; las pruebas sintéticas previas
  confirmaron que un OOM del worker no mata al controlador/Codex.
- Los runners genéricos de `tools/` y `scripts/` no usan esa frontera de forma
  consistente. `tools/kv_cache_ab.py`, `tools/meter_system_profiles.py` y
  `scripts/run-astra-strata.sh` inician procesos directamente; los scripts
  PowerShell de campañas/benchmarks enumerados en
  `receipts/launcher-audit.json` usan `Start-Process` sin Job Object visible en
  sus puntos de entrada. El audit es estático; no se ejecutó ninguno de ellos.

**Decisión:** P0 continúa recomendado. El aislamiento Q35/Q37 es válido para ese
runner y sus pruebas, no es una garantía global. Próximo trabajo justificable:
crear un launcher común que aplique límites de memoria/swap, política OOM y
cleanup de árbol en Linux/Windows, y añadir regresiones de contención antes de
reanudar pruebas model-backed mediante esos entrypoints. Mantener OOMD activo;
no bajar contexto, pesos ni cuantización para ocultar el problema.

### P1 · Qwen3.8 Flash-Next con NInfer

La fuente primaria cambió desde el gate Q32: Don-Chad publicó v0.16.1 con
runtime Windows x64. Flash-Next sigue siendo preview y el release explícitamente
no lo incluye en su prueba local de inferencia. El README documenta su
conversión desde el GGUF IQ2_XS a un contenedor NInfer y un volumen n-gram.

La búsqueda local encontró los dos shards GGUF Flash-Next IQ2_XS en `Disco
local`, pero sólo runtimes Windows antiguos v0.4.0 y v0.6.1 en rutas de
evaluación; no encontró un `.ninfer` v3 ni runtime v0.16.1 en las raíces
consultadas. El host actual no puede ejecutar el paquete Windows. La prueba
NInfer/Strata sigue **pendiente por acceso de ejecución Windows y artefacto
convertido compatible**; no se compara con el benchmark publicado ni se altera
el perfil Flash-Next productivo.

Reapertura preregistrable cuando la ejecución Windows esté conectada a esta
tarea: verificar driver/runtime/checksum; convertir/copiar el IQ2_XS exacto y
su volumen n-gram a un destino con espacio suficiente; confirmar el modelo
v3 y la ruta Windows; luego ejecutar una comparación serial con contexto,
prompts y medidas emparejadas contra Strata. Separar throughput, calidad y
estabilidad; ningún cambio productivo por una prueba aislada.

### Fuentes bloqueadas revalidadas

Se mantuvieron #26 (H3/KV cartridges: A100/Qwen2.5-72B, sin reproducción
local compatible), #28 (anécdota Flutter→SwiftUI sin repo/fixture/criterio),
#31 (DS41Engine requiere ROCm/HIP y recursos/hardware ausentes) y #32
(Instagram sin caption/transcripción atribuible) como bloqueadas con condición
concreta. No apareció una prueba local que pueda cambiar una decisión. #36
permanece bloqueada por falta de evidencia primaria del Reel.

## Gate de cierre

- Sin GPU/modelo/descargas/build durante esta iteración.
- No se inició ni detuvo ningún proceso ajeno.
- P0 queda abierto hasta resolver la falta de aislamiento de entrypoints.
- P1 queda pendiente para la sesión Windows; no hay comparación válida todavía.
- Recibos: `receipts/launcher-audit.json`,
  `receipts/windows-ninfer-gate.json`,
  `receipts/source-revalidation.json`.

## Sincronización

Se actualizaron `Accionables!A2:N2` (P0 de aislamiento),
`Accionables!A49:N49` (P1 NInfer Flash-Next v0.16.1 pendiente de Windows y
conversión), y se agregó la fila 269 de `Evaluaciones LlamaCode` con el resultado
Q38. El readback confirmó IDs/estados y contenido exactos; se preservó formato
Arial 10 con ajuste de texto y alineación superior. Recibo:
`receipts/google-sheet-sync.json`.
