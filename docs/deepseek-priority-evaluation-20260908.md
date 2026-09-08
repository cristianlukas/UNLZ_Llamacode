# DeepSeek prioritario en Ubuntu — 2026-09-08

## Resultado

Se agregó el perfil Linux prioritario:

- **ID:** `d6b3fc6c-3d49-4835-9487-47dfbb53b48e`
- **Nombre:** `DEEPSEEK · V4 Flash IQ3_S · experimental · 131K`
- **Modelo:** DeepSeek V4 Flash 0731 UD-IQ3_S, cuatro shards del volumen compartido.
- **Backend:** build CUDA Flash-Next registrada en Ubuntu.
- **Reparto:** capas por GPU con expertos en CPU y capas 29–36 de expertos en CUDA1.
- **KV:** Q4 K/V; contexto operativo 131K.
- **Windows:** sin cambios; el ajuste se guarda en `platformArgs.linux`.

## Pruebas locales

| Prueba | Resultado |
|---|---:|
| Carga desde LlamaCode | OK |
| VRAM durante la carga | 47.412 MiB total; GPU0 23.935 MiB, GPU1 23.477 MiB |
| Server Speed v1 | 14,30 tok/s promedio; 14,46 tok/s P50 |
| Prefill | 25,14 tok/s |
| TTFT P50 | 2.398 ms |
| HE0 actual | 0/1; falló después de 2 reparaciones |

Como referencia histórica, la variante DeepSeek IQ3_S anterior completó BCB 8/8 a 9,645 tok/s, pero esa evidencia no se considera una validación actual del nuevo perfil porque cambió la huella de modelo/backend. El perfil queda por eso visible como experimental y no como default.

## Orden prioritario en LANZAR

1. DEEPSEEK — IQ3_S, experimental, 131K
2. ASTRA — Qwen Next, cache experto 188, 196K
3. SOL — Qwen 28B, MTP3, 131K
4. TERRA — Qwen 28B diario, 131K
5. LUNA — ThinkingCap Qwen3.6, MTP4, CUDA, 64K
6. METEOR — BigBang MTP, throughput

TERRA quedó restaurado como servidor activo después de las pruebas.
