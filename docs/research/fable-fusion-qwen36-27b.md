# Fable Fusion Qwen3.6-27B Q6 MTP frente a ThinkingCap

Fecha: 2026-08-08. Hardware: 2x RTX 3090 24 GB, Ryzen 7 7700, Windows.

## Veredicto

Fable Fusion Q6 MTP queda integrado como perfil experimental opt-in del tier
48 GB. En una batería textual de instrucciones estrictas obtuvo 26/30 (86,7%)
frente a 12/30 (40%) de ThinkingCap Q4 MTP3 y terminó cada tarea en una mediana
de 2,41 s frente a 6,67 s. No reemplaza todavía al perfil operativo: falta repetir
la suite agentica E2E con archivos, tools y tests reales.

## Compatibilidad

- Modelo MTP: `Qwen3.6-27B-Fable-Fus-711-UnHeretic-NM-DAU-NEO-MAX-NEO-MTP-Q6_K.gguf`
  (24.033.705.440 bytes).
- Modelo regular de control: `...NEO-Q6_K.gguf` (23.582.384.672 bytes).
- Visión: `mmproj-F16.gguf` (927.607.360 bytes).
- llama.cpp b10228 genera salida corrupta con ambos GGUF, incluso sin MTP.
- llama.cpp b10331 corrige la salida; el perfil exige esa build como mínimo.
- `split-mode=tensor` dispara una aserción en b10228. El perfil usa `layer` y
  `tensor-split 1,1`.

## Calidad textual reproducible

Runner: `tools/benchmark_fable_vs_thinkingcap.ps1`, diez tareas de matemática,
lógica, parsing, formato y código, tres pasadas, mismo sampling conservador,
32k de contexto, K=f16/V=q8, MTP3 y reasoning off.

| Perfil | Score | Decode mediano | Tiempo mediano/tarea |
|---|---:|---:|---:|
| ThinkingCap Q4 MTP3 | 12/30 | 54,50 t/s | 6,67 s |
| Fable Fusion Q6 MTP3 | **26/30** | 44,23 t/s | **2,41 s** |

Fable decodifica menos tokens por segundo, pero obedece mejor el formato y usa
menos tokens. ThinkingCap agotó con frecuencia el límite de 512 tokens antes de
emitir la respuesta final. Los dos fallaron de forma consistente el caso ambiguo
`a=b=c` y una salida JSON extremadamente estricta.

Artefacto completo:
`D:/Models/llamacpp/Qwen3.6-27B-Fable-Fusion-Q6/quality-3passes-b10331-instruct.json`.

## Barrido de inferencia

Mismo prompt corto, tres repeticiones por punto:

| Configuración | TPS observados |
|---|---:|
| MTP2, K=f16/V=q8 | 47,48–50,74 |
| MTP3, K=f16/V=q8 | 52,76–58,96 |
| MTP4, K=f16/V=q8 | **58,05–61,23** |
| MTP4, K=q8/V=q8 | 63,48–65,59 |

El perfil adopta MTP4. Aunque K=q8 fue aproximadamente 7% más rápido, K=f16 se
mantiene como default porque cuantizar K puede degradar coherencia a contexto
largo; q8/q8 queda disponible como variante de benchmark.

## Smoke final a 120k con visión

La configuración integrada cargó en b10331 con MTP4, `mmproj-F16`, K=f16/V=q8,
batch 2048, ubatch 512 y un slot efectivo de 120.064 tokens. Respondió
`FINAL: ready` correctamente. El uso observado fue 16.087 MiB en CUDA0 y
17.321 MiB en CUDA1, sin spill a RAM ni presión de VRAM.

## Pendiente antes de promover

1. Ejecutar `Agent efficiency E2E v1` x3 contra ThinkingCap con archivos y tests.
2. Medir calidad con prompts realmente largos cerca de 120k; carga y generación
   corta ya quedaron validadas.
3. Agregar un set de visión con imágenes y respuestas verificables.
