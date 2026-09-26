# Auditoría local: Liquid LFM2.5-VL-3B-DSpark — 2026-09-26

## Dictamen

- **Sí aporta a perfiles/modelos si el objetivo es decodificar más rápido el mismo LFM2.5-VL-3B.** En dos solicitudes visuales de lectura/descripción, se observaron aceleraciones de decode de 2,30–2,35× con `n=8` y de 2,26–3,33× con `n=9`, medidas frente al mismo target sin draft en una RTX 3090.
- **No mejora el Computer Use medido.** Con el schema verdadero de `desktop_click`, control, `n=8` y `n=9` produjeron tool-calls válidas, pero las tres apuntaron a `(x=0.5, y=0.5)`, el centro de la pantalla y no el switch en `(≈0.88, ≈0.296)`. No se ejecutaron acciones. El decode subió, pero la mediana end-to-end fue 895 ms control, 987 ms `n=8` y 890 ms `n=9`.
- **No cambié el harness.** El parser de tools funcionó; el error que vimos está en el grounding del modelo. El harness existente prioriza controles semánticos UIA y evidencia, así que una fixture sintética no justifica alterar el motor general.
- **No aplica a Ingi-Charla ni a coding.** Es un drafter entrenado para el target VLM LFM2.5-VL-3B; aquí no evaluamos voz STT/TTS, ingeniería de software ni tareas de agente. No sustituye ningún modelo de Charla.
- Los tres perfiles quedaron **manual-only**, no favoritos y no “best”. `DSpark n=8` y `n=9` se marcan **SUPERIOR sólo en decode / INFERIOR para Computer Use**; el control queda como baseline.

## Fuentes del lanzamiento

- [Anuncio de Liquid AI sobre LFM2.5-VL-3B-DSpark](https://www.liquid.ai/blog/lfm2-5-vl-dspark): drafter específico, bloques especulativos de 8/9 y resultados publicados; la latencia de prefill/imagen limita el speedup end-to-end.
- [Ficha oficial del target LFM2.5-VL-3B](https://huggingface.co/LiquidAI/LFM2.5-VL-3B-GGUF) y [ficha GGUF del drafter DSpark](https://huggingface.co/LiquidAI/LFM2.5-VL-3B-DSpark-GGUF): pesos F16 disponibles y receta de `llama-server` con `--spec-type draft-dspark`.
- [Documentación de speculative decoding de llama.cpp](https://github.com/ggml-org/llama.cpp/blob/master/docs/speculative.md).
- Liquid publica para llama.cpp/M3 Ultra 1,57–2,14× de decode y 1,30–1,77× end-to-end. Es una medición externa en otro hardware; no la mezclo con el resultado local. Liquid afirma equivalencia bajo greedy, mientras que en la prueba local `n=8` una descripción cambió levemente de redacción con `temp=0`; se conserva como discrepancia observada, no como afirmación general de pérdida de fidelidad.

## Hardware, modelos y protocolo

- Windows; AMD Ryzen 9 9950X3D, 16 núcleos/32 hilos, 61,7 GiB de RAM; 2× RTX 3090 de 24 GB. El benchmark aislado usó CUDA1 para no interferir con el `llama-server` ajeno que seguía activo en CUDA0. Ese servidor se mantuvo funcionando durante las pruebas.
- Runtime oficial `llama.cpp b10964`, commit `b29c606e2`; target `LiquidAI/LFM2.5-VL-3B-GGUF:F16` (5,403,158,560 bytes), `mmproj-LFM2.5-VL-3B-F16.gguf` (853,993,952 bytes) y drafter `LiquidAI/LFM2.5-VL-3B-DSpark-GGUF:F16` (567,205,280 bytes). Archivos locales en `D:\Models\llamacpp\LFM2.5-VL-3B-DSpark-bench`.
- Misma huella para control y DSpark: contexto 8192, batch 512/ubatch 128, KV K/V `q8_0`, Flash Attention, 16 hilos, reasoning off, greedy `temp=0`, top-p 0,95, top-k 20, min-p 0, penalidad repetición 1, presencia 0, un slot. Se usó F16, igual que el benchmark de referencia; la publicación no mide aquí quantizaciones.
- Tres prompts con la misma imagen sintética de 1280×800: lectura de estado, un pedido de descripción de controles y un probe exploratorio de visión/herramienta. Se guardaron tres repeticiones por target/draft. Para los factores de decode de estado y descripción uso el primer request de cada servidor; las repeticiones posteriores se benefician del prompt KV cache y se guardan como dato bruto, pero no se usan para speedup end-to-end.
- El probe exploratorio `computer_use_tool` de los dos primeros JSON usó una firma simplificada y **no** representa el contrato real; queda preservado pero excluido del veredicto. La evaluación que decide Computer Use está en el tercer JSON: llamada exacta `desktop_click` de LlamaCode (coordenadas normalizadas 0–1), `cache_prompt=false`, tres requests por perfil, misma imagen. Las llamadas no se ejecutaron para no hacer un click real.
- El control y ambos drafts devolvieron un `tool_calls[0]` válido. Se puntuó el centro del switch visible, aprox. x=1126/1280=0,88, y=237/800=0,296. Los tres devolvieron x=0,5 y=0,5: error de 486 px en horizontal y 163 px vertical sobre la fixture.

## Resultados de lectura visual

`decode ×` y `end-to-end ×` usan control/draft; son mediciones de un primer request por prompt, no un intervalo de confianza.

| Caso | Control decode / wall | DSpark n=8 decode / wall | DSpark n=9 decode / wall |
|---|---:|---:|---:|
| Leer estados | 131,8 tok/s · 1345 ms | 309,9 tok/s (**2,35×**) · 983 ms (**1,37×**) | 273,9 tok/s (**2,26×**) · 901 ms (**1,14×**) |
| Describir controles | 122,9 tok/s · 1516 ms | 283,4 tok/s (**2,30×**) · 1089 ms (**1,39×**) | 407,2 tok/s (**3,33×**) · 1061 ms (**1,61×**) |

La fixture fue leída correctamente en las tres configuraciones: tema oscuro, telemetría y diagnósticos estaban desactivados. Estas dos respuestas cortas indican una ganancia de velocidad; no califican la calidad general de VQA, OCR ni grounding.

## Resultados del tool-call real

Tres repeticiones por configuración, sin cache KV de prompt. Las medianas están calculadas a partir de esos tres requests.

| Perfil | Decode mediano | Wall mediano | tool_calls válidas | Coordenadas emitidas | Aceptación draft |
|---|---:|---:|---:|---|---:|
| Control | 129,7 tok/s | 895 ms | 3/3 | `(0.5, 0.5)` · incorrecta | — |
| DSpark n=8 | 159,5 tok/s · **1,23×** | 987 ms · **1,10× más lento** | 3/3 | `(0.5, 0.5)` · incorrecta | 17/64 = 26,6% |
| DSpark n=9 | 187,3 tok/s · **1,44×** | 890 ms · prácticamente igual | 3/3 | `(0.5, 0.5)` · incorrecta | 18/63 = 28,6% |

La aceleración de tokens no corrigió la selección espacial ni redujo consistentemente la espera total. En este escenario de un solo click, el prefill visual y la variabilidad de la primera pasada pesan más que generar unos tokens más rápido. No hay una ventaja práctica de Computer Use.

## Decisión de perfiles e impacto en LlamaCode

En [`assets/system_profiles.json`](../assets/system_profiles.json) quedaron tres entradas con contexto 8k, `manualOnly: true`, `best: false`, `favorite: false`, `benchmark: true`, `autoCompanion: false` y mínimo llama.cpp b10964:

- `sys-bench-lfm25-vl3b-f16-control-20260926`: target y `mmproj` F16, baseline visual.
- `sys-bench-lfm25-vl3b-dspark8-20260926`: el mismo target + draft F16, `draftNMax=8`.
- `sys-bench-lfm25-vl3b-dspark9-20260926`: el mismo target + draft F16, `draftNMax=9`.

La carpeta local contiene target, mmproj y drafter; los pesos no se agregan al repositorio. Los perfiles usan sampling greedy sólo para reproducir el test de equivalencia. Si se habilitan para un experimento con otro sampling, revalidar precisión y tool-use. No se tocaron el harness, el parser, los perfiles de Charla ni los perfiles productivos/default.

## Artefactos reproducibles

- Benchmark inicial n=8: [`artifacts/lfm25-vl-dspark-3090-20260926.json`](../artifacts/lfm25-vl-dspark-3090-20260926.json).
- Benchmark inicial n=9: [`artifacts/lfm25-vl-dspark9-3090-20260926.json`](../artifacts/lfm25-vl-dspark9-3090-20260926.json).
- Probe con contrato real de Computer Use y repeticiones sin cache: [`artifacts/lfm25-vl-dspark-computer-use-contract-3090-20260926.json`](../artifacts/lfm25-vl-dspark-computer-use-contract-3090-20260926.json).
- Fixture: [`assets/benchmarks/custom/lfm25_vl_dspark_ui_settings_v1.png`](../assets/benchmarks/custom/lfm25_vl_dspark_ui_settings_v1.png). SHA-256: `7dbf300035862eb581e422144394ff013342d7f859b4e7cfb84326dc73098174`.
