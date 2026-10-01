# QwFN-hybrid: replay de fidelidad

Prueba nueva del 2026-10-01. Compara el `llama.cpp` limpio `ca1426903fabe9af26cd10c42034cb4bbd2e0e11` con el engine híbrido QwFN `6b26989f8a2bdefd6c541ba0d0586c80b9e3b011`, misma quant IQ3_XXS, KV Q8 y los mismos IDs de continuación. Hay un replay por escenario; es una medición directa, no el gate registrado por QwFN, que necesita varias variantes QwFN, repeticiones y el control de ruido de llama.cpp.

## Configuración y entrada

- Host: 2× RTX 3090 de 24 GiB y 123 GiB RAM. Los pares reportados usaron sólo GPU 0; la primera corrida exploratoria de código usó dos GPUs visibles y se descartó del resumen principal.
- QwFN: `ctx=73728`, `batch=32768`, `KV=q8_0`, `--vram 12 --ram 19 --threads 8 --spec-block`; MTP apagado para medir logits del target sin draft. llama.cpp: `--kv q8_0 --ubatch 1`; el replay evaluador fuerza exactamente los mismos tokens.
- Traces exactos, copiados de `bench/tokens` del commit QwFN: `traces/{code,agent,reasoning}.{prompt,replay}`. Los archivos `.nll`, `.topk` y logs de ambas engines están en `raw/`.

## Resultado

| Trace | Tokens | llama.cpp NLL | QwFN NLL | Shift QwFN−llama.cpp (IC bootstrap 95%) | Mean |ΔNLL| | KL top-k | Argmax igual |
|---|---:|---:|---:|---:|---:|---:|---:|
| code | 800 | 0,03020 | 0,02937 | −0,00083 [−0,00156; −0,00020] | 0,00237 | 0,000218 | 99,5% |
| agent | 800 | 0,15380 | 0,15342 | −0,00038 [−0,00239; +0,00168] | 0,01039 | 0,000873 | 99,5% |
| reasoning | 600 | 0,44395 | 0,44371 | −0,00024 [−0,00347; +0,00282] | 0,02103 | 0,001626 | 99,0% |

Las distribuciones son cercanas en estos tres traces. No se mide aquí la estabilidad estadística entre repeticiones, el conjunto largo del gate publicado ni la calidad funcional de las respuestas. Para una decisión de calidad, conservar HE0 → HE20 → BCB y las suites de tools.

No repetir estos tres replays con los mismos IDs, quant, KV y flags como una campaña nueva. Extender en el futuro con más escenarios, null-run y referencias QwFN sólo si hay un cambio de engine/quant o si se necesita completar el gate de paridad completo.
