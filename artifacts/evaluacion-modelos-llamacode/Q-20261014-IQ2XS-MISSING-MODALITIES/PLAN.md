# Plan y cierre — Q-20261014-IQ2XS-MISSING-MODALITIES

## Objetivo

Completar la cobertura que faltaba para IQ2_XS y comparar sus perfiles con el Qwen3.8-27B Q4 denso: recuperación de contexto, Server Speed, Computer Usage, visión y compatibilidad de audio. No repetir la campaña de coding/agentes ya evaluada el 2026-10-12; no modificar perfiles ni código productivo.

## Modelos y condiciones

- Candidato: ISTA-DASLab Qwen3.8-Flash-Next-GSQ-RCO-GGUF, revisión ed59f92082b1e93c0e96d60a8b11aab089b52f09; IQ2_XS en Strata 0.1.41.
- Control: ggml-org Qwen3.8-27B-GGUF, revisión efbb3b1f70a21d97fd4495240648405f7228554f; Q4_K_M en llama.cpp 0.4.1-dev.
- Ambos son perfiles dual RTX 3090 con ventana de 131.072 tokens y sampling común conservador. IQ2_XS usa KV int8 y caché de expertos Strata; Q4 usa KV Q8_0 de llama.cpp.
- La comparación mide los perfiles completos entre dos engines; no permite atribuir diferencias a la cuantización por sí sola.
- Pesos, encoder visual, runtime, hashes y URLs de fuente están en receipts/model-source-manifest.json.

## Resultado por prueba

1. **Context Retrieval:** completado; mismo fixture, 117.825 tokens según tokenizer del pack y siete hechos exactos. IQ2_XS 7/7 en 33,719 s; Q4_K_M 7/7 en 181,940 s.
2. **Server Speed v1:** completado; dos pasadas, un warmup, 8 categorías, 32 muestras por perfil, un slot, sin concurrencia, límite de prefill 65.536. Cero fallos. IQ2_XS: 152,36 decode / 304,15 prefill tok/s, TTFT 348,41 ms. Q4_K_M: 37,45 decode / 359,01 prefill tok/s, TTFT 267,59 ms.
3. **Computer Usage:** completado; tres réplicas por perfil en Xvfb privado sobre un formulario local nuevo. IQ2_XS 0/3; Q4_K_M 0/3. El registro separa las ventanas no navegadas y las fallas de alcance visual/timeout. No se promueve el perfil de agente.
4. **Visión:** completado después de validar los encoders. Ambos contaron 3 triángulos azules y 2 círculos rojos. IQ2_XS 1,478 s; Q4_K_M 8,670 s. El primer intento IQ2_XS se truncó por un límite de 128 tokens y se conservó; el retest a 512 pasó.
5. **Ingi-Charla/audio:** auditoría de compatibilidad, no inferencia acústica. Los model cards son Image-Text-to-Text; GET /v1/audio/transcriptions dio 404 en el endpoint Q4. No se midió WER/CER ni se presentó texto como audio.

Ver [RESULTS.md](RESULTS.md) y receipts/evaluation-summary.json para conclusiones, limitaciones y referencias a cada recibo.

## Preflight y cierre

El primer preflight quedó bloqueado por 5,29 GiB de swap usados. Tras la petición del usuario de liberar memoria, se despejó swap y se reactivó; el preflight nuevo registró 180 KiB de swap usado y ~104 GiB disponibles. Los modelos se cargaron secuencialmente. Al cierre no quedan servidores del ensayo, procesos en Xvfb :97 ni listeners en 8350/8765/8898; quedan ~105 GiB de RAM disponible y ~47 GiB de VRAM libre. Los datos finales están en receipts/session-cleanup.json.

Sólo cambiaron scripts/fixtures/recibos de esta campaña y la documentación de evaluación. Los scripts de sesión X11 se lanzan explícitamente con bash para funcionar en el checkout NTFS. No se construyó ni probó el producto porque no hubo cambios C++/QML/core. La cola quedó cerrada bajo el token e7981694-e63a-40a8-b06e-c07b833d35cb.
