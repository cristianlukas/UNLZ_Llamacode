# Q157 · Resultado

**Estado:** recheck completado; no había procesos objetivo que detener; no se lanzó una inferencia nueva porque los siguientes gates están bloqueados por condiciones externas o ya cerrados.

## Procesos y recursos

- `ps` no mostró procesos cuyos argumentos/nombres correspondieran a PeritoSoft, `llama-server` ni un servidor Strata/Qwen.
- `ss -ltnp` no mostró listeners de inferencia. Los listeners visibles fueron OpenRGB en 6742, CUPS en 631, DNS local en 53 y `artcraft-launch` en 47413; se dejaron intactos.
- `docker ps` no mostró contenedores.
- No se envió señal ni se cerró ninguna aplicación.
- `nvidia-smi` respondió con driver 615.71.09; ambas RTX 3090 estaban a 0% de cómputo (890 MiB y 110 MiB de memoria gráfica ocupada por escritorio/otros procesos).

## Barrido de pruebas siguientes

- Q156 Gyro-M vs ASTRA cerró con no-go de etapa (2/8 cada uno; el candidato más lento E2E) y sus pesos eval-only fueron retirados. No repetir.
- Los gates de NInfer/Flash-Next Q32 y Job Objects Windows de Q35 requieren una sesión de Codex Windows nativa; el usuario pidió dejarlos pendientes hasta que esté disponible.
- Q152 Gyro-Coder-L continúa bloqueada porque el runtime del proveedor no enumera las dos RTX 3090; no descargar el GGUF ni usar fallback de una GPU.
- Q119 del detector de presión está cerrado para Linux: ASTRA DEFAULT 1M y SOL completaron cargas reales sin falso stop/OOM; no hay traza nueva de presión severa que habilite otra prueba. No reducir memoria/contexto ni crear presión artificial.
- Las demás comparaciones Flash-Next locales están cerradas, retiradas o requieren un runtime/artefacto nuevo. ASTRA RCO IQ2_XS y SOL quedaron intactos.

## Decisión

No hay un test de modelo pendiente ejecutable en este host que pueda cambiar la decisión sin reabrir una campaña ya cerrada o ignorar un gate explícito. Mantengo la cola en Q146 con estos puntos de reanudación: Windows nativo para Q32/Q35; runtime dual-3090 corregido para Q152; o nueva evidencia real de presión severa para Q119.

Recibo de proceso/recursos: `receipts/peritosoft-and-next-gate-check.json`.
