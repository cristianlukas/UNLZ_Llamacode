# Plan — Q-20261017-LLAMACPP-MTP-CODING-FOLLOWUP

## Objetivo

Completar las etapas de coding/agente que quedaron incompletas en el A/B
histórico `Q-20261010-UNSLOTH-MTP-AB`, a pedido del usuario el 2026-10-17.
No reabrir Hard Mode ni repetir BCB8 MTP-on, que ya tiene un resultado válido
3/8 tras reparaciones. No cambiar perfiles productivos, HarnessSpec ni defaults.

## Perfiles fijados

- Control MTP-off: los mismos cuatro shards locales Unsloth Qwen3.8-Flash-Next
  UD-Q4_K_XL y llama.cpp commit `836d57176dc699a726c55418e4f96b8ca628e1bf`,
  fingerprint histórico `7f84727070a2fb93d008a42c90391f3904d800f7d7c2e67f173813ab0435ff89`.
- Candidato MTP-on: mismos shards/runtime y draft Q8_0 autocontenido original,
  revisión `efc50b7c3195a10eebd8d3e32f83b27b2aeb239d`, SHA-256
  `58a47d6a216307e9b97172d5bfdc3436a8994b632f5e436b9bb6edf8951da8d1`.
  El archivo eliminado por la limpieza previa no está en su ruta original; se
  restaurará sólo en el disco secundario y la ruta del catálogo de la copia aislada
  apuntará allí. Por eso registraré la huella efectiva recién calculada y la
  compararé con `69aacf099a61a10b4370ec10d0fec4d7fa83c93135b6cf57ada8302b664d32b8`;
  mismo contenido no implica huella idéntica si el builder incluye la ruta.
- HarnessSpec: `cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`.
  Runtime/configuración exactos se heredan de `Q-20261010-UNSLOTH-MTP-AB/PLAN.md`
  y `RESULTS.md`; se verifican contra recibos antes de inferencia.

## Pruebas pendientes

1. BCB8 MTP-off: el intento original quedó incompleto en 2/8, sin score válido.
   Reejecutar la suite completa con el mismo fingerprint y protocolo, ya que no es
   reanudable como score de calidad.
2. TaskFlow ULTRA MTP-off y MTP-on: una corrida de screening por perfil, misma
   suite, HarnessSpec, seed, prompt, sampling y máximo de tres reparaciones.
   Registrar primera pasada, cada reparación, aceptación final, tools, archivos,
   tiempos y causas.
3. No repetir HE0, HE20, BCB8 MTP-on, velocidad ni Hard Mode: sus resultados
   válidos ya están archivados y no hace falta duplicarlos para la pregunta actual.

El pedido más reciente del usuario de ejecutar las pruebas restantes autoriza
reabrir sólo estos screens, pese al corte previo que cerró los perfiles. Esto no
habilita una promoción ni una suite de tres seeds; las corridas nuevas siguen
siendo exploratorias y no se reportarán como evidencia estable.

## Guardas

- Lock exclusivo requerido para toda la campaña; token: `b472760c-6225-4b10-a595-d9c6ead5afbd`.
- Preflight antes de descargar/cargar: hashes del modelo base, presencia/hash del
  draft o descarga fijada, espacio, MemAvailable, presión, procesos GPU/VRAM,
  puertos y runtime. No detener procesos ajenos ni cambiar swap.
- Guardas del A/B histórico: exigir al menos 40 GiB de MemAvailable antes de
  cargar; abortar durante la carga si el swap supera en 1 GiB el valor inicial,
  si aparece OOM/error CUDA o si otro proceso de cómputo ocupa una GPU.
- Si el draft no está, sólo restaurar desde la revisión/hash fijados y después de
  confirmar margen de disco. Guardar manifiesto y hash; conservar el archivo
  descargado fuera del árbol versionado. No recrear la ruta de la copia eliminada.
- Abortos/errores de infraestructura no son ceros de calidad. No repetir fallos
  funcionales ni cambiar parámetros para forzar aceptación.
- Si cualquier preflight falla, registrar el bloqueo y detener la inferencia.

## Artefactos

Guardar preflight, configuraciones efectivas, hashes, logs/eventos, resultados y
postflight en `artifacts/evaluacion-modelos-llamacode/Q-20261017-LLAMACPP-MTP-CODING-FOLLOWUP/`.

## Cierre — 2026-10-17

El preflight aprobó el inicio de BCB8 MTP-off con fingerprint
`7f84727070a2fb93d008a42c90391f3904d800f7d7c2e67f173813ab0435ff89`. Durante
la primera tarea, el monitor detectó que el swap usado había subido
2.354.708.480 bytes sobre la base, por encima de la guarda preregistrada de
1 GiB, y canceló benchmark y servidor. No se produjo un score evaluado. El
postflight confirmó el proceso de inferencia y el daemon aislado detenidos,
puertos cerrados y OOM 0, pero menos de 1 GiB de swap libre. Por tanto, TaskFlow
ULTRA MTP-off/on queda sin iniciar y la campaña se cierra bloqueada, no como
fallo de modelo. Ver `RESULTS.md` y `receipts/postflight.json`.
