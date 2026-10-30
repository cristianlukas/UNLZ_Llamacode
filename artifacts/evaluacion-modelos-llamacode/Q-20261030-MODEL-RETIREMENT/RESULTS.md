# Q192 — Resultado de limpieza por dominancia

Fecha: 2026-10-30T15:13:19Z

Se revisaron las 84 filas de modelos del inventario. Once perfiles tenían valor numérico en las tres métricas requeridas. Cuatro filas estaban dominadas numéricamente en las tres: PrismML (fila 20), Gemma 12B (23), TERRA Qwen3.8-27B (24) y Qwen3.6-35B-A3B Q4_K_XL (27). Se retiraron sólo dos archivos, tras verificar tamaño, SHA-256 y que ningún servidor ni proceso tenía abiertos esos artefactos.

## Archivos retirados

- `Ternary-Bonsai-2-27B-PQ2_0.gguf`, D: 7.206.168.928 bytes, SHA-256 `3907dc1658db1f78a9826bf8d5bcb8dc65db0d466388937af57f2294fae62ec1`. P/D/Q172 832,88/53,53/75; dominador NInfer v3 (fila 17) 1.513,90/157,44/83,33. Ladders de cinco niveles aproximadamente 8K–256K; terminal Prism 256K y NInfer 261.888. Tool-Eval 2.8.0. El Q172 Prism es seed42=75; NInfer es media seeds42–44=83,33. Ambos fallaron gates críticos.
- `Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf`, HDD extra: 22.853.663.008 bytes, SHA-256 `55983c5a75a1ab969824077b3bb3de4146e82a9234072b48ad4e8f92ad3fe9f1`. P/D/Q172 6.426,38/114,17/0; dominador numérico LFM2.5-VL-3B (fila 26) 8.712,98/159,18/25. La comparación de columnas agregadas no implica equivalencia: Qwen3.6 es LLM con ladder hasta 261.888 tokens; LFM es VLM medido hasta 31.872. El Qwen36 falló 84/84 escenarios por agotamiento del presupuesto de razonamiento.

Se liberaron 30.059.831.936 bytes de archivos. El espacio libre medido pasó de 7.413.547.008 a 14.619.717.632 bytes en D: y de 5.792.980.992 a 28.646.645.760 bytes en HDD extra.

## Conservados

- Gemma 4 12B QAT Q4_0 (fila 23): aunque está dominado en las tres columnas, los fixtures de PeritoSoft esperan el GGUF en `D:\Models\llamacpp\gemma-4-12b-it-qat-q4_0.gguf`; la copia local corresponde a esa ruta.
- TERRA Qwen3.8-27B (fila 24): aunque la fila tiene promedios menores que SOL, la configuración local conserva el perfil de lanzamiento LlamaCode `2_TERRA · Qwen3.8 27B · vLLM TP2 P2P MTP4 validado`. Se dejó intacto para no romperlo. El Q173 válido es MTP-off, el Q172 es seed42 y MTP4 no obtuvo medición válida por un assert CUDA.

No se tocaron ASTRA ni SOL. También quedaron intactos los snapshots de locks dentro de recibos y la copia de lock de la caché build; no son locks activos. El lock raíz de esta operación se liberó después de la sincronización. No se ejecutaron benchmarks, inferencias ni GPU.

Google Sheets `Modelos locales por peso`: filas 20 y 27 marcadas `Retirado`, peso actual 0, ruta histórica conservada, métricas actuales vaciadas y celda de notas con enlace `Superseded by`; filas 23 y 24 incluyen la razón de conservación. Lectura nativa de vuelta confirmada, fórmulas y WRAP conservados.
