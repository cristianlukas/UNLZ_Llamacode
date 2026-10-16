# Resultados — Q-20261016-FLASHNEXT-FOLLOWUP

**Estado: screening parcial bloqueado por preflight de swap. Sin promoción ni
cambios productivos.** Se reutilizó Strata 0.1.41 y Qwen3.8 Flash-Next UD-Q4_K_XL
local, en 2×RTX 3090 con split 18/30. Los shards ya tenían hashes verificados en
Q-20261010-FLASHNEXT-Q4-P100-POST; no se volvieron a leer 111 GB.

## Server Speed v1 con y sin `--trim-stage-weights`

Se completó un único par, A/B, con 8 categorías y mediciones cold/warm (16 por
brazos), temperatura 0, top-p 1, seed 424242 y una solicitud a la vez. La
prueba fue HTTP directo al servidor Strata, con el corpus
`assets/benchmarks/server_speed_v1.json` (SHA-256
`4bad8a5d24ce11096eb9634f7d03f24b83734c3f454031efb28d5fa259c996e9`); no fue una
sesión completa de la aplicación LlamaCode. Runner SHA-256
`c9aa0f451f016d7b3fd5f28ee62b075afad4f14c93543b634f5d2669b782bd2d`; hashes
de configuración base A/B `753ffb83dcc473ae3d50b019067a74bac40f994cb8083ea9bdf652acb8483e01` /
`1bc0e6e41ed219ccb443e5b171c49f1bfa0ae95ace96448c0c86bd87a20f9787`.

| Métrica | A: sin trim | B: trim | Delta B−A | Lectura |
|---|---:|---:|---:|---|
| Decode medio | 65,35 tok/s | 63,61 tok/s | −1,74 tok/s (−2,7%) | B algo más lento |
| Prefill medio | 64,11 tok/s | 46,48 tok/s | −17,63 tok/s (−27,5%) | B más lento |
| TTFT medio | 1.628 ms | 2.418 ms | +790 ms (+48,5%) | B más lento |
| Latencia total media | 4.086 ms | 4.958 ms | +873 ms (+21,4%) | B más lento |
| Hash de respuesta distinto entre A/B | — | — | 13/16 muestras | Las salidas no fueron idénticas |

Estos son datos de un solo par; no permiten afirmar una regresión estable ni
una mejora. Tampoco evalúan calidad. El criterio preregistrado pide tres pares
con dirección consistente y diferencia superior al ruido. No se alcanzó.

El brazo A cargó en 146 s y duró 222 s; B cargó en 141 s y duró 246 s. Los dos
terminaron las 16 solicitudes, liberaron el puerto 8350 y no tuvieron OOM. En A,
MemAvailable mínimo 60,63 GiB, SwapFree mínimo 0,76 GiB y PSI memory `some`
avg10 máximo 13,9%. En B, mínimo 65,34 GiB, SwapFree mínimo 0,77 GiB y PSI
máximo 13,68%. Después de B quedaron 0,77 GiB de swap libre. El siguiente
arranque se detuvo antes de cargar Strata porque el preflight exige al menos
1 GiB; el recibo registra 0 muestras, puerto libre y ninguna inferencia.

### Incidencias del arnés

- El primer intento lanzó `/usr/bin/python3` y falló en la importación de
  `regex`; no cargó el modelo ni produjo muestras. Se conserva separado como
  `receipts/server-speed/pair01-A-order01-system-python-failure/`.
- Con el `.venv` de Strata, A sí completó. El arnés falló después al resumir un
  solo brazo vacío; se corrigió para reanudar desde recibos completos sin
  repetir muestras y se verificó con `py_compile` y smoke de resumen parcial.
- La guarda de swap se amplió antes de B: abortar también si SwapFree queda
  bajo 0,5 GiB durante 15 muestras. El control de 1 GiB al inicio se mantuvo.

## Ramas no ejecutadas

El probe Q4 de contexto 262K, visión Q4 y las réplicas base pendientes de
Computer Usage para ASTRA/Q4 no se lanzaron: al cerrar B había 0,77 GiB de
SwapFree, por debajo del preflight de 1 GiB. El `mmproj` y el encoder estaban
disponibles en la inspección local, pero no se envió una imagen. No se hizo una
prueba de audio: Flash-Next no tiene endpoint local ASR/TTS verificado y no se
simuló audio con texto.

Se reutiliza, sin repetir, la evidencia válida Q4 ya registrada: coding/agents,
ADV, TaskFlow Q4 (13/13 después de dos reparaciones) y tool-eval de
Q-20261010-FLASHNEXT-Q4-P100-POST y Q-20261014-R9700-TASKFLOW. No se cambiaron
perfiles, HarnessSpec, defaults ni prompts productivos. No aplican build ni
tests de C++/QML; sólo se validó el runner Python.

## Reanudación

Reanudar como tarea nueva después de que un preflight fresco confirme
SwapFree ≥1 GiB, MemAvailable ≥32 GiB, puerto 8350 libre y GPUs sin inferencia
ajena. Conservar el par 1 y empezar por `pair02-B-order01` usando el runner
resumible; no volver a ejecutar pair 1. Luego completar pares 2 y 3, y sólo
después intentar contexto, visión y Computer Usage en serie, cada rama con su
propio preflight. La configuración, script y recibos están en este directorio.
