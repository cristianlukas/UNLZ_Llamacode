# Resultado: Flash-Next Q4 en dos RTX 3090

## Veredicto

La prueba sí se ejecutó usando **las dos RTX 3090**. Unsloth UD-Q4_K_XL
completó el núcleo LC-H1 con 29/29 casos finales (25/29 en el primer intento)
y ADV v1 con 10/10 finales (7/10 en el primer intento). Los casos que fallaron
al principio se recuperaron dentro del límite de reparación. Es un screening
local positivo para coding/agentes; una corrida no demuestra superioridad ni
justifica cambiar perfiles productivos.

Es una prueba representativa de “Flash-Next Q4”, porque el post no especifica el
GGUF exacto. No replica las 4×P100, Q8 KV ni el contexto de 262K del post.

## Método y configuración

- Modelo: `unsloth/Qwen3.8-Flash-Next-GGUF`, revisión
  `38bb39ee97821de2c9009abb7e93950eec396e66`, cuantización UD-Q4_K_XL. Los cuatro
  SHA-256 de shard están en `receipts/manifest.json` y se verificaron contra la
  revisión.
- Runtime: Strata 0.1.41, commit
  `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`, build local CUDA 12.8 / SM86.
- Hardware usado: GPU 0 y GPU 1, NVIDIA GeForce RTX 3090 de 24 GiB cada una;
  split de capas 18/30, `--resident-experts`, reserva de 2048 MiB. Se observó
  salida balanceada: alrededor de 22.0 y 22.2 GiB ocupados por tarjeta en HE0.
- Contexto máximo 131072, KV int8 con 32768 tokens residentes, MTP/spec 4,
  `spec-min-p=0.70`, una solicitud concurrente. El runtime no expuso visión.
- Harness LlamaCode LC-H1: `agent-maximo`, thinking activado, R4096, seed 4242,
  hasta 3 reparaciones; HarnessSpec
  `cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`.
  Se mantuvo el mismo harness y los mismos IDs de suite que la evaluación
  Strata de referencia.
- Fingerprint de perfil: `09d45e63b1f548df63775d947a051a70ca66561bb5a04bcf292050eb8bcb2958`.

## Resultados

| Suite | Primer intento | Final | Reparaciones | Tiempo | TPS promedio de la suite |
|---|---:|---:|---:|---:|---:|
| HumanEval (1) | 1/1 | 1/1 | 0 | 23,1 s | 55,0 |
| HumanEval (20) | 20/20 | 20/20 | 0 | 1283,2 s | 56,9 |
| BigCodeBench-Hard (8) | 4/8 | 8/8 | 2 | 848,9 s | 59,1 |
| ADV v1 (10) | 7/10 | 10/10 | 2 | 2347,1 s | 59,7 |
| **Total** | **32/39** | **39/39** | — | **4502,3 s (75 min)** | — |

Los recibos completos están en `receipts/results/`. `adv10.json` conserva la fila
cruda exportada de LlamaCode, incluidas métricas por llamada y verificaciones de
aceptación. Ninguna suite tuvo timeout ni fallo de infraestructura.

## Rendimiento y estabilidad observados

Durante las suites, LlamaCode registró entre 55,0 y 59,7 tok/s de promedio por
suite. El estado de Strata durante generación informó aproximadamente 54–58
tok/s de decode y 53–77 tok/s de prefill en muestras individuales. Son cifras
observadas dentro de las tareas de coding, no un Server Speed v1 independiente
ni una comparación apareada.

En la muestra de carga, Strata informó las dos 3090 (49.152 MiB combinados,
48 GiB); el máximo observado fue 46.249 MiB usados (45,2 GiB) y temperatura de
hasta 68 °C. La RAM usada rondó
61 GiB de 123,5 GiB y el swap permaneció por debajo de la guarda de 2 GiB.
No se observaron errores CUDA, OOM ni timeout. Al cierre se detuvieron el
daemon de LlamaCode y Strata; los puertos 8898 y 8350 quedaron cerrados y las
GPU volvieron a 743 MiB y 108 MiB ocupados respectivamente.

## Transferencia y límites

- El antecedente dual del mismo checkpoint con Strata 0.1.39 también terminó
  39/39 en LC-H1. Es coherencia histórica, no una comparación controlada de
  versiones: sólo hay una corrida por configuración y no se puede atribuir una
  diferencia de tiempo a Strata, cuantización o variabilidad.
- No se ejecutó TaskFlow ULTRA ni Server Speed v1 independiente; las métricas
  TPS anteriores provienen de las suites LC-H1/ADV.
- No se intentó 262K. Esta ejecución usó máximo 131K y no incluyó un corpus de
  recuperación larga con posiciones verificables.
- Computer Usage GUI E2E, visión e Ingi-Charla acústica quedan sin evaluar:
  faltan fixtures/verificadores adecuados y Strata reportó visión desactivada.
- No se cambiaron perfiles, HarnessSpec ni valores de producción.

## Artefactos

- [Plan y recibos de ejecución](.)
- Resultados individuales: `receipts/results/he0.json`, `he20.json`,
  `bcb8.json`, `adv10.json`.
- Configuración dual efectiva: `receipts/configs/q4-udq4kxl-main.json`.
- Log de carga/runtime: `receipts/logs/q4-strata-engine-dual-gpu.log`.
