# Plan de continuación — Q-20261016-FLASHNEXT-RESUME2

- Inicio: 2026-10-16, lock `68392897-0073-43b0-986b-107003fe6f38`.
- Pedido explícito del usuario: ejecutar las pruebas pendientes del programa de evaluación.
- Reusar los pares 1 y 2 ya completos; no repetir sus 64 muestras.

## Alcance

1. Terminar pair 3 (A/B) de Server Speed v1 con el mismo Q4 UD-Q4_K_XL, Strata
   0.1.41, split, corpus, configs y seed; conservar recibos en la campaña original.
2. Si pair 3 completa sin abortos, intentar en serie el retrieval Q4 262K, la
   prueba visual Q4 con el fixture congelado y las réplicas base CU ASTRA/Q4 en
   Xvfb privado, cada una con preflight fresco. No enviar audio como texto.
3. No repetir coding/agentes, ADV, TaskFlow ni tool-eval: reutilizar sus recibos
   Q4 anteriores. No cambiar perfiles, harness ni producto.

## Guardas de esta continuación

Los intentos previos terminaron con MemAvailable mínimo de 62,84 GiB, PSI avg10
máximo 0,47 y OOM 0, aunque SwapFree quedó en 0,499 GiB. Linux puede conservar
páginas frías en swap después de que vuelva a haber RAM libre; por eso SwapFree
no es un indicador aislado de presión y queda como telemetría. El preflight
requiere MemAvailable ≥32 GiB, GPU libre, puerto libre y PSI por debajo del
umbral de aborto. Durante la carga se aborta si MemAvailable <20 GiB durante
15 muestras, PSI memory some avg10 ≥80 o full avg10 ≥60 durante 15 muestras, o
aumenta `oom_kill`. No limpiar swap ni interrumpir procesos ajenos.

## Reanudación

El runner copia `scripts/run_server_speed_trim_ab.py`; omite brazos ya completos
mediante sus recibos. El preflight inicial está en `receipts/preflight-start.json`.
Si un brazo se bloquea/aborta o un screen no pasa su gate, registrar el recibo,
actualizar la fila y cerrar bloqueada. Si todo completa, resumir los tres pares
sin declarar mejora estable si la dirección no coincide y dispersión domina.

## Estado al cierre

Los tres pares A/B terminaron y validaron 96/96 muestras; no hay dirección
estable para promover `--trim-stage-weights`. El intento 5 de contexto recuperó
la clave exacta en 258.046 tokens de contenido y terminó sin OOM. Visión Q4 dio
9/11 campos exactos. En Computer Usage, la revisión manual de capturas dio
ASTRA 3/3 y Q4 1/3; Q4 duplicó texto en el editor. Detalle y evidencia en
`RESULTS.md` y `receipts/cu-manual-review.json`.

El swap no se limpió ni alteró. ASTRA completó CU con mínimo 52,7 GiB de
MemAvailable aunque SwapFree llegó a 12 KiB; PSI some avg10 máximo 37,2 y OOM
0. Q4 mantuvo 55,5 GiB disponibles con SwapFree mínimo 26,3 MiB, PSI máximo
9,76 y OOM 0. SwapFree se conserva como telemetría, mientras la guarda usa
MemAvailable, PSI, OOM, GPU y puertos. Servidores propios y puertos quedaron
libres tras cada corrida.

Se reutilizaron coding/agentes, ADV, TaskFlow y tool-eval Q4; no se repitieron.
Audio no se simuló porque no hay endpoint local ASR/TTS verificado. Las
validaciones de scripts y recibos están descritas en `RESULTS.md`; no hubo
cambios de C++/QML ni tests de producto.

Postflight 22:59Z: MemAvailable 107,99 GiB, SwapFree 239,7 MiB, PSI avg10 0,
OOM 0, puertos del benchmark libres y sin procesos de cómputo CUDA. Recibo:
`receipts/postflight-20261016T2259Z.json`.
