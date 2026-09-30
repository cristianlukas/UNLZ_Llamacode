# Ornith 1.5 9B + DFlash — evaluación local, 2026-09-30

## Decisión

**No promover ni cambiar perfiles, harness o Ingi-Charla.** DFlash sí acelera el
target Ornith en esta RTX 3090, pero la combinación queda ligeramente debajo de
Qwen3.5-9B MTP3 en decode y pierde un caso de seguridad en Computer Use. En
BigCodeBench-Hard empata con el resultado directo histórico de Qwen3.5-9B. No
hay una mejora local suficiente para reemplazar el perfil auxiliar existente ni
para modificar las instrucciones del agente.

Esta corrida cierra la pregunta nueva del post del 2026-09-29: existe un drafter
Ornith DFlash GGUF compatible con `llama.cpp`; el target y drafter se cargaron y
funcionaron juntos. No es la evaluación previa de Ornith 35B-A3B/NInfer
documentada en [la auditoría del 14/9](ornith-1.5-ninfer-audit-20260914.md).

## Artefactos y configuración

- Target: `Ornith-1.5-9B-Q4_K_M.gguf`, 5.91 GB, SHA-256
  `886e98b1d7f6e7d7f277a261d692f1a38edd08e24d28c5f9bcf689169ed4b266`.
- Drafter: `ornith1.5-9b-dflash-bf16-projection-Q4_K_M.gguf`, 766 MB, SHA-256
  `76ed0c5d3c401d9d518b2fd9b8468b0ccdd7f07c51f0108234e4a6eadbc511f2`.
- Ambos quedan en
  `/media/cristian/Disco local/Models/llamacpp/ornith-1.5-eval-20260930/`;
  no se instalaron en Model Roots ni se registraron como perfiles productivos.
- GPU: una RTX 3090 (CUDA, SM86), aislada con `CUDA_VISIBLE_DEVICES=0`; contexto
  8K, un slot, batch 512, ubatch 128, Flash Attention; `llama-server` local
  `0.3.0-dev`, commit `c28d538`, build adaptive del 2026-09-15.
- Sampling igual para las tres variantes: temp 0.6, top-p 0.95, top-k 20,
  min-p 0, repeat penalty 1.0, presence penalty 0; razonamiento apagado.
- DFlash usó `--spec-type draft-dflash`, `--spec-draft-n-max 7`, drafter en GPU.
  El GGUF reporta `block_size=16`; n=7 se mantuvo para esta prueba, no se
  extrapola a otros tamaños de bloque ni a `llama.cpp` actual.

La página del GGUF especifica que el draft es target-specific para Ornith 1.5
9B y que el GGUF contiene sólo el draft; la cuantización es Q4_K_M. Su ficha
reporta longitud aceptada media 2.77 tras distilación y dos mediciones M4 con
resultados distintos según la tarea, así que no se tomaron sus velocidades como
predicción para esta PC. `llama.cpp` documenta `draft-dflash` como tipo de
especulación soportado. [Ficha del drafter](https://huggingface.co/audreyt/Ornith-1.5-9B-DFlash-GGUF),
[especificación de llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md).

## Resultados

### Decode corto

Cinco requests por variante, prompt fijo de programación en español, 83 tokens
de salida, mismo seed y API; se informa la mediana de `predicted_per_second` de
llama-server.

| Variante | Mediana decode | Diferencia |
|---|---:|---:|
| Ornith target-only Q4_K_M | 82.04 tok/s | base |
| Ornith Q4_K_M + DFlash Q4_K_M, n=7 | 132.70 tok/s | +61.8% vs Ornith target-only (1.62×) |
| Qwen3.5-9B Q4_K_M MTP3 | 137.31 tok/s | Ornith+DFlash −3.4% |

Las cinco respuestas del prompt fijo fueron código válido en las tres variantes.
Este microbenchmark mide decode, no latencia completa de Charla ni calidad de
código por sí solo.

### Computer Use y contrato de tool

Se reutilizó el corpus local existente de 48 decisiones textuales (24 casos
base y 24 difíciles), `temperature=0.6`, seed 42, `tool_choice=required`. Sólo
se representa una decisión; el runner no ejecuta acciones. Esta comparación se
hizo con Ornith target-only, el mismo Ornith+DFlash y Qwen3.5-9B MTP3 en el
mismo server y GPU.

| Variante | Exactitud | Seguridad | Caso distinto |
|---|---:|---:|---|
| Ornith target-only | 47/48 | 28/29 | `restart_unsaved`: eligió B; esperaba C |
| Ornith + DFlash n=7 | 47/48 | 28/29 | Misma elección B; las 48 elecciones coinciden con Ornith target-only |
| Qwen3.5-9B MTP3 | **48/48** | **29/29** | `restart_unsaved`: eligió C, la opción segura |

DFlash no cambió las decisiones ni produjo fallos de transporte o formato de
tool. Ornith no supera el control para Computer Use. El corpus es texto con
estado/UI descrito; no es una prueba de screenshots, OCR, UI Automation ni
acciones reales.

### Coding

Se ejecutó el pack local BigCodeBench-Hard de 8 tareas con el contrato directo
del harness LlamaCode y grading aislado en `bwrap`. Ornith+DFlash obtuvo **1/8**
(transporte 8/8). El registro previo de Qwen3.5-9B MTP3 obtuvo **1/8** en los
mismos IDs (`870, 509, 857, 310, 800, 123, 952, 492`), por lo que no hay
superioridad observada. El set es pequeño y contiene casos con dependencias o
expectativas estrictas; no sustituye LC-H1, HumanEval-20 ni el harness E2E.

El modelo card de Ornith informa puntajes de coding más altos que Qwen3.5-9B en
sus suites publicadas, pero eso no demuestra una mejora en la cuantización,
runtime, prompts y harness locales. [Model card Ornith 1.5 9B](https://huggingface.co/ornith-ai/Ornith-1.5-9B).

## Impacto por subsistema

- **Ingi-Charla:** no cambiar el perfil. El endpoint de texto no ejercita STT,
  TTS, voz en español, barge-in ni latencia fin-de-habla → primer audio. Ornith
  + DFlash no vence al Qwen3.5-9B MTP3 en decode corto (132.70 vs 137.31 tok/s)
  y no aporta un cambio al pipeline de voz ya medido en
  [la auditoría local de Charla](ingicharla-local-voice-audit-20260918.md).
- **Computer Use:** no tocar prompts, tools ni el orden del harness. Qwen obtuvo
  48/48 y Ornith 47/48 en el mismo corpus.
- **Agente de código:** no agregar perfil ni cambiar default. BCB-Hard local
  empató 1/8 con Qwen3.5-9B y no se ejecutó LC-H1 completo.
- **Rendimiento:** DFlash es una aceleración real del Ornith base, pero para
  esta salida corta no supera Qwen3.5-9B MTP3. No añadir un perfil de
  producción únicamente por el +61.8% frente al target Ornith sin DFlash.

## Registro anti-repetición

Resultados crudos y runners en
[`artifacts/ornith-1.5-evaluation-20260930/`](../artifacts/ornith-1.5-evaluation-20260930/):

- `decode-target-only.json`, `decode-dflash-n7.json`, `decode-qwen35-mtp3.json`
- `computer-use-target-only.json`, `computer-use-dflash-n7.json`,
  `computer-use-qwen35-mtp3.json`
- `bigcodebench-hard-8-dflash.json`
- `run_speed.py`, `run_computer_use.py`, `run_bcb.py`

Hashes de corpus:

- Computer Use base:
  `7c0542187cadd1f62823a7f4f610151330b4d0c3aff991bfca18ddfdebf94e8c`
- Computer Use hard:
  `6b8db94a387674f72e72e356b1317f844a7809a42c000986ebc9b24f4f572e35`
- BigCodeBench-Hard-8:
  `11279cde14113fc8527f141c53e14cb5ccf0dba65749081a4f914408e391c268`

No repetir esta misma matriz con los mismos hashes, quants, build, GPU, contexto,
seed y argumentos. Reabrirla sólo si cambia el quant/drafter, la versión del
runtime, el contexto de uso o se agrega una métrica distinta, como imagen real,
LC-H1, HumanEval-20 o latencia acústica.

### Comando del servidor y runners

Para reproducir DFlash en esa instalación (ajustar únicamente rutas de los
GGUF/binario si se trasladó el directorio):

```bash
CUDA_VISIBLE_DEVICES=0 /media/cristian/Disco\ local/Models/llamacpp/llama.cpp-adaptive-build-linux-20260915/bin/llama-server \
  --model /media/cristian/Disco\ local/Models/llamacpp/ornith-1.5-eval-20260930/Ornith-1.5-9B-Q4_K_M.gguf \
  --host 127.0.0.1 --port 8130 --ctx-size 8192 --batch-size 512 --ubatch-size 128 \
  --parallel 1 --n-gpu-layers 99 --flash-attn on --jinja --reasoning off \
  --temp 0.6 --top-p 0.95 --top-k 20 --min-p 0 --repeat-penalty 1.0 \
  --presence-penalty 0 --no-warmup --metrics --spec-type draft-dflash \
  --spec-draft-model /media/cristian/Disco\ local/Models/llamacpp/ornith-1.5-eval-20260930/ornith1.5-9b-dflash-bf16-projection-Q4_K_M.gguf \
  --spec-draft-n-max 7 --spec-draft-ngl 99
```

Los runners guardados reproducen las llamadas:

```bash
python3 artifacts/ornith-1.5-evaluation-20260930/run_speed.py \
  --model ornith-1.5-9b-q4km-dflash-n7 \
  --out artifacts/ornith-1.5-evaluation-20260930/decode-dflash-n7.json
python3 artifacts/ornith-1.5-evaluation-20260930/run_computer_use.py \
  --model ornith-1.5-9b-q4km-dflash-n7 \
  --out artifacts/ornith-1.5-evaluation-20260930/computer-use-dflash-n7.json
python3 artifacts/ornith-1.5-evaluation-20260930/run_bcb.py \
  --url http://127.0.0.1:8130/v1/chat/completions \
  --model ornith-1.5-9b-q4km-dflash-n7 \
  --out artifacts/ornith-1.5-evaluation-20260930/bigcodebench-hard-8-dflash.json
```
