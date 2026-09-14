# Auditoría de la receta vLLM Qwen3.8 144K — 2026-09-14

## Objetivo

Evaluar si la receta comunitaria para una RTX 3090 —AutoRound INT4, KV FP8,
144K, `max-num-batched-tokens=1024`, caché de prefijo y sin MTP— aporta una
mejora aplicable al SOL de LlamaCode en esta máquina con dos RTX 3090 y P2P.

La publicación externa mide una sola 3090 en WSL2 y reporta 38,39 tok/s
promedio. Esa cifra no es directamente comparable con el SOL TP2 local.

## Configuración probada

- vLLM `0.27.1` dentro de la imagen local ya disponible.
- Qwen3.8-27B AutoRound INT4 local, sin descargar pesos nuevos.
- TP=2, dos RTX 3090, P2P/NCCL disponible.
- KV FP8 E4M3, FlashInfer, `max-model-len=147456`.
- `max-num-seqs=1`, `max-num-batched-tokens=1024` y
  `long-prefill-token-threshold=1024`.
- Prefix caching, chunked prefill, `mamba-cache-mode=align` y
  `prefix-match-unit=16`.
- Sin MTP/especulación, para aislar la receta del drafter.
- `gpu-memory-utilization=0.90`, porque el valor comunitario `0.9475` no
  reserva en esta máquina: la GPU0 tenía aproximadamente 22,14 GiB libres y
  el objetivo exigía 22,32 GiB.

## Resultados locales

La variante con `0.90` cargó y quedó saludable. vLLM calculó 617.563 tokens de
KV disponibles, con una concurrencia teórica de 4,19 sesiones de 147.456
tokens. El arranque completo tardó aproximadamente 128 s, incluyendo una
compilación AOT/JIT de unos 81 s; los artefactos quedaron en la caché local de
vLLM y no se dejó el contenedor ejecutándose.

| Prueba | Resultado |
| --- | ---: |
| Requests cortos, sin MTP | 53,03 / 52,59 / 51,90 tok/s |
| Prefill observado en request de contexto | ~1.444 tok/s |
| Respuestas HTTP | 3/3, sin error del engine |
| KV pool | 617.563 tokens |
| Contexto configurado | 147.456 tokens |
| Variante `gpu-memory-utilization=0.9475` | No inicia por falta de margen en GPU0 |

Las requests cortas fueron una comprobación de velocidad y salud; no se
presentan como una campaña BCB ni como validación de tool-use. El endpoint
expuso correctamente el razonamiento separado de la respuesta.

## Comparación contra SOL

| Variante | Narrativo | Código | Prefill | Calidad / estabilidad |
| --- | ---: | ---: | ---: | --- |
| Receta 144K, TP2, sin MTP | ~52 tok/s | No medido con BCB | ~1.444 tok/s observado | Smoke estable; no BCB |
| SOL TP2/P2P, sin MTP | 50,11 tok/s | 49,91 tok/s | 2.355 tok/s @10K; 1.543 @90K | Estable |
| **SOL TP2/P2P, MTP4** | **74,03 tok/s** | **102,36 tok/s** | 2.287 tok/s @10K; 1.500 @90K | **BCB 8/8, tool-use OK** |

La diferencia entre la receta 144K y el SOL sin MTP no es concluyente a favor
de la receta: usan distinta ventana, distinta forma de medir y una sola
mini-campaña. Sí es concluyente para la decisión operativa: la receta no supera
al SOL promovido y elimina la aceleración MTP4.

## Decisión para LlamaCode

- No reemplazar SOL ni modificar su backend.
- No agregar otro perfil duplicado de Qwen3.8.
- Mantener `max-num-batched-tokens=8192` y MTP4 en SOL, que ya están validados
  con BCB 8/8 y tool-use.
- Conservar como idea reutilizable el control de margen de VRAM: `0.9475` es
  demasiado agresivo para esta GPU0; `0.90` es el margen seguro observado.
- Prefix caching, chunked prefill y `mamba-cache-mode=align` ya están presentes
  en el compose actual de SOL; no faltaba implementar esa parte.
- El modo 144K podría servir como perfil diagnóstico de baja concurrencia, pero
  no aporta suficiente beneficio para entrar al dropdown prioritario.

No se descargaron modelos, no se dejaron servicios persistentes y no se
modificó el default de LlamaCode.
