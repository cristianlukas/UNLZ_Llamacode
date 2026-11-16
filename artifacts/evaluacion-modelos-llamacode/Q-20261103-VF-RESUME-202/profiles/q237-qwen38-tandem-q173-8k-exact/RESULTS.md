# Q237 · Qwen3.8-27B UD-Q4_K_XL · Tandem exact-token Q173 8K

- Estado final: **PASS**; worker bounded/detached terminó success, servidor exit0, puerto18776 libre.
- Artefacto: GGUF SHA-256 3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e; runtime Tandem CUDA SM86 Q210 SHA-256 31de89f011944d9f88d7f8fd188df04d6d1c93db5faad1a697820ad36c0eae96.
- Hardware: ASUS+PNY RTX3090; layer split1:1; KV q8_0; contexto8320; tres repeticiones secuenciales, seed42, cache off, 128 output.
- Validación exacta del servidor: **3/3** prompts de8192 tokens y128 tokens de salida.
- Prefill **979.97 ± 3.91 tok/s** (984.62/980.25/975.05). Decode **36.759 ± 0.035 tok/s** (36.803/36.716/36.758). TTFT medio **8.360 s**; API-ready10.45s diagnóstico; cold/hot init N/D.
- Q172/calidad N/D. No es un resultado de calidad ni decisión de adopción.
- Ladder Q173 del mismo perfil ahora válido en8K/32K/64K: puntos P/D 979.97/36.759, 927.87/33.298, 802.55/25.070. Promedio de contexto con igual peso **903.46 prefill / 31.709 decode tok/s**; cada punto conserva n=3. No mezclar con otros motores/perfiles.
- Q235 se conserva inválido; Q172 Q227 del mismo modelo conserva su fallo TC-74 y no se modifica.
- Google Sheets: Resultados fila520 actualizado/readback PASS; Modelos locales por peso fila4 completada con el promedio Q173 8K/32K/64K y cada punto por separado. Readback en receipts/q237-sheet-sync-readback.json.
- Preregistro y recibos: receipts/preregistration.json, receipts/cpu-fixture-test.json, receipts/q237-result.json, receipts/postflight.json; progreso runs/q173-8k-exact-tandem-progress.jsonl.
