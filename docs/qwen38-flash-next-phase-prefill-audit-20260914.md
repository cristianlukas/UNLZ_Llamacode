# Qwen3.8-Flash-Next: auditoría de `phase-prefill` — 2026-09-14

## Alcance

Se evaluó la propuesta de liberar temporalmente la caché de expertos durante
el prefill y restaurarla antes del decode. La implementación externa está en
la rama `flashnext-e06` de `Inovello/llama.cpp`, commit `d7bca64`.

El objetivo era comparar el runner experimental contra el ASTRA actual con el
mismo GGUF `UD-Q4_K_XL`, dos RTX 3090, expertos residentes en host y KV F16.
El modelo existente ocupa aproximadamente 104 GB y está en la partición
secundaria; no se duplicó en `models` porque la partición de modelos no tiene
espacio suficiente.

## Compilación

La rama externa compiló correctamente como runner aislado:

- CUDA 12.0, `CMAKE_CUDA_ARCHITECTURES=86`.
- NCCL detectado.
- `llama-server` generado en la caché de pruebas, sin reemplazar el runtime
  de LlamaCode.
- Las variables `LLAMA_PHASE_PREFILL_UBATCH`,
  `LLAMA_PHASE_PREFILL_MODE` y `LLAMA_PHASE_PREFILL_MIN_TOKENS` están presentes
  en el binario.
- El runtime actual de LlamaCode no contiene esas variables ni ese código.

## Configuración de control

Se intentó reproducir la receta funcional de ASTRA:

```text
--n-gpu-layers 999 --cont-batching --load-mode mmap
--flash-attn on --parallel 1 --batch-size 512 --ubatch-size 512
--threads 16 --threads-batch 44 --cache-type-k f16 --cache-type-v f16
--override-tensor ffn_(gate|up|down)_exps.weight=CUDA_Host,per_layer_token_embd.weight=CPU
--moe-expert-cache 188 --moe-expert-cache-inserts 2 --numa distribute
```

También se probó la variante del post con caché 150 y la activación de
`LLAMA_ATTN_ROT_DISABLE=1`.

## Resultados reproducibles

| Prueba | Resultado |
|---|---|
| Compilación `flashnext-e06` | OK |
| Carga con caché 150 + rotación desactivada | Carga, pero aborta al primer prefill con `CUDA error: an illegal memory access` |
| Carga con caché 188, receta ASTRA, sin rotación forzada | Carga correctamente |
| Smoke de 59 tokens con caché 188 | Salida corrupta: `////////` |
| Smoke de 17 tokens con `reasoning_effort=none` | Salida corrupta: `////////////////` |
| Medición phase-prefill A/B | No válida: el control del mismo runner no supera el smoke funcional |

El control con caché 188 llegó a ocupar aproximadamente 19 GiB y 16 GiB de
VRAM en las dos placas y quedó escuchando en HTTP. El fallo posterior ocurrió
en generación, no por falta de memoria.

## Comparación con perfiles actuales

Los números publicados para `phase-prefill` —aproximadamente 2,2–2,5× más
prefill y decode casi sin cambios— no se pueden trasladar a LlamaCode: son de
otra rama, otra receta exacta y un runner que en nuestra máquina no conserva
una salida mínima correcta. Además, la optimización sólo atacaría TTFT/prefill;
no corrige la falta de calidad agente de ASTRA.

ASTRA ya tiene estas limitaciones registradas:

- calidad BCB/HE0 no válida o diagnóstica;
- corrupción de prefill en configuraciones Flash-Next experimentales;
- MTP con caché de expertos no estable;
- SOL sigue siendo el perfil de coding validado con BCB 8/8 y tool-use estable.

## Decisión

No se implementa `phase-prefill` en LlamaCode ni se reemplaza el binario de
ASTRA. Tampoco se cambia SOL, TERRA, LUNA ni los demás perfiles. La rama queda
como artefacto de investigación externo, no como default ni como candidato
prioritario.

Para reconsiderarlo hacen falta, como mínimo, un control funcional en el mismo
runner, una corrida phase-prefill apareada a 8K/32K, validación de salida sin
corrupción y una prueba de tool-use. El parche no modifica los límites de
cuantización: KV y pesos seguirían dentro de Q8 como exige LlamaCode.
