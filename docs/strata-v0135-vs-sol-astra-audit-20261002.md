# Strata 0.1.35 vs. SOL y ASTRA — auditoría local

Fecha: 2026-10-02  
Estado: integrado como perfil local experimental **ASTRA** tras la comparación
agentiva LC-H1. SOL conserva su perfil y configuración.

## Decisión

Strata IQ3_S **no reemplaza SOL ni cambia el harness predeterminado**. En la
evaluación directa inicial obtuvo 1/8, frente al 8/8 histórico de SOL y al 8/8
del pack Qwen Next Q2_K_XL guardado como comparación directa. Luego, en el mismo
harness agentivo LC-H1, Strata obtuvo 10/10 en Intelligence Adversarial v1 y
superó a SOL (8/10) después de las reparaciones permitidas. Para Computer Use, IQ3_S
obtuvo 100% en el corpus de decisiones y seguridad con las tres variantes de
prompt, pero no superó en exactitud el 100% histórico del Qwen3.8-27B Q6. La
compuerta local de promoción también falla porque la variante `sandwich` supera
en más de 5% la latencia de `state-first`. Ese benchmark no ejecuta la GUI real y
no se hizo una pareja con el endpoint productivo de SOL.

Se agregó a la configuración local de esta instalación como perfil opcional
**ASTRA**. Es experimental; SOL no se reemplazó ni se cambiaron los defaults de
coding, Ingi-Charla o el harness. Las evidencias evalúan protocolos distintos:
el 1/8 directo no usa el loop agentivo ni las reparaciones, y no debe presentarse
como resultado de LC-H1.

## Instalación evaluada

| Campo | Valor |
|---|---|
| Runtime | Strata oficial v0.1.35; fuente de release `v0.1.35`, tarball SHA-256 `2a72742ee298746172aefcc8c9de708e5600ad5a9fa9de393632b49d77772b76` |
| Modelo | `ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF`, IQ3_S, revisión de HF `ed59f92082b1e93c0e96d60a8b11aab089b52f09` |
| Configuración | Contexto 131072, KV int8, 32768 tokens KV residentes, MTP4, expert cache automática, layer split en GPU 0 y 1, visión activada |
| Máquina | Ryzen 9 9950X3D, 124 GiB RAM, 2× RTX 3090 24 GiB, driver 610.57.04, CUDA 12.8 |
| API local | OpenAI compatible, puerto 8350; una secuencia residente y cola FIFO |

El engine CUDA y el encoder de visión se compilaron desde el tarball oficial.
Pesos, MTP y encoder viven fuera del repo en
`/media/cristian/7CFE1E0FFE1DC1F6/models/Strata-review-20261002/`; el checkout y
el entorno Python están en `~/.cache/strata-review-20261002/`. No se descargaron
pesos dentro del repo. El setup usó `--no-start`; el servidor sólo se inició al
comenzar las mediciones.

La receta fue:

```sh
./setup.sh --family qwen --model IQ3_S --context 131072 --vision yes \
  --gpus 0,1 --yes --no-start \
  --data-dir '/media/cristian/7CFE1E0FFE1DC1F6/models/Strata-review-20261002/data' \
  --models-dir '/media/cristian/7CFE1E0FFE1DC1F6/models/Strata-review-20261002/models'
```

El servidor de evaluación se inició en el puerto temporal 8350. El hash SHA-256
de ambos packs de entrada quedó anotado en `input-sha256.txt`.

## Resultados

### BigCodeBench-Hard-8

Se reutilizó exactamente el pack y grader de la comparación histórica, con los
mismos IDs y muestreo `temp 0.6`, `top_p 0.95`, `top_k 20`, `min_p 0`, thinking
apagado y tope de 6144 tokens.

| Sistema / artefacto | Aciertos | Tiempo observado |
|---|---:|---:|
| SOL, referencia guardada | 8/8 | 74 tok/s narrativo, 102 tok/s código en la auditoría histórica |
| ASTRA/Qwen Next UD-Q2_K_XL, pack directo 2026-09-23 | 8/8 | 129,7 s por los ocho casos, aprox. 30,3 tok/s decode |
| Strata 0.1.35, Qwen Next IQ3_S | **1/8** | 41,35 s total; media 5,17 s por caso |

Strata sólo pasó `BigCodeBench/870`. Falló `509`, `857`, `310`, `800`, `123`,
`952` y `492`. Los ocho requests llegaron al modelo y se calificaron. La
velocidad de Strata no compensa que siete implementaciones no pasaran los tests.
La fila de ASTRA es una cuantización y un runtime distintos del perfil ASTRA
Q4 actual, por lo que sirve como antecedente de Qwen Next, no como A/B exacto.

### Computer Use

El corpus `computer_use_prompt_order_hard_v1` tiene 24 situaciones, incluidas
63 decisiones de seguridad por cada variante y tres órdenes de contexto. Se
hicieron tres pasadas, semillas 11/42/77, temperatura 0,6, `top_p 0.95`,
`top_k 20`, ocho tokens de salida y thinking apagado:

| Variante | Exactitud | Seguridad | Mediana | P95 |
|---|---:|---:|---:|---:|
| `state-first` | 72/72 | 63/63 | 695 ms | 762 ms |
| `question-first` | 72/72 | 63/63 | 684 ms | 754 ms |
| `sandwich` | 72/72 | 63/63 | 865 ms | 935 ms |

La referencia histórica Qwen3.8-27B Q6 también obtuvo 72/72 y 63/63 en el
mismo corpus. Sus prompts y presupuesto de salida provenían de otra corrida,
así que no uso la latencia histórica de 4,73 s como comparación directa. Las
tres variantes nuevas empatan el resultado de exactitud; la compuerta del runner
marca `FAIL` porque `sandwich` no queda dentro del 5% de la mediana
`state-first`. Son decisiones de texto sobre estado dado: **no** miden
capturas reales, interacción con X11/AT-SPI, recuperación de errores ni clicks.

La primera pasada, guardada como `computer-use-hard.json`, dejó thinking
activado y usó sólo ocho tokens; la salida se agotó dentro de `<think>` y no
contenía una opción final. No representa una medición válida de capacidad. Se
conserva para trazabilidad; el resultado válido es
`computer-use-hard-thinking-off.json`, que usa `reasoning_effort: none`.

### API, herramientas, concurrencia y visión

- Health y `/v1/models`: OK; contexto 131072 e imagen como modalidad de entrada.
- Smoke de código: devolvió `def add(a, b): return a + b`.
- Function calling: emitió `lookup_ticket({"ticket_id":"A-204"})`; el round-trip
  simulado de `LC-42` terminó con el estado y responsable correctos.
- Concurrencia: dos requests simultáneos se serializaron; acabaron a 267 ms y
  492 ms, con 493 ms de pared. Un harness que paraleliza subagentes quedaría
  limitado por la cola de una sola secuencia.
- Visión: leyó `SESSION 17` de una imagen sintética de UI. Es un smoke de OCR,
  no una validación visual general ni una comparación con SOL.
- Ingi-Charla: no se probó voz-a-voz. Strata expone texto e imagen; no sustituye
  los proveedores STT/TTS ni demuestra mejora en la ruta de voz.

## Comparación correcta con ASTRA y el post

El perfil ASTRA guardado apunta a Qwen3.8-Flash-Next UD-Q4_K_XL en cuatro
shards, pero esos pesos no están en los volúmenes montados. Por eso no pude
arrancar ese perfil ni presentar sus cifras como medición nueva. El recibo
disponible `qwen38-q2-vs-sol-20260923.json` corresponde a UD-Q2_K_XL servido por
`llama-server qwen4exp`, no al Q4 ni al runtime Strata.

El post de Reddit es una experiencia anecdótica de un autor con otra máquina,
cuantización IQ3_XXS, harness y tarea de autoclicker. No aporta pack, semillas,
medición de seguridad, comparación con SOL ni corrida reproducible de LlamaCode.
Esta prueba local usó IQ3_S, no IQ3_XXS; no se deben trasladar directamente sus
tokens/s ni el juicio del autor.

## Decisión para no repetir trabajo

- **No repetir** la descarga/build de Strata 0.1.35 ni BCB8 IQ3_S: el recibo es
  `artifacts/strata-v0135-vs-sol-astra-20261002/bcb8.json`.
- El Computer Use válido está en
  `artifacts/strata-v0135-vs-sol-astra-20261002/computer-use-hard-thinking-off.json`;
  no reutilizar el resultado erróneo con thinking activo como score.
- Inputs fijados en `input-sha256.txt`; pruebas auxiliares y métricas están en
  el mismo directorio: `tool-roundtrip.json`, `concurrency-probe.json`,
  `vision-probe.json` y `vision-ui-probe.png`.
- Sólo tendría sentido reabrirlo con un objetivo acotado: A/B del harness
  real de Computer Use contra SOL bajo el mismo runner, mismos tokens,
  prompts y semillas; o una cuantización/runtime diferente que vuelva a pasar
  BCB. No volver a hacer una corrida completa por el post de Reddit.

Comandos de scoring conservados en los recibos:

```sh
python3 artifacts/ornith-1.5-evaluation-20260930/run_bcb.py \
  --url http://127.0.0.1:8350/v1/chat/completions \
  --model qwen3.8-flash-next-iq3_s \
  --out artifacts/strata-v0135-vs-sol-astra-20261002/bcb8.json \
  --max-tokens 6144

python3 artifacts/strata-v0135-vs-sol-astra-20261002/benchmark_computer_use_thinking_off.py \
  --url http://127.0.0.1:8350/v1/chat/completions \
  --model qwen3.8-flash-next-iq3_s \
  --corpus assets/benchmarks/custom/computer_use_prompt_order_hard_v1.json \
  --passes 3 --seeds 11,42,77 --order-seed 4242 \
  --temperature 0.6 --top-p 0.95 --top-k 20 \
  --out artifacts/strata-v0135-vs-sol-astra-20261002/computer-use-hard-thinking-off.json
```

No se tocaron archivos de código, QML, perfiles ni configuración de voz. No
corresponde correr los gates de build/tests del proyecto para esta auditoría.

## Integración local solicitada

El perfil activo ASTRA usa el backend OpenAI-compatible local de Strata:

- URL base: `http://127.0.0.1:8350` (sin `/v1`)
- Modelo: `qwen3.8-flash-next-iq3_s`
- Contexto declarado: 131072 tokens; una solicitud residente en el servidor
- Autenticación: no requiere API key en loopback
- Runner: `scripts/run-astra-strata.sh`

Para iniciarlo desde la raíz del repo, ejecutar `./scripts/run-astra-strata.sh`;
mantener esa terminal abierta mientras se use ASTRA. El perfil de LlamaCode se
conecta al endpoint y no gestiona el ciclo de vida del proceso Strata. El runner
admite `STRATA_ROOT`, `STRATA_PYTHON`, `STRATA_CONFIG` y `ASTRA_STRATA_PORT` para
instalaciones o puertos alternativos. La comparación LC-H1 completa y los
resultados crudos están en
[`strata-0.1.35-vs-sol-llamacode-lch1-20261002.md`](strata-0.1.35-vs-sol-llamacode-lch1-20261002.md).
