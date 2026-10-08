# Qwen3.8 BeeLlama KVarN5/KVarN4 — auditoría del post de 50 tok/s

Fecha: 2026-09-14  
Equipo: Ubuntu, 2× RTX 3090, P2P disponible  
Modelo: `Qwen3.8-27B-UD-Q4_K_XL.gguf`  
Runtime: BeeLlama preview v0.4.7, `--split-mode layer`, `--tensor-split 1,1`

## Qué parte del post es aplicable

El post propone tres ideas: KVarN asimétrico (`KVarN5` para K y `KVarN4` para V), una cola de tokens exactos (`--kv-tail-tokens 1024`) y MTP2. La primera se puede probar con nuestro backend y respeta la política de LlamaCode si la cola queda en cero. La cola propuesta no se promovió: BeeLlama sólo permite que esa cola sea F16 o BF16, por encima del máximo KV Q8 fijado para la aplicación.

El resultado externo de 47–50 tok/s no es directamente comparable: usa otra GPU, otro tamaño de VRAM, otra build y un quant distinto. No incluye BCB ni una validación equivalente de tool-use.

## Pruebas locales

Todas las corridas usaron el mismo GGUF, las dos RTX 3090, P2P, batch 512/ubatch 256, contexto sin desplazamiento, muestreo determinista para la comparación y `--kv-tail-tokens 0`.

| Configuración | Contexto | Prefill | Decode | Resultado |
|---|---:|---:|---:|---|
| KVarN5/KVarN5, control previo | 8K | 543,83 tok/s | 36,81 tok/s | Baseline local |
| KVarN5/KVarN4, candidato | 8K | 436,66 tok/s | 36,22 tok/s | Carga y responde; prefill −19,7% |
| KVarN5/KVarN5, control previo | 131K | 511,9 tok/s | 35,99 tok/s | Baseline local |
| KVarN5/KVarN4, candidato | 131K | 443,86 tok/s | 36,58 tok/s | Carga y responde; prefill −13,3% |

La solicitud de código devolvió Python válido en ambas corridas. La prueba de herramientas del candidato devolvió `finish_reason=tool_calls` con:

```json
{"name":"read_file","arguments":"{\"path\":\"/tmp/example.py\"}"}
```

No hubo `assert`, corrupción de salida ni fallo de carga. Esto confirma compatibilidad, pero no una ventaja de calidad. BCB completo y visión siguen pendientes para la familia BeeLlama; el control KVarN5/KVarN5 ya tiene smoke 4/4, JSON, Python, tool-call y needle largo validados.

## Decisión para LlamaCode

- No reemplazar SOL: SOL sigue en 74 tok/s narrativo / 102 tok/s código y BCB 8/8.
- Mantener el perfil experimental BeeLlama KVarN5/KVarN5, que es el mejor equilibrio medido para este backend: aproximadamente 36 tok/s de decode a 131K, sin KV superior a Q8.
- Agregar KVarN5/KVarN4 sólo como variante de benchmark, porque es estable pero más lento en prefill y no aporta calidad demostrada.
- No implementar `--kv-tail-tokens 1024` como perfil: su tipo exacto F16/BF16 viola el límite de KV Q8. Tampoco promover MTP2 del post sin un drafter/artifacto local y una prueba de aceptación estable.

## Artefactos y entorno

La prueba usó el modelo ya existente en `/media/cristian/Disco local/Models/llamacpp/Qwen3.8-27B-GGUF/` y el binario BeeLlama fuera del repositorio en `/home/cristian/.cache/llamacode/beellama-bin-v047-20260913/`. No se descargaron modelos ni se movió ningún archivo.

