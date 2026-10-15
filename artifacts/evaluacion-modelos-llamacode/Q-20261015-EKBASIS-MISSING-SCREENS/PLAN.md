# Plan — Q-20261015-EKBASIS-MISSING-SCREENS

- **Estado:** screening parcial completado el 2026-10-15T15:01:41Z; agente/GUI E2E no evaluables con el entorno disponible. Lock `e02e2104-5bc4-4030-a7d4-955f13601e32`.
- **Antecedente:** `Q-20261009-EKBASIS-27B` cerró dos screens textuales (Computer Use y clasificación Git), pero no midió imagen, recuperación con payloads largos ni latencia como probe independiente. No se repiten aquellas suites.
- **Objetivo de este seguimiento:** completar evidencia local que sea ejecutable sobre el mismo checkpoint Ekbasis-27B-INT4, vLLM 0.30.0 y API oficial `serve.py` 1.3. No integrar nada al agente ni modificar perfiles productivos.

## Alcance preregistrado

1. **Visión de imagen (screening):** usar el fixture sintético `vision-holdout-v1` y enviar una imagen local como data URI al endpoint oficial `/v1/systemone`. Hacer 11 preguntas tipadas de conteo (4 clases de forma + 7 colores), opciones 0–3. Verificador exact-match externo. No accionar la GUI ni tratarlo como Computer Usage E2E.
2. **Recuperación de estado y contexto efectivo (screening):** preguntas tipadas con un hecho sintético único insertado alrededor del 5%, 50% o 95% del estado. Tres longitudes de estado aproximadas (1K, 2K, 3.5K tokens); medir tokens efectivos, aciertos y latencia. El server está limitado a `max_model_len=4096`; no se probarán 16K/262K/1M ni se inferirá calidad de contexto largo.
3. **Rendimiento del predictor (probe):** 12 solicitudes seriales cortas con esquema determinista; las nueve consultas de contexto también miden latencia por tres tamaños de payload. Medir latencia cliente/servicio, p50/p95, requests/s y tokens de entrada. No es TPS de generación ni una prueba de carga multi-cliente; `max_num_seqs=1`.
4. **Coding/agent y Computer Usage E2E:** sólo confirmar disponibilidad de runner compatible. Para afirmar reducción de daño hacen falta brazos emparejados sin/con sidecar y estado final verificado. No se sustituirá el agente real por un mock. Preflight reporta que no existe `node` en PATH; no se instalarán runtimes ni se conectarán acciones a apps del usuario.
5. **Ingi-Charla/audio:** auditoría de interfaz. El API oficial evaluado ofrece decisión tipada sobre texto e imágenes; no declara entrada acústica, ASR ni TTS. Sin una modalidad acústica publicada, no enviar audio ni medir WER/CER/RTF.

## Criterios y límites

- Salida válida requiere HTTP 200, respuesta tipada parseable y todos los campos esperados.
- Visión: reportar exactitud por propiedad y exact match de 11/11; el conjunto sintético es pequeño y no mide pantallas reales.
- Contexto: conservar todas las solicitudes y la ubicación del hecho; cualquier respuesta errónea cuenta como fallo de recuperación. 9 tareas no permiten estimar generalización.
- Performance: reportar distribución descriptiva, sin declarar ganador ni comparar con otra GPU/runtime.
- Toda llamada usa sólo loopback. No se ejecuta una acción ni un comando propuesto por el modelo.
- Preflight actual: GPU1 tiene 24.016 MiB libres y no tiene proceso de cómputo listado; RAM disponible 106 GiB, PSI 0, swap preexistente 5 GiB, sin tocar swap. Si baja la RAM disponible de 32 GiB, aparece presión sostenida o falla el servicio, detener y preservar el intento.


## Cierre del seguimiento

- El checkpoint volvió a verificar SHA-256 `3ef9d39220a665c741bd734dfa59637607f62993f7f1a52dca2383af6cd085e1`; runtime vLLM 0.30.0, PyTorch 2.13.0+cu130 y Transformers 5.19.0. El servidor cargó en una RTX 3090, `max_model_len=4096`, una secuencia; el API oficial 1.3 quedó en loopback.
- Visión: 9/11 propiedades correctas; formas 4/4 y colores 5/7. El holdout sintético confundió amarillo y naranja, con confianza 0,796 y 0,948.
- Recuperación: 9/9 preguntas exactas con el hecho cerca del 5%, 50% o 95%; input efectivo máximo 3.526 tokens. No es una medición >4K ni un contexto largo.
- Rendimiento: 12/12 solicitudes seriales, mediana 135,67 ms, p95 136,90 ms; no se midió TPS de generación ni concurrencia.
- La primera configuración del adaptador repitió por error `/v1/completions` y obtuvo 404 durante warmup; el URL base corregido inició y todos los requests puntuados terminaron con HTTP 200. No hubo casos puntuados en el primer intento.
- No hay runner local compatible para agente conectado (`node`/Playwright/Chromium ausentes) ni integración Ekbasis en el agente LlamaCode; no se sustituyó por un mock. No se evaluó Computer Usage E2E. El API revisado admite texto e imágenes, no una modalidad de audio; Ingi-Charla queda fuera.
- vLLM y el adaptador propios fueron detenidos; los puertos 18171/18172 quedaron libres. MemAvailable posterior 106 GiB, PSI 0, swap 4,9 GiB (frente a 5,0 GiB inicial), GPU1 108 MiB y sin procesos de cómputo.
