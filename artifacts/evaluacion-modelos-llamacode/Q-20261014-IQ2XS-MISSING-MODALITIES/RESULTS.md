# Resultados — Q-20261014-IQ2XS-MISSING-MODALITIES

**Fecha:** 2026-10-14  
**Estado:** Completa como screening incremental.  
**Decisión:** No promover perfiles ni cambiar defaults de producción. IQ2_XS tuvo buen resultado en recuperación larga, velocidad de generación y conteo visual. Ambos perfiles fallaron el holdout E2E de escritorio.

## Resumen de resultados

| Prueba | Flash-Next IQ2_XS / Strata | Qwen3.8-27B Q4_K_M / llama.cpp |
|---|---:|---:|
| Recuperación de contexto, prompt de 117.825 tokens | 7/7 hechos, 33,719 s | 7/7 hechos, 181,940 s |
| Server Speed v1, 2 pasadas, 32 muestras | 152,36 tok/s decode; 304,15 tok/s prefill; TTFT medio 348,41 ms | 37,45 tok/s decode; 359,01 tok/s prefill; TTFT medio 267,59 ms |
| Computer Usage E2E, formulario holdout R4-82 | 0/3 confirmaciones visibles | 0/3 confirmaciones visibles |
| Conteo visual, 3 triángulos y 2 círculos | Correcto, 1,478 s | Correcto, 8,670 s |
| Audio nativo / WER-CER | Auditoría de compatibilidad; no se midió audio | Auditoría de compatibilidad; ruta de transcripción devolvió HTTP 404 |

La comparación de velocidad y calidad es de perfiles completos: Strata 0.1.41 sobre Flash-Next MoE frente a llama.cpp 0.4.1-dev sobre el GGUF denso Q4_K_M. No es un A/B que aísle únicamente la cuantización. Las configuraciones usaron contexto 131.072 y sampling común conservador; hashes, runtime y parámetros están en el manifiesto de fuentes.

## Context Retrieval

Se envió el mismo prompt holdout de 117.825 tokens medidos con el tokenizer del pack. La API reportó 117.877 prompt tokens en ambos perfiles. Los siete valores exactos estaban distribuidos entre 4% y 94% de profundidad y ambos modelos los recuperaron todos.

IQ2_XS tardó 33,719 s; el control Q4 denso tardó 181,940 s. Esta prueba alcanza 117.825 tokens dentro de la ventana común de 131.072; no se probó contexto de 160K ni 262K.

Recibos: [IQ2_XS](receipts/context/iq2xs.json), [Q4_K_M](receipts/context/q4-k-m.json) y [fixture](fixtures/context_retrieval_118000.txt).

## Rendimiento del servidor

Se ejecutó LlamaCode Server Speed v1 con dos pasadas medidas y un warmup, 8 categorías, un slot, sin concurrencia y límite de prefill de 65.536 tokens. Cada perfil produjo 32 muestras válidas y cero muestras fallidas.

IQ2_XS midió 152,36 tok/s de decode, 304,15 tok/s de prefill y 348,41 ms de TTFT medio. Q4_K_M midió 37,45 tok/s de decode, 359,01 tok/s de prefill y 267,59 ms de TTFT medio. En esta configuración, Q4 procesó prefill más rápido y tuvo TTFT menor; IQ2_XS generó tokens de salida con mayor velocidad. La diferencia de engines, arquitecturas y planificadores impide atribuir el delta sólo a los pesos.

Recibos nativos y metadatos: [IQ2_XS](receipts/server-speed/iq2/) y [Q4_K_M](receipts/server-speed/q4/).

## Computer Usage E2E

El holdout fue una página local de despacho: asignar la orden R4-82 a Quartz Bay, marcar Priority, escribir “route checked” y verificar la confirmación visible. Se ejecutaron tres réplicas por perfil, en displays Xvfb privados con resoluciones, locale y tema distintos. No se usó el display compartido.

- **IQ2_XS: 0/3.** En la primera réplica Chrome cargó el fixture, pero el agente no completó el formulario. En las réplicas 2 y 3 abrió una ventana de Chrome sin navegar a la página.
- **Q4_K_M: 0/3.** Las réplicas 1 y 2 agotaron el timeout de 300 s mientras repetían observaciones con “El alcance visual ya no está disponible”; la tercera terminó en 89,121 s sin confirmación visible.

Esto es un fallo del perfil completo de Computer Usage (modelo, backend y herramientas de escritorio), no un diagnóstico aislado del modelo. Las capturas, OCR, mensajes, configuración y logs de cada réplica están bajo [receipts/runs](receipts/runs/).

## Visión

Ambos endpoints aceptaron image_url con el mmproj configurado y respondieron exactamente 3 triángulos azules y 2 círculos rojos. IQ2_XS tardó 1,478 s; Q4_K_M, 8,670 s.

El primer intento IQ2_XS quedó truncado por el presupuesto de salida de 128 tokens antes de emitir el JSON final. Se preservó el recibo truncado y se repitió con 512 tokens; la repetición pasó. El mmproj compartido de Flash-Next fue verificado localmente en 907.543.008 bytes, SHA-256 b1a82259702816a5330d7bd7607cd9676b11780e79ff7348c21103ff3ce49bd0. El encoder oficial del Q4 denso también se validó en el servidor. La prueba es un conteo visual sintético, no una evaluación de OCR compleja.

Recibos: [IQ2_XS](receipts/vision/iq2xs.json), [primer intento truncado](receipts/vision/iq2xs-attempt-1-truncated.json), [Q4_K_M](receipts/vision/q4-k-m.json) e [imagen holdout](fixtures/vision_holdout.png).

## Audio e Ingi-Charla

Las tarjetas identifican ambos modelos como Image-Text-to-Text. El endpoint Q4 de llama.cpp devolvió HTTP 404 para GET /v1/audio/transcriptions. El alcance fue sólo de compatibilidad: no se envió audio, no se evaluó reconocimiento o síntesis de voz, y no hay métricas WER/CER. Ingi-Charla mantiene STT y TTS separados; una transcripción de texto no habría contado como prueba acústica. Ver [auditoría de modalidad](receipts/audio-capability-audit.json).

## Memoria, procesos y cambios

La primera ejecución se detuvo por 5,29 GiB de swap usado. Tras el cierre de aplicaciones indicado por el usuario se liberó swap temporalmente y se reactivó; antes de inferir, el nuevo preflight registró 180 KiB usados y aproximadamente 104 GiB de RAM disponible. Los perfiles se ejecutaron de a uno. Al terminar se detuvieron IQ2_XS, Q4, los daemons de LlamaCode, el servidor HTTP del fixture y Xvfb :97; los puertos 8350, 8765 y 8898 quedaron cerrados. La memoria final observada fue ~105 GiB disponible, 180 KiB de swap y VRAM usada de 855/108 MiB en las dos RTX 3090. También se eliminaron 458.263.379 bytes de caché de Chrome y 22.015.619 bytes de runtime aislado temporal; se conservaron capturas, OCR y recibos.

Los únicos cambios son artefactos de esta evaluación y su harness. Los lanzadores invocan los scripts X11 con bash porque el volumen NTFS no conserva el bit ejecutable. El holdout visual usa un presupuesto de salida de 512 tokens para que el modelo pueda cerrar la respuesta estructurada. No se editaron perfiles de producción, HarnessSpec, C++/QML/core ni defaults. No se corrieron build ni tests del producto porque no hubo cambios de producto.

Recibos de cierre y comparación: [resumen estructurado](receipts/evaluation-summary.json), [limpieza de sesión](receipts/session-cleanup.json), [manifiesto de modelos/runtime](receipts/model-source-manifest.json) y [preflight de reanudación](receipts/resume-preflight.json).
