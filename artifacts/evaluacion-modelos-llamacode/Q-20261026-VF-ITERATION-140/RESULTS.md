# Q140 — Reconciliación de pendientes con Q135/Q138

**Fecha:** 2026-10-26
**Estado:** reconciliación completada; no se inició un test nuevo.

## Hallazgos y correcciones

1. **JetBrains Qwen3.8-3.6-27B-blend:** `Accionables!A20:N20` seguía indicando “NO ejecutada”. La misma revisión y quant ya tuvo A/B dual-RTX3090 de tres semillas en Q135. Actualicé estado, decisión, evidencia y fecha en `D20:N20`: blend 78/100 frente al control Qwen3.8-27B 83/100; regresión TC-80 3/3; E2E 9,03% más rápido en pares correctos, inferior al gate 15%; tokens +0,33%. Se resuelve sin adopción. Q135 sólo probó 32K; los perfiles 64K/128K no se justifican después de fallar el gate de calidad, salvo caso material nuevo.
2. **Qwen27B/Ghidra:** el inbox, la app local y `IA local!A58:O58` todavía presentaban Q138 como preregistrado/bloqueado antes de inferencia. Los tres se actualizaron como piloto completado en fixture C sintético propio. Qwen obtuvo 31/36 y ASTRA 22/36, pero el tiempo mediano Qwen fue 2,84× (gate máximo 1,25×); no hubo casos críticos/safety. No promover Qwen27B. Esto no prueba el workflow sobre un binario real de R36S/PortMaster.

## Pendientes que siguen siendo externos

- **Q35/Q32 — Windows:** los gates de Job Objects y NInfer Windows preview esperan una sesión/host Windows nativo. El usuario pidió dejar esos gates pendientes hasta tenerla.
- **Qwen tools/tenant:** no hay un principal autenticado no falsificable ni policy confiable por recurso. No se inventó un fixture ni se aceptó tenant desde el prompt.
- **VF-20261019 #20/#21 — routing híbrido:** faltan proveedor y modelo/ID efectivos, `keyRef`, techo de gasto y límites de datos autorizados; no hubo llamadas externas ni gasto.
- **R36S real:** falta seleccionar un target propio o de licencia abierta y su oráculo reproducible. Q138 fue sintético y no se repite.
- Otras entradas se mantienen bloqueadas por incompatibilidad de GPU/runtime/espacio, ausencia de artefacto o fuente no verificable, según inbox y recibos existentes.

No encontré una nueva prueba local y decision-changing que pueda arrancar sin incumplir esos gates. No corrí build, test, benchmark, inferencia ni GPU. ASTRA, SOL, Flash-Next productivo y modelos PeritoSoft no se modificaron.

## Verificación

- Google Sheet: `Accionables!D20:N20` e `IA local!I58:L58`, lectura de vuelta exacta; 15 celdas revisadas con `WRAP` y alineación `TOP`.
- Inbox VF-20261019-01 y sus adiciones: 69 entradas; #63 ahora enlaza la conclusión Q138.
- App local: `data/actionables.json`, ID `vf-qwen-ghidra-open-fixture-20261025` actualizado. Copia pre cambio: `data/actionables.json.bak.q140-20261026T0537Z`.
- Recibo con IDs de celdas, hashes y bloqueos: `receipts/reconciliation.json`.
