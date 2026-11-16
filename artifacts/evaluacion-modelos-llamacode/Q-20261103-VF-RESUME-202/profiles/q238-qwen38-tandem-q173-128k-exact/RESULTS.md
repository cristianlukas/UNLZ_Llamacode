# Q238 · Qwen3.8-27B UD-Q4_K_XL · Tandem Q210 · Q173 exact 128K

## Resultado

- **PASS**: three sequential no-cache requests passed the exact server-side token gate: prompt `[131072, 131072, 131072]`, output `[128, 128, 128]`; one `bench_complete=ok`, no request errors.
- Model SHA-256 `3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e`; runtime SHA-256 `31de89f011944d9f88d7f8fd188df04d6d1c93db5faad1a697820ad36c0eae96`. 2× RTX 3090 ASUS GPU0 + PNY GPU1, layer split 1:1, q8_0 KV, context131200.
- Q173 P **633.1577 ±1.3303 tok/s**; D **19.99684 ±0.00083 tok/s**; TTFT **207.014 s**; API-ready **10.466 s** diagnostic. Cold/hot initialization **N/D**.
- Same-profile valid ladder, n=3 each: 8K P/D979.9728/36.75907; 32K927.8669/33.29768; 64K802.5527/25.06973; 128K633.1577/19.99684. Equal-context means over these four rungs: P **835.8875**, D **28.78083 tok/s**. At 128K vs64K, P is 21.1% lower and D20.2% lower. This is context-dependent throughput evidence only; it is not a cross-runtime comparison.
- **Quality remains N/D.** Q172 was not rerun; the existing same-profile Q172 partial result and TC-74 failure remain a separate autonomous-use blocker. No LHA-1 result is implied. No adoption, deletion, or supersession decision follows from Q238. Production and PeritoSoft were untouched.
- Detached unit exited0, port18778 free, no CUDA compute app, and no inference-server executable remained after cleanup. Preflight MemAvailable116.47GB, PSI avg10=0; observed temperatures stayed ≤76°C. During-run GPU memory samples were about12GB per card (sampled, not a continuous peak record).

## Evidence

- Preregistration: `receipts/preregistration.json`; exact-token CPU fixture PASS: `receipts/cpu-fixture-test.json`; worker result: `receipts/q238-result.json`; server progress: `runs/q173-128k-exact-tandem-progress.jsonl`; postflight: `receipts/postflight.json`.
- Google Sheets `Resultados!521` updated/readback; `Modelos locales por peso!4` updated with equal-context mean and the four per-context measurements.
