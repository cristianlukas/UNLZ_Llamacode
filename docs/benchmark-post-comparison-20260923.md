# Campaña comparativa del post Qwen/NInfer — 2026-09-23

## Objetivo

Evaluar si las ideas del post aportan una mejora real a LlamaCode en cuatro
superficies: INGI-CHARLA, Computer Use, harness y runtime/modelo.

La campaña queda implementada en
[`tools/post_comparison.py`](../tools/post_comparison.py). El analizador usa
pares por identificador, conserva corridas incompletas como `inconclusive` y no
convierte un crash, timeout o falta de artefacto en un cero de calidad.

## Plan congelado

| Track | Baseline | Candidata | Métricas | Gate de promoción |
|---|---|---|---|---|
| Harness/prefijo | stable-turn + wire actual | rolling-tool o equivalente | avances, plateaus, regresiones, sufijo no cacheado, TTFT | cero regresiones y mejora de sufijo/TTFT |
| Contexto/runtime | perfil validado actual | receta Q4/KV/MTP/visión comparable | startup, PP, TG, TTFT, VRAM pico, aceptación MTP | TG +5%, memoria ≤+5%, sin pérdida funcional |
| Visión | imagen nueva | historial cacheado + imagen nueva | exactitud, media fresca cobrada, TTFT, VRAM | misma exactitud y menor coste/TTFT |
| Calidad agente | HE0 → HE20 → BCB8 actual | misma suite y mismo harness | primer intento, reparaciones, tools, calidad, tiempo | calidad no menor y mejora de velocidad |

La campaña de modelo debe ejecutarse serialmente en 8K, 32K, 64K y 131K, con
KV permitido por el hardware, MTP constante y visión separada del control de
texto. Un contexto configurado no se considera capacidad KV física hasta que
el servidor y el probe lo confirman.

El criterio numérico por defecto del analizador es:

- velocidad de decode: al menos +5% sobre la mediana baseline;
- calidad: ninguna pérdida en la misma suite;
- VRAM: no más de +5%;
- rolling-tool: checkpoints monótonamente crecientes, sin regresiones y con
  sufijo no cacheado menor.

## Implementación

- `tools/post_comparison.py`: contrato de resultados, resumen de secuencias de
  checkpoints, comparación pareada y decisión `promote/reject/inconclusive`.
- `tests/test_post_comparison.py`: ocho regresiones para avances, plateaus,
  regresiones, emparejamiento, gates de calidad/memoria y plan completo.
- No se modificaron perfiles, modelos, defaults ni el ejecutor de Computer Use.

## Resultados ejecutables en este checkout

### Analizador y regresiones nuevas

Ejecutado:

```bash
python3 -m unittest tests/test_post_comparison.py
python3 tools/post_comparison.py --plan
```

Resultado: **8/8 PASS**. La suite Python completa del repositorio ejecutó
**40/40 PASS** incluyendo esta campaña. El plan generado contiene los cuatro tracks y el
analizador reproduce correctamente la secuencia de checkpoints publicada:

```text
19023 → 21146 → 24664 → 26641
avances=3, plateaus=0, regresiones=0
```

### Corrida real Qwen3.8 IQ4_XS

Se ejecutó `llama-server` en serie sobre la GPU 1 con el GGUF local, KV Q8,
`parallel=1`, Flash Attention y sampling conservador. El recibo crudo está en
[`artifacts/post-comparison-20260923/qwen38-iq4xs-results.json`](../artifacts/post-comparison-20260923/qwen38-iq4xs-results.json).

| Variante | Contexto | Exactitud NIAH | PP | TG | Latencia | VRAM |
|---|---:|---:|---:|---:|---:|---:|
| Baseline sin MTP | 8K | 1/1 | 886,0 | 25,5 | 6,26 s | — |
| MTP3 | 8K | 1/1 | 1.233,1 | 67,8 | 4,32 s | — |
| Baseline sin MTP | 32K | 1/1 | 1.042,5 | 37,7 | 19,85 s | 19.265 MiB |
| MTP3 | 32K | 1/1 | 1.181,7 | 70,0 | 17,65 s | 20.187 MiB |
| MTP3 | 131K | 1/1 | 846,8 | 51,9 | 95,43 s | 23.403 MiB |

En 32K, MTP3 mejora TG **+85,7%**, PP **+13,3%** y reduce latencia **−11,1%**;
la VRAM sube **+4,8%**, por debajo del gate de +5%. El analizador clasifica
esta comparación como **promote para el perfil MTP3 de 32K**, no como promoción
automática del post completo.

En 131K, la recuperación sigue siendo exacta y la receta carga, pero quedan
sólo **724 MiB libres** antes de visión; por eso no se considera una configuración
diaria segura.

Visión a 131K con `mmproj` en GPU falló al reservar **887,99 MiB**. Repitiendo
con `--no-mmproj-offload`, el servidor cargó con 648 MiB libres y reconoció una
imagen rojo/azul correctamente, con 100% de aceptación MTP en ese request. Esto
valida la idea de host-map/offload del proyector, pero no demuestra margen para
video, múltiples imágenes ni concurrencia.

### Evidencia local reutilizable

| Track | Resultado local | Veredicto |
|---|---|---|
| INGI-CHARLA | `TestVoice` 41/41; Qwen3.5-9B 106,1 → 166,1 tok/s con MTP; contexto 32K | Mantener, no importar 128K/visión extrema |
| Computer Use | UIA/OCR/snapshots/receipts/aprobación ya validados; OpenSourceJev 16/16 aislado, sin modelo Qwen real | No agregar modelo; sidecar finito sólo como experimento futuro |
| Harness/prefix cache | 17.776 tokens reutilizados; TTFT ~10,1 s → ~1,2 s; schemas canonicalizados | Mejora ya incorporada; rolling-tool real pendiente de servidor compatible |
| Modelo NInfer Qwen3.8 | 50,1 tok/s a 80K, 62,9 a 120K, BCB 3/8 | No reemplaza SOL |
| Modelo SOL | BCB 8/8, tool-use estable, contexto largo y visión validados | Sigue siendo baseline |

Fuentes: [Charla](ingicharla-local-voice-audit-20260918.md), [Computer
Use](opensourcejev-computer-use-audit-20260921.md), [prefix
cache](vllm-prefix-cache-mcp-audit-20260918.md), [NInfer
Qwen3.8](ninfer-3090-linux-evaluation-20260908.md) y [campaña de
harness](harness-quality-campaign-20260915.md).

## Bloqueos de la corrida de modelos

No se ejecutó NInfer/vLLM ni una comparación específica del flag propietario
`rolling-tool`: esos runtimes no son necesarios para el smoke llama.cpp y no
están activos en el checkout. La prueba de modelo sí usó el `llama-server` y
GGUF reales disponibles localmente.

El CTest C++ preexistente no pudo ejecutarse desde este entorno Linux: los
builds disponibles son multi-config Windows y sus registros apuntan a rutas
`C:/Users/...`; no se modificó C++/QML/core en esta campaña.

### Verificación adicional de esta revisión

Se repitieron los controles que no requieren levantar otro servidor:

```text
python3 -m unittest tests/test_post_comparison.py       8/8 PASS
python3 -m unittest tests/test_compaction_quality_matrix.py  2/2 PASS
python3 tools/post_comparison.py --plan                OK; 4 tracks
nvidia-smi topo -m                                     GPU0↔GPU1 = PHB
```

También se intentó `timeout 240 ./scripts/tests-linux.sh Release`. El script
detectó correctamente el checkout NTFS y comenzó la configuración CMake en la
caché nativa, pero quedó bloqueado en estado de I/O mientras había otra
configuración sobre el mismo directorio de tests. Terminó por timeout, sin
emitir un fallo de compilación ni llegar a CTest; por eso no se presenta como
un resultado de calidad. Los tests Python focalizados son el resultado
reproducible de esta revisión.

La documentación upstream de llama.cpp mantiene la misma cautela: `tensor`
usa NCCL automáticamente cuando está compilado y es experimental, mientras
`layer` es el reparto por capas por defecto. La guía también advierte que el
tensor split no está implementado para varias arquitecturas MoE/híbridas. Esto
coincide con nuestra auditoría local: el A/B dual de 3090 no mostró una mejora
reproducible con NCCL/P2P y tensor split no fue estable. Ver
[`multi-gpu.md`](https://github.com/ggml-org/llama.cpp/blob/master/docs/multi-gpu.md)
y el [issue de cuelgue con MTP + tensor split en contexto largo](https://github.com/ggml-org/llama.cpp/issues/28252)
antes de reabrir esa variante.

## Conclusión

La campaña sí encuentra una mejora concreta: **MTP3 en el Qwen3.8 IQ4_XS local
es útil a 32K**, manteniendo NIAH 2/2 y dentro del presupuesto de VRAM. También
confirma que 131K solo es viable con margen mínimo y que visión requiere
proyector en host/RAM para no caer en OOM. No se promueve 131K+visión como
default. `rolling-tool` sigue siendo la hipótesis abierta del harness y falta
probarla con el runtime que implemente ese checkpointing.
