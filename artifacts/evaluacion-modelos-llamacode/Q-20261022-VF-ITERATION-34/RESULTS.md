# Q34 — Resultado de velocidad directa: NInfer Qwen3.8-27B v3 vs SOL

**Estado:** completada; el gate de velocidad preregistrado pasa por poco. No cambia la recomendación de adopción para agentes.

## Decisión

El perfil NInfer v3 superó a SOL al menos 10% en 2 de 5 medianas E2E: copia del prompt de 2K (+38,3%) y de 24K (+11,9%). No alcanzó 10% en ninguna de las tres celdas de generación nueva (+9,6% a 8K, +8,8% a 24K; a 1K fue 1,4% más lento). El gate preregistrado —≥2/5 celdas y cero errores/OOM— pasa exactamente en su umbral.

Esto cierra el hueco de velocidad de Q32 frente al perfil productivo SOL, pero es una comparación de **perfiles completos** en prompts sintéticos de hasta 24.487 tokens. NInfer tiene contexto configurado de 32K; SOL tiene 262K. No separa el efecto de los pesos, runtime, speculative decoding, contexto o hardware.

**Recomendación:** mantener SOL como perfil de coding/agentes y no integrar NInfer por ahora. Q32 dio 78/100 (<gate 80,98), TC-74 falló 3/3, TC-84 2/3 y TC-92 filtró datos cross-tenant 2/3; la velocidad no anula esos fallos. Sólo tendría sentido considerar un piloto aislado sin tools si existe una carga real, prompt-copy-dominante, ≤32K, persistente y capaz de amortizar el arranque (estimación simple: ~43 solicitudes por proceso caliente); antes necesitaría un holdout de calidad de ese uso. No se cambió ningún perfil ni servicio productivo.

## Resultados de la matriz emparejada

| Celda | SOL E2E mediana | NInfer E2E mediana | Diferencia NInfer vs SOL | Lectura |
|---|---:|---:|---:|---|
| Generación nueva · 1K | 3,256 s | 3,302 s | −1,4% | NInfer ligeramente más lento |
| Generación nueva · 8K | 6,191 s | 5,651 s | +9,6% | Mejora, debajo del umbral 10% |
| Generación nueva · 24K | 14,638 s | 13,457 s | +8,8% | Mejora, debajo del umbral 10% |
| Copia de prompt · 2K | 3,001 s | 2,169 s | +38,3% | Pasa umbral |
| Copia de prompt · 24K | 14,126 s | 12,628 s | +11,9% | Pasa umbral |

Se completaron 15 requests por perfil (30 total), tres repeticiones por celda, misma secuencia y prompts; tokens reales emparejados en las 15 parejas, salida mediana 256 por celda y cero errores HTTP/OOM. No hubo discrepancias de tokens de prompt. El resumen completo está en `attempts/direct-sol-speed-02/receipts/speed-results.json`, las mediciones crudas en `runs/speed-measurements.jsonl` y el cierre en `attempts/direct-sol-speed-02/receipts/speed-final-verification.json`.

NInfer inició en 175,69 s frente a 141,91 s de SOL (+33,78 s). El ahorro medio descriptivo fue 0,801 s/request; con esa media, el costo extra de arranque se amortiza alrededor de 42,2 requests medidos. Es una estimación del workload fijado, no una predicción de producción. SOL prefill/decode se derivó aproximadamente de histogramas Prometheus; NInfer usa telemetría por solicitud, por lo que esas tasas no deben leerse como una comparación aislada exacta.

## Diagnóstico del intento inicial y cleanup

El intento 01 llegó a readiness y su warmup devolvió HTTP 500 `EngineCore encountered an issue` antes de cualquier medición. No se guardaron sus logs antes de desmontarlo, por lo que la causa no se pudo recuperar. En el único diagnóstico permitido (A2), un request mínimo sin overrides de sampling respondió HTTP 200 en 1,019 s; completó sus 8 tokens en el canal de razonamiento y terminó por límite. El log diagnóstico no reprodujo el 500 ni un fallo NCCL/OOM; sí contiene warnings de TritonBundler por cubins ausentes. Esto no confirma la causa del primer fallo.

La matriz A3 omitió overrides redundantes sólo en los requests SOL, manteniendo los mismos valores efectivos configurados por su servidor; capturó el log antes del cleanup. Ambos servidores y el contenedor de Q34 se detuvieron. Postflight: cero inference servers/contenedores, MemAvailable 121,58 GiB y SwapFree 3,66 GiB. ASTRA, SOL, Flash-Next productivo, PeritoSoft, perfiles, configuraciones productivas y pesos no se alteraron.

## Próximo paso por prioridad

1. **P1 Flash-Next:** bloqueado en el host Ubuntu; el paquete NInfer revisado indica Windows-only. Reabrir sólo con soporte Linux explícito o entorno Windows compatible.
2. **P2 Qwen3.8-27B:** velocidad vs SOL ya medida; no adoptar en agentes. El siguiente accionable es hardening de seguridad (orden/serialización de tools, autorización de tenant server-side y mutaciones/notificaciones tras commit). Sólo después, y con un caso sin tools concreto, preregistrar un holdout de calidad representativo.
3. **P2.2 OpenJet:** sigue bloqueado; el GGUF tiene 64 bloques y el kernel requiere 65. No repetir los cuatro intentos previos sin compatibilidad/soporte nuevo.
4. **P3 RCO:** screen 0/8 vs control 1/8; gate ≥3/8 no pasa. No repetir la misma revisión.
5. **P4 Swift:** bloqueado por acceso/licencia comercial y compatibilidad exacta.
6. **P5 Strata/claims:** no apareció claim nuevo que justifique otra corrida.

## Artefactos principales

- Plan y enmiendas: `PLAN.md`; prerregistro: `receipts/preregistration.json`.
- Intento 01, diagnóstico A2 y matriz A3: `attempts/`.
- Métricas y verificación final: `attempts/direct-sol-speed-02/receipts/speed-results.json` y `speed-final-verification.json`.
- Cola canónica: `WORK_QUEUE.md`; acción sincronizada en el JSON local de la app y Google Sheets.
