# Resultados — Q-20261013-Q4-MTP-CLEANUP

## Estado

La respuesta a si se habían borrado antes es **no**: la tarea anterior sólo
había separado alias de perfiles. Esta limpieza se ejecutó ahora por pedido
explícito del usuario.

## Cambios

- Eliminado el draft MTP dedicado de Flash-Next Q4:
  `models/unsloth-qwen38-flashnext-mtp/mtp-Qwen3.8-Flash-Next-Q8_0.gguf`.
- El archivo medía 4.137.429.120 bytes (3,85 GiB), SHA-256
  `58a47d6a216307e9b97172d5bfdc3436a8994b632f5e436b9bb6edf8951da8d1`.
  La disponibilidad reportada por el filesystem aumentó en 4.137.435.136
  bytes; la carpeta vacía del sidecar también se retiró.
- Los cuatro shards base UD-Q4_K_XL (~104 GiB) se conservaron: los comparten el
  perfil Flash-Next Q4 de Strata y otras configuraciones Q4 vigentes. Quitarlos
  habría roto esos perfiles, que no son los dos brazos llama.cpp MTP.
- No había perfiles activos llamados exactamente `Q4 · llama.cpp MTP-on` ni
  `Q4 · llama.cpp MTP-off`, ni referencias activas al archivo draft. Esos dos
  brazos sólo estaban definidos en los recibos/scripts históricos de la
  evaluación; se conservan para no perder configuración, eventos ni resultados.
  No se borraron ni editaron `profiles/profile_history.jsonl` ni los artefactos
  de `Q-20261010-UNSLOTH-MTP-AB`.

## Verificación

Antes de borrar se cotejaron tamaño y SHA-256 contra el recibo histórico; el
lock seguía perteneciendo a esta tarea; el draft no estaba abierto por ningún
proceso y su directorio contenía únicamente ese archivo. Después se confirmó
que tanto archivo como directorio ya no existen, que no queda otra copia con el
mismo nombre bajo `/media/cristian`, y que informes/recibos de la evaluación
siguen presentes. No se usaron GPU, servidores, inferencia ni descargas.

## Próxima acción

No volver a ejecutar estos perfiles con los artefactos locales actuales. El
brazo MTP-on sólo podría reconstruirse descargando otra vez el draft; ambos
perfiles seguirían superando el corte de 30 minutos por corrida. El historial
permanece disponible en
[`Q-20261010-UNSLOTH-MTP-AB`](../Q-20261010-UNSLOTH-MTP-AB/RESULTS.md).

Recibos: [`cleanup-preflight.json`](receipts/cleanup-preflight.json) y
[`cleanup-result.json`](receipts/cleanup-result.json).
