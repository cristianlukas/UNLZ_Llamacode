# Q153 — estado de ejecución

**Estado actual:** evaluación cancelada por decisión de retención 2026-10-26 20:47 UTC; Huihui v2 retirado antes de inferencia. No hay resultado de modelo.

- Google Sheet Listado: 57 celdas de preregistro escritas y leídas de vuelta sin diferencias en Evaluaciones LlamaCode!A357:J357, Accionables!A26:N26, Inventario de modelos!A18:R18 e IA local!A63:O63. WRAP/TOP permaneció intacto. El detalle está en receipts/google-sheet-prereg.json.
- Preflight inicial (2026-10-26 19:55:20 UTC): no se encontró inference server, listener de API de modelo ni contenedor Docker. Ambas RTX 3090 se detectan. D dispone de 500.149.567.488 B libres. MemAvailable 113.939.988.480 B; PSI de memoria 0; swap utilizado 4.414.611.456 B, sin presión sostenida.
- Se aplica el gate Q116-A2 (5/5 fixtures CPU): warning full≥20% O some≥70% por 30 muestras de 10 s; parada full≥60% O some≥80% por 15 muestras; reset severe-any al caer ambas. MemAvailable, RSS y swap por sí solos no paran pruebas. La interfaz/ArtCraft no se cerró. La descarga de pesos está en D; Control 0.1.51 y Qwen 0.1.50 tienen SHA verificada y están extraídos aislados. No hubo pack, servidor, inferencia, benchmark, build ni kernel GPU.
- **Siguiente paso:** dejar completar el checkpoint a D, verificar tamaño/SHA y luego validar pack/API y asignación a ambas GPU antes de medir; el runtime pinneado ya fue verificado y extraído en D.

## Progreso preparatorio — 2026-10-26 20:25 UTC

- Integridad parcial: shard 1/3 verificado (10.946.624 bytes; SHA-256 coincide con el manifiesto fijado). Los otros dos shards aún están en descarga y no tienen SHA local validada.
- La cabecera GGUF del shard 1 declara `qwen4exp`, “Qwen3.8 Flash Next”, split 3/3 con 1.224 tensores en total; el primer shard contiene solo metadatos, como corresponde. Recibo: `receipts/model-header-inspection.json`.
- Los metadatos completos de tokenizer del shard Huihui y del shard control ASTRA coinciden byte-lógicamente: 248.320 tokens, 247.587 merges, SHA-256 canónica `c4f14798e03b8d2fadcb06bc42f1d0fce3cc2c9bcc743b6bdec16bb03b59f4fd`. Esto permite reutilizar prompts idénticos entre brazos; los tokens reales se registrarán por solicitud. Recibo: `receipts/tokenizer-comparison.json`.
- Dependencia del pack validada sin instalar paquetes: `gguf-py` del commit exacto de llama.cpp requerido por Control 0.1.51 (`3cf03257f219afbe7334045ff7c6a06ac68c627d`) importa correctamente IQ4_XS/BF16; working tree limpio.
- Inspección del packer: `--compat-bf16` es necesario para las proyecciones pequeñas IQ4_XS. El pack se hará sin `--experts-bin`, evitando duplicar pesos que el motor lee de los shards.
- El dry-run de Tool-Eval 2.8.0 confirmó que `--hardmode-only` resuelve exactamente TC-70–TC-97 (28 escenarios de categoría P) con contexto de 32K y los parámetros fijados; no llamó a un servidor ni ejecutó inferencia. Recibo: `receipts/bench-harness-preflight.json`.
- No hubo build, servidor, inferencia, benchmark ni uso de GPU. ArtCraft y los modelos conservados siguen intactos.
- Recibo: `receipts/artifact-dependency-preflight.json`.

ASTRA Flash-Next RCO IQ2_XS, SOL, MTP compartido, PeritoSoft y resultados históricos se conservan.


## Cierre por decisión de retención — 2026-10-26 20:47 UTC

- Descarga detenida antes de completar; 11 archivos parciales eliminados (90.088.295.210 bytes). El espacio libre observado en D aumentó 90.088.308.736 bytes.
- No hubo pack, server, inferencia, benchmark ni uso de GPU para Q153. Prefill, decode, calidad, seguridad, tiempo total y contexto quedan **N/D**, no cero.
- Runtime/control aislado y evidencias se conservan. SOL, ASTRA RCO IQ2_XS y MTP compartido siguen presentes. No se escribió fila en `Resultados`.
- El primer SIGTERM dejó viva la raíz Electron y reapareció su worker. Se identificaron y terminaron después 14 procesos de PeritoSoft/tray y el `llama-server` Qwen3.5-9B exacto. Verificación a 20:51 UTC: cero procesos PeritoSoft, cero servidor Qwen3.5 y puertos 32100/32101/8033 cerrados. La GUI Codex y Plank permanecieron intactas; el supervisor desktop no se detuvo.
- Recibos: `receipts/candidate-cleanup-preregistration.json` y `receipts/candidate-cleanup-completion.json`.
