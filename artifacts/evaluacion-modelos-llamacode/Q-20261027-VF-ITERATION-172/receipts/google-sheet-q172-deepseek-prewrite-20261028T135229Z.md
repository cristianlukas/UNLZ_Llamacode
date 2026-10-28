# Google Sheet Q172 pre-write snapshot

- Captured: 2026-10-28T13:52:29Z
- Spreadsheet: `1HonTqnoVJ7-nhogAx8fWbBQp52Vc1E4xWBXkaln1Lfk`
- Ranges read before update: `Accionables!A48:N48`, `Resultados!A371:AF371`, `Resultados!A1:AF1`.
- `Accionables!A48:N48` contains the Q172 DeepSeek action item. Its status is stale: arena-110 stop and arena-90 smoke/retry remain described as pending.
- `Resultados!A371:AF371` contains `Q172-DEEPSEEK-DSX-T16-DUAL3090-SEED42`, but still says download/build/smoke/quality pending. No ASTRA Q172 control row exists in `Resultados`.
- Existing local source of truth: `receipts/dsx-t16-quality-seed42-summary.json`, `receipts/astra-control-seed42-summary.json`, `runs/deepseek-t16/astra-vs-dsx-seed42.json`, and the corresponding `RESULTS.md` section.
- Planned update: replace row 371 with the completed DeepSeek seed42 record and append a separate ASTRA control record; update only the Q172 actionable row. Keep unsupported prefill/decode TPS as N/D and make the shared TC-92 safety failure explicit.
