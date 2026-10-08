# Auditoría REAP-320 — Qwen3.8 Flash-Next

Fecha: 2026-09-14  
Equipo: Ubuntu, 2× RTX 3090 de 24 GB, P2P activo, 123,5 GiB de RAM  
Runtime: build `qwen4exp` de llama.cpp con `--lazy-mode on-direct`  
Regla de cuantización: pesos y KV como máximo Q8; no se usó BF16/F16 como KV en estas pruebas.

## Qué se evaluó

Se descargó el quant REAP-320 de Qwen3.8 Flash-Next en:

`/media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.8-Flash-Next-REAP320-Q3/`

El modelo Q3 ocupa aproximadamente 68,95 GB y conserva 320 expertos de los 512 originales. También se descargaron, para probar speculative decoding, los sidecars en:

`/media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.8-Flash-Next-MTP/MTP/`

La referencia externa es el [model card de REAP-320](https://huggingface.co/AnonimousA/Qwen3.8-Flash-Next-REAP-320-GGUF). Sus resultados de HumanEval no son una validación de LlamaCode y el propio reporte incluye una sonda con fabricaciones, por lo que se verificaron localmente antes de considerar cualquier promoción.

## Receta local

La receta reproducible usó reparto por capas entre las dos GPU, `--n-cpu-moe 20`, `--load-mode mmap`, `--lazy-mode on-direct`, Flash Attention, batch 2048, ubatch 512, una sesión y KV `q8_0` tanto para K como para V. El muestreo fue el estándar de coding de LlamaCode: temperatura 0,6, top-p 0,95, top-k 20, min-p 0 y repeat penalty 1.

## Resultados

| Prueba | Resultado local | Lectura |
| --- | ---: | --- |
| Carga y health a 32K | OK; ~4,8 s de carga | Arranque reproducible |
| Decodificación corta a 32K | ~32,2 tok/s | Sin MTP; salida coherente |
| Tool-use | OK; tool call JSON válido | Compatible con el parser básico |
| Prefill, 14.416 tokens | 725 tok/s | Contexto medio |
| Prefill, 14.916 tokens | 631 tok/s | Variación normal entre cargas |
| Prefill, 54.016 tokens con límite 64K | 577,25 tok/s | Contexto largo real |
| Prefill, 90.016 tokens con límite 262K | 515,35 tok/s | Confirma procesamiento largo real |
| Límite de contexto 262.144 | Carga y health OK; ~22,9 GB de VRAM en la tarjeta más ocupada | Techo operativo reservado, no implica que se haya llenado a 262K |
| BCB, pasada 1 | 1/8 | Insuficiente frente a SOL 8/8 |
| BCB, pasada 2 | 1/8 | Resultado estable, pero no satisfactorio |

Los ocho casos de BCB se ejecutaron aislados. El único aprobado fue `BigCodeBench/870`; los otros siete fallaron en diferencias de CSV, transferencia de archivos, generación aleatoria, agregación, conversiones de unidades y excepciones esperadas. No es un problema de velocidad: es una señal de calidad agentiva insuficiente para usarlo como perfil principal.

## MTP y sidecars

Se probaron dos sidecars presentes en `models/`:

| Sidecar | Resultado |
| --- | --- |
| `mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf` | No carga: falta `token_embd.weight` |
| `mtp-Qwen3.8-Flash-Next-Q4_K_M.gguf` | No carga: falta `output_hc_norm.weight` |

El modelo principal sí carga y genera. El fallo está en la compatibilidad del loader actual con el formato de sidecar standalone/shared de Qwen3.8 para este modelo REAP; no demuestra que el quant principal esté corrupto. MTP queda bloqueado y no se contabiliza en la velocidad.

## Comparación con la tabla vigente

| Perfil | Calidad / agentes | Velocidad comparable | Contexto | Decisión |
| --- | --- | --- | --- | --- |
| SOL | BCB 8/8; tool-use estable | 74 narrativo / 102 código | 262K validado | Sigue siendo el default |
| ASTRA | BCB no válido | 16–41 tok/s | ~196K | REAP es una alternativa técnica más medible para contexto, pero no una mejora de calidad |
| QWEN38-Q8 | Validación agentiva pendiente | 41,3 a 8K / 22,1 a 262K | 262K validado | REAP es más rápido en corto, pero QWEN38-Q8 conserva mayor fidelidad de pesos |
| REAP-320 Q3 | BCB 1/8 en dos pasadas | ~32,2 tok/s corto; 515–577 tok/s de prefill largo | 262K reservado; 90K probado con prefill real | No promover |

## Conclusión

REAP-320 sí aporta una receta técnicamente útil para hacer funcionar Qwen3.8 Flash-Next con mucha menos VRAM y contexto largo real. No es superador de SOL para LlamaCode: su BCB 1/8, la falta de MTP funcional y la ausencia de visión lo dejan como experimento de infraestructura, no como perfil agentivo.

No se agregó al dropdown ni se cambió ningún default. SOL continúa siendo el perfil principal. El modelo principal REAP-320 se conserva bajo `models/` porque aporta una receta de contexto largo que no es peor en todo. Los dos sidecars MTP incompatibles se eliminaron después de la prueba y liberaron aproximadamente 5,2 GB.

Logs y evidencias:

- `/home/cristian/.cache/llamacode/reap320-q3-32k.log`
- `/home/cristian/.cache/llamacode/reap320-q3-64k.log`
- `/home/cristian/.cache/llamacode/reap320-q3-131k.log`
- `/home/cristian/.cache/llamacode/reap320-q3-262k.log`
- `/home/cristian/.cache/llamacode/reap320-bcb-20260914.json`
- `/home/cristian/.cache/llamacode/reap320-q3-mtp-64k.log` (sidecar Q8 eliminado)
- `/home/cristian/.cache/llamacode/reap320-q3-mtp-q4-64k.log` (sidecar Q4 eliminado)
