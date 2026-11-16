# Q236 · Qwen3.8-27B UD-Q4_K_XL · Tandem exact-token Q173 64K

- Estado final: **PASS en intento02**; intento01 se conserva como inválido por el offset de plantilla y fue detenido antes de repetir más.
- Artefacto: GGUF SHA-256 `3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e`. Runtime Tandem CUDA SM86 Q210 SHA-256 `31de89f011944d9f88d7f8fd188df04d6d1c93db5faad1a697820ad36c0eae96`.
- Hardware: ASUS+PNY RTX3090; split por capas1:1; K/V q8_0; `--ctx-size 65664`; tres repeticiones secuenciales, seed42, cache off, 128 tokens.
- El wrapper local corrigió el re-tokenizado BPE. Con `--pp65535`, las tres solicitudes del servidor fueron exactamente65.536 tokens de prompt y128 de salida; validación server-side 3/3 PASS.
- Prefill **802,55 ± 6,82 tok/s** (811,79 / 800,34 / 795,53). Decode **25,07 ± 0,01 tok/s** (25,061 / 25,065 / 25,083). TTFT medio≈81,67 s; API ready10,58s diagnóstico. Cold/hot init N/D.
- Q172/calidad N/D. Q234 32K y Q237 8K completan puntos válidos del mismo modelo/runtime. Ladder 8K/32K/64K: promedio con igual peso 903.46 prefill /31.709 decode tok/s; Q236 sigue siendo solo el punto64K y no afirma calidad ni superioridad.
- Worker systemd detached, resultado success, server exit0, puerto18775 libre y compute apps libres después. Servicio separado del proceso Codex.
- Sheets: `Resultados!519` actualizado; falta sincronizar la fila perfil correspondiente en `Modelos locales por peso`.
- Recibos: `receipts/preregistration.json`, `receipts/cpu-fixture-test.json`, `receipts/cpu-fixture-test-amendment01.json`, `receipts/attempt-01-invalid-offset.json`, `receipts/q236-result.json`, `receipts/postflight.json`; eventos `runs/q173-64k-exact-tandem-progress.jsonl`.
