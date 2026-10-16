# Resultados — Q-20261016-FLASHNEXT-RESUME2

**Estado: screening completado, parcial y sin promoción.** Se completaron las
pruebas factibles de esta reanudación; audio quedó fuera por no haber un
endpoint local ASR/TTS verificado. No se modificaron perfiles ni producto.

## Server Speed v1: A/B de `--trim-stage-weights`

Qwen3.8 Flash-Next UD-Q4_K_XL, Strata 0.1.41, dos RTX 3090, split 18/30,
mismo corpus/hash, seed 424242, ocho categorías cold/warm, temperatura 0,
top-p 1 y una solicitud a la vez. HTTP directo al servidor: mide rendimiento,
no calidad ni sesión de la aplicación.

| Par | Orden | Métrica | A sin trim | B con trim | B−A | Hashes distintos |
|---|---|---|---:|---:|---:|---:|
| 1 | A/B | Decode / prefill | 65,35 / 64,11 tok/s | 63,61 / 46,48 tok/s | −2,7% / −27,5% | 13/16 |
| 1 | A/B | TTFT / latencia total | 1.628 / 4.086 ms | 2.418 / 4.958 ms | +48,5% / +21,4% | 13/16 |
| 2 | B/A | Decode / prefill | 65,20 / 73,26 tok/s | 70,26 / 78,33 tok/s | +7,8% / +6,9% | 12/16 |
| 2 | B/A | TTFT / latencia total | 1.421 / 3.883 ms | 1.333 / 3.623 ms | −6,2% / −6,7% | 12/16 |
| 3 | A/B | Decode / prefill | 65,72 / 72,16 tok/s | 70,01 / 80,40 tok/s | +6,5% / +11,4% | 11/16 |
| 3 | A/B | TTFT / latencia total | 1.440 / 3.880 ms | 1.304 / 3.583 ms | −9,4% / −7,7% | 11/16 |

Los pares 2 y 3 favorecen trim en las cuatro medias; el par 1 da el signo
opuesto. Como la dirección no es consistente en los tres pares, no hay mejora
estable y no se promueve el flag. Los hashes distintos no miden calidad. La
validación offline pasó para 96/96 muestras, IDs únicos, hashes y configs;
detalles en [`receipts/server-speed-validation.json`](receipts/server-speed-validation.json)
y los recibos fuente en
[`Q-20261016-FLASHNEXT-FOLLOWUP`](../Q-20261016-FLASHNEXT-FOLLOWUP/receipts/server-speed/).

## Contexto Q4 a 262K

El intento 5 completó una recuperación exacta: contexto 262.144, contenido
258.046 tokens medidos localmente y clave en la posición 0,94983. Devolvió
`LC-95P-7D3A9C` exactamente; prefill 1.864 tok/s y 138,46 s, decode 49,1
tok/s. Recibo en [`receipts/context262k-attempt-05.json`](receipts/context262k-attempt-05.json).

Los intentos no puntuables anteriores quedan separados: el 2 falló por el
lector SSE; el 3 procesó el prompt, pero el presupuesto de salida se consumió
en razonamiento; el 4 fue abortado por la guarda anterior de SwapFree con
62,84 GiB disponibles, PSI bajo y OOM 0. El intento 5 retiró ese corte aislado
y terminó sin OOM; MemAvailable bajó aproximadamente de 63,9 a 62,9 GiB y
SwapFree de 0,485 a 0,442 GiB. La guarda efectiva usa MemAvailable, PSI y OOM;
SwapFree queda como telemetría.

## Visión Q4

El holdout obtuvo **9/11 campos exactos**: formas 4/4 y conteos de color 5/7.
Contó cero amarillos en vez de uno y dos naranjas en vez de uno. La petición
multimodal terminó en 12,243 s sin error de transporte. No pasa exact match;
no se promueve. Recibo y fixture congelado en `receipts/vision-attempt-01.json`
y `receipts/vision-attempt-01-preflight.json`.

## Computer Usage: réplica base 2

La revisión manual de capturas prevalece sobre el OCR automático, que no lee de
forma fiable el cuerpo del editor. Resultado detallado y hashes en
[`receipts/cu-manual-review.json`](receipts/cu-manual-review.json).

- **ASTRA IQ3_S: 3/3 tareas completas.** Calculadora 1387; línea inglesa exacta
  en el editor; luego resultado 1363 y reemplazo exacto en español, con el
  documento sin guardar.
- **Flash-Next Q4: 1/3 completa.** Calculadora 1387 pasó. El editor duplicó la
  línea inglesa; en la tercera tarea mostró 1363 y agregó la línea española,
  pero dejó también el texto inglés duplicado, así que no completó el reemplazo.
- El OCR automático registró 2/3 para ambos perfiles; la inspección de las
  capturas cambia la puntuación efectiva de ASTRA a 3/3 y Q4 a 1/3.

ASTRA usó como mínimo 52,7 GiB de MemAvailable; SwapFree llegó a 12 KiB, PSI
memory some avg10 máximo 37,2 y OOM 0. El kernel movió 37.693 páginas (unos
147 MiB) a swap durante la corrida. Q4 conservó como mínimo 55,5 GiB
disponibles; SwapFree mínimo 26,3 MiB, PSI avg10 máximo 9,76 y OOM 0. Ambas
sesiones terminaron normalmente y liberaron servidor, puerto y Xvfb privado.

## Alcance reutilizado y validaciones

Coding/agentes, ADV, TaskFlow y tool-eval Q4 se reutilizaron desde recibos
anteriores válidos; no se repitieron. No hay endpoint local ASR/TTS verificado,
por lo que no se simuló audio como texto.

Pasaron `py_compile` de los runners, validación JSON de configs/recibos, hashes
de las muestras A/B y `git diff --check`. No se tocó C++, QML ni el producto,
así que no aplicaban build ni tests del producto. Los servidores propios
terminaron y sus puertos quedaron libres. No se alteró el swap ni se detuvieron
procesos ajenos.

El postflight a las 22:59Z registró MemAvailable 107,99 GiB, SwapFree 239,7 MiB,
PSI some/full avg10 0, OOM 0, puertos de tarea libres y cero procesos de cómputo
CUDA. Ver [`receipts/postflight-20261016T2259Z.json`](receipts/postflight-20261016T2259Z.json).
