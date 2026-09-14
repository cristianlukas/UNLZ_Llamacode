# Auditoría local de Swift-Qwen3.8-27B

Fecha: 2026-09-14  
Equipo: Ubuntu, 2× RTX 3090 de 24 GiB, driver con P2P, 123 GiB de RAM  
Objetivo: comprobar si el fine-tune Swift mejora el uso de Qwen3.8 en LlamaCode sin superar Q8 en pesos ni KV.

## Candidato

Se descargó el tier `Q4_K_M` y el proyector de visión oficial en:

- `/media/cristian/7CFE1E0FFE1DC1F6/models/Swift-Qwen3.8-27B-GGUF/Swift-Qwen3.8-27B-Q4_K_M.gguf`
- `/media/cristian/7CFE1E0FFE1DC1F6/models/Swift-Qwen3.8-27B-GGUF/mmproj-Swift-Qwen3.8-27B-F16.gguf`

El modelo ocupa aproximadamente 18,0 GB y el proyector 0,93 GB. Se respetó `KV Q8` (`q8_0` para K y V).

La tarjeta del modelo afirma que Swift conserva una calidad similar al Qwen3.8 original reduciendo el razonamiento medio. Esas cifras publicadas corresponden principalmente a BF16/W4A16 y no sustituyen una validación BCB local del GGUF.

## Pruebas locales

| Prueba | Resultado |
| --- | --- |
| Carga con runtime experimental Flash-Next, MTP y P2P | Falla con acceso ilegal CUDA en RMSNorm durante la inicialización |
| Carga con el mismo runtime y `GGML_CUDA_PDL=0` | Falla de igual forma; PDL no era la causa |
| Carga CPU, contexto 2K | Funciona; smoke correcto, 17,7 tok/s de prefill y 2,4 tok/s de decode |
| Carga GPU dual con MMQ, contexto 8K, sin MTP | Funciona; 33,2 tok/s en smoke |
| Carga GPU dual con MMQ, contexto 8K, MTP3 | Funciona y estable |
| MTP3, coding corto | 80,85 tok/s; aceptación 80/84 (95,2%) |
| MTP3, JSON corto | 76,90 tok/s; aceptación 12/12 (100%) |
| MTP3, smoke corto | 42,29 tok/s; aceptación 6/6 (100%) |
| Contexto 131K reservado con MTP3 y KV Q8 | Carga y permanece saludable |
| Prefill largo | 67.243 tokens procesados a 1.129,9 tok/s |
| Decode después del prefill largo | 50,7 tok/s; aceptación 11/11 |
| Contexto 262K con MTP3 | Falla con acceso ilegal CUDA al crear el contexto |
| Contexto 262K sin MTP | Falla con el mismo tipo de acceso ilegal |
| Visión con `mmproj` oficial, 32K | Funciona; descripción correcta, 570,5 tok/s de prefill y 35,7 tok/s de decode |
| Servidor después de visión | `{"status":"ok"}` |

El build que funciona requiere `GGML_CUDA_FORCE_MMQ=1`; no se cambió el build permanente de LlamaCode. La falla a 262K parece pertenecer a la combinación de este GGUF/runtime con la reserva grande de contexto, no al proyector de visión ni a MTP exclusivamente.

## Comparación práctica

| Dimensión | Swift local | SOL actual |
| --- | ---: | ---: |
| Decode corto con MTP | 76,9–80,9 tok/s | 74 narrativo / 102 código, benchmark histórico |
| Prefill largo medido | 1.129,9 tok/s a 67K | No comparable en esta corrida |
| Contexto operativo reproducible | 131K | 262K validado |
| KV | Q8 | FP8 en el backend de SOL; dentro del límite funcional del proyecto |
| Visión | Sí, validada en smoke | No validada |
| BCB | Pendiente | 8/8 |
| Tool-use | No validado con BCB; JSON smoke correcto | Validado |
| Estabilidad | Buena a 131K con MMQ; 262K falla | Principal y estable |

## Decisión

Swift es útil como candidato experimental para coding con razonamiento más eficiente y como alternativa multimodal de Qwen3.8. No es demostrablemente superior a SOL: no tiene BCB local, no alcanza 262K en este setup y sus cifras cortas no son comparables directamente con el benchmark de SOL.

Por eso no reemplaza ni cambia el default SOL. Tampoco se agregó al listado prioritario todavía. Para promoverlo haría falta repetir BCB/HE20 con el mismo harness de LlamaCode y, si se quiere un perfil permanente, resolver la inestabilidad de 262K o fijar explícitamente 131K como techo operativo.

## Configuración reproducible validada

```text
GGML_CUDA_FORCE_MMQ=1
CUDA_VISIBLE_DEVICES=0,1
--ctx-size 131072
--n-gpu-layers 999
--split-mode layer
--tensor-split 1,1
--flash-attn on
--load-mode mmap
--cache-type-k q8_0
--cache-type-v q8_0
--spec-type draft-mtp
--spec-draft-n-max 3
--batch-size 1024
--ubatch-size 256
--temp 0.6 --top-p 0.95 --top-k 20 --min-p 0.0
```

