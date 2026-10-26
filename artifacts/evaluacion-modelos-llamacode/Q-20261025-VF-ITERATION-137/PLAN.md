# Q137 — Historical results migration to Google Sheets

## Objective
Review local historical benchmark results and all tabs of the existing workbook, then append unique, locally supported profile/result records to the existing `Resultados` tab without changing other tabs.

## Preflight and scope
- Repository instructions, README, WORK_QUEUE, and lock were read before edits.
- Exclusive lock owner: `q137-historical-results-f48b7fb562c14411`.
- Spreadsheet: `Listado`, ID `1HonTqnoVJ7-nhogAx8fWbBQp52Vc1E4xWBXkaln1Lfk`.
- Audited all 18 tabs; `Resultados` had 27 existing profile records (rows 2–28), 32 columns A:AF, and blank destination rows 29–144.
- Existing IDs were checked for overlap before writing.

## Sources
- `docs/benchmark-profile-ledger-2026-08.md`: profiles 1–58 reached by the August campaign. Profiles 59–86 were explicitly not started and were excluded.
- Historical reports listed in `receipts/sheet-migration.json`; their 58 resulting profile rows preserve report-specific cohorts and evidence.

## Migration rules
- Appended 116 unique rows: 58 campaign-ledger profiles plus 58 additional report-backed records.
- Preserved distinct test cohorts, including direct BCB vs LC-H1, model-only screens vs agent runs, and distinct runtime/configuration variants.
- Recorded infrastructure, warmup, invalid-format, cancellation, and output-guard outcomes as blocked/invalid/partial; never reinterpreted them as model-quality zero.
- Left unsupported fields as N/D. Legacy stage tok/s were not relabeled prefill/decode without evidence separating those metrics. No cross-suite quality/velocity score was invented.
- Did not infer Windows/Linux model paths or production consumers.
- Kept existing rows and other tabs unchanged.

## Completed write and verification
- Wrote `Resultados!A29:AF144` (116 rows) using existing Arial 10, wrap, top alignment; row height 108px.
- Full readback matched all 3,712 submitted cells; 116 unique IDs, no mismatches.
- Exact row JSONL SHA-256: `29c12bff5e60480f2110aa7e05aca115b54578899ee69c7142139cf546185e07`.
- No inference, benchmark, GPU use, model download, build, or software test.
- Results: `RESULTS.md`; summary receipt and exact rows: `receipts/sheet-migration.json`, `receipts/sheet-migration-rows.jsonl`.
