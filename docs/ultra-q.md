# ULTRA-Q · DeepSeek V4 Flash 0731

Perfil experimental para una RTX 3090 de 24 GB, Ryzen 9900X y 128 GB DDR5. No
reemplaza a MAX-Q hasta superar los benchmarks locales.

## Instalación

El perfil `sys-ultraq-dsv4-0731-iq3s` descarga manualmente los cuatro shards
`UD-IQ3_S` desde `unsloth/DeepSeek-V4-Flash-0731-GGUF`. Se recomiendan al menos
150 GB libres. Las descargas usan la cola reanudable existente y el perfil no es
companion de ningún showcase.

Requiere llama.cpp oficial b10217 o posterior. LlamaCode compara el número de
build, elige el binario compatible más nuevo y conserva instaladas las builds que
usan otros perfiles.

## Configuración inicial

```text
ctx 131072 · gpuLayers 44 · batch 1024 · ubatch 512
KV q4_0 · flash-attn · no-mmap · parallel 1
--n-cpu-moe 39 · temp 1.0 · top-p 0.95
```

Los contextos permitidos para crear variantes son 64k, 131k, 192k, 256k y 384k.
384k es experimental: debe verificarse contra RAM comprometida, pagefile, VRAM y
tiempo de prefill. El tuner incluye `--n-cpu-moe 31/35/39/43` y conserva el gate
de calidad/perplexity existente.

## Híbrido ULTRA-Q → MAX-Q

El perfil `sys-hybrid-ultraq-maxq` usa ULTRA-Q sólo para planificar y MAX-Q para
editar, ejecutar tools y verificar. El flujo es secuencial porque ambos modelos
comparten GPU:

1. Construye contexto de sólo lectura con AGENTS/README, árbol acotado y Git.
2. Detiene MAX-Q y carga ULTRA-Q.
3. Exige y valida `HybridPlan v1` JSON.
4. Guarda el plan bajo `AppLocalData/LlamaCode/hybrid-plans/<sha256>.json`.
5. Descarga ULTRA-Q, restaura MAX-Q y entrega request + plan internamente.

El transcript conserva sólo el request original. Planes vacíos, inválidos o con
schema incorrecto cancelan la ejecución. Un journal en QSettings permite volver a
seleccionar el ejecutor después de un cierre durante el hot-swap. La revisión
final con ULTRA-Q no es automática porque exigiría otro intercambio de ~116 GB.

## Validación

Antes de promover ULTRA-Q ejecutar, con tres pasadas como mínimo:

- `Agent efficiency E2E v1`;
- `Stress largo y difícil`;
- casos de tool calling encadenado;
- A/B MAX-Q, ULTRA-Q y el híbrido;
- soak de cargas, cancelaciones y reinicios.

Registrar calidad final/al primer intento, reparaciones, tokens de thinking,
TTFT, tok/s, tiempo de carga, RAM/VRAM pico, pagefile y tiempo total. Las suites
requieren que los cuatro shards y el runtime compatible estén instalados; no se
publican resultados simulados cuando esos artefactos no están presentes.
