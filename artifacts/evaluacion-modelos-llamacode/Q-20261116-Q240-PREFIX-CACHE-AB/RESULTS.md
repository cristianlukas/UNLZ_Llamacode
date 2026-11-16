# Q240 — Results

**Completed screening; A/B comparison inconclusive due arm order/cache carry-over.**

- Qwen3.8-27B UD-Q4_K_XL, SHA `3f227079…bc8b01e`; Q210 Tandem llama.cpp, SHA `31de89f0…c0eae96`; dual ASUS+PNY RTX3090.
- Three passes × six turns per arm; 36/36 HTTP requests succeeded; cache metrics available; no tool executed (`tool_choice=none`).
- Rolling-tool: median 530.865 ms; median prompt 549.5 tokens; median cache metric 406.5.
- Unstable-prefix: median 528.705 ms; median prompt 549.5; median cache metric 406.5. Difference is below the preregistered 10% threshold.
- **Limitation:** arms ran serially on one server; the second arm inherited first-arm prefix cache state. Therefore the comparison cannot prove whether schema key order changes reuse. The run does establish that this build reports cache counts and reuses prefix tokens in the tested loop.
- No quality/Q172/LHA conclusion; the harness does not capture or grade answer content. No default change.
- Worker exited 0; server/compute apps and port 18780 were clear after the run; GPU state returned to display baseline.

Raw data: `runs/q240-prefix-cache-result.json`. Full receipt: `receipts/attempt01-completed.json`. Google Sheets read-back PASS: `Resultados!A523:AH523`, `Accionables!D78:N78`, and `Modelos locales por peso!Z4`; details in `receipts/sheet-readback.json`.
