# Q234 · Qwen3.8-27B UD-Q4_K_XL · Tandem Q173 32K

- Estado: **PASS**, 3/3 requests; cada una procesó 32.768 tokens de prompt y generó 128 tokens.
- Perfil: Tandem CUDA SM86 Q210, 2×RTX 3090 (ASUS+PNY), split por capas 1:1, K/V q8_0; prompt 32K, seed 42, thinking off.
- Prefill: **927.87 ± 7.41 tok/s**, repeticiones 937.69, 926.11, 919.80.
- Decode: **33.30 ± 0.01 tok/s**, repeticiones 33.31, 33.30, 33.29.
- TTFT de solicitud: 35.32 s promedio (prompt de 32K; no es tiempo de inicialización). API-ready diagnóstico: 10.839 s; cold/hot init: N/D.
- Validación: eventos server-side exactos, 3/3 completos; logs registran buffers CUDA0 y CUDA1; server exit 0 y puerto 18773 libre. Temperatura al finalizar ≤70 °C en ambas tarjetas.
- Calidad/Q172: **N/D, no ejecutado en este test**. Sin afirmación de superioridad; es un nuevo punto de ladder contra Q213 8K.
- Intento precedente Q233/QEngine Qwen3.8-27B-INT4: no llegó a inferencia por reserva insuficiente en ASUS; anotado en Resultados!E516.

Recibos: `receipts/preregistration.json`, `receipts/q234-result.json`, `runs/q173-32k-tandem.json`, `runs/q173-32k-tandem-progress.jsonl`, `logs/server.log`.


Actualización del ladder (2026-11-16): Q237 8K y Q236 64K completaron la misma cohorte exact-token. El promedio igual-peso de Q173 8K/32K/64K es P903.464 y D31.7088 tok/s; el resultado propio de esta fila sigue siendo el punto32K. Q172 no se ejecutó. Ver Resultados!520 y Modelos locales por peso!4.
