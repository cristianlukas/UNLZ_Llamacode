# Q137 — Resultados migrados a Google Sheets

## Resultado

Se añadieron **116 filas** a `Resultados!A29:AF144`: 58 perfiles realmente alcanzados por el ledger de agosto y 58 perfiles o variantes respaldados por informes locales posteriores. La pestaña conserva sus 27 filas previas; ahora contiene 143 perfiles desde la fila 2 hasta la 144.

Se revisaron las 18 pestañas del workbook. Solo se escribió en `Resultados`. El readback confirmó 116 filas, 32 columnas, 116 IDs únicos y **0 celdas diferentes** respecto de los datos enviados (3.712 celdas verificadas). SHA-256 del recibo exacto JSONL: `29c12bff5e60480f2110aa7e05aca115b54578899ee69c7142139cf546185e07`.

## Cobertura incorporada

- Ledger de campaña de agosto: 58 perfiles ejecutados o parcialmente ejecutados, con estado, fingerprints, etapas, puntuaciones, tiempos y limitaciones conservados.
- Informes posteriores: Ornith/DFlash y modelos compactos; Qwen 3.8 Unsloth a contexto largo; ASTRA/SOL/Swift; perfiles W4A16, Tensor/Layer split y evaluación PPL; auditorías NInfer/RCO/DFlash; campañas LC-H1 y BCB directas; variantes Qwen 3.5 4B; par TaskFlow SOL/ASTRA.
- Cada fila conserva su cohorte y protocolo. Los puntajes directos BCB no se combinaron con LC-H1.

## Límites de interpretación

- Los perfiles 59–86 del ledger se describen como **no iniciados** y se excluyeron.
- Los campos sin evidencia se dejan como N/D. No convertí throughput histórico ambiguo en prefill/decode.
- Warmup, errores de infraestructura, timeouts, cancelaciones y formato inválido se registran como bloqueos/ejecuciones incompletas, nunca como calidad cero.
- No se infiere uso productivo ni rutas locales de modelo cuando las fuentes no lo acreditan.
- No se calcula una clasificación global ni una métrica calidad/velocidad entre harnesses incompatibles.

## Verificación y ejecución

El contenido escrito se releyó íntegramente desde Sheets y se comparó celda por celda con la carga preparada. No se ejecutaron modelos, benchmarks, builds, pruebas de software ni operaciones de GPU. El recibo completo está en `receipts/sheet-migration.json` y las 116 filas exactas leídas de vuelta en `receipts/sheet-migration-rows.jsonl`.
