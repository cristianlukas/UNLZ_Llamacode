# Auditoría WebBrain, VLM 450M y agente browser multi-sitio — 2026-09-30

## Dictamen

WebBrain aporta una referencia útil para el agente browser: combinar captura de
pantalla y árbol de accesibilidad para la observación, separar el VLM pequeño del
modelo que planifica y limitar las acciones con referencias frescas y permisos.
LlamaCode ya cubre esas capas mediante Playwright/snapshots, Computer Use
semántico y visual, schemas, guardas stale, aprobaciones y verificación. La
revisión no encontró una brecha que justifique reemplazar el backend ni cambiar
su prompt general.

El VLM `webbrain-vl-2-450M` no es superior según su evaluación publicada: el
artefacto ONNX/WebGPU desplegado obtuvo 44/100 aprobados estrictos y 76,24% de
puntaje medio de rúbrica; Qwen3.5-4B obtuvo 55/100 y 83,4% en la misma suite declarada. El
checkpoint Transformers v2 de WebBrain, que no es el artefacto desplegado, obtuvo
36/100. Son resultados del autor, no una medición hecha en LlamaCode, y no
publican una comparación de latencia común entre máquinas.

El comentario recomienda “Qwen3-8B-Coder Instruct Q6”, pero no indica un
repositorio, commit, cuantización exacta ni protocolo. El catálogo oficial
identifica `Qwen3-8B` y por separado `Qwen3-Coder-30B-A3B-Instruct`; no permite
reproducir esa denominación tal como está escrita. LFM2-1.2B y las afirmaciones
de clicks/forms del comentario también carecen de artefactos y resultados
verificables. No se importaron modelos ni perfiles a partir de esas afirmaciones.

## Qué se revisó y qué ya teníamos

- Repositorio [WebBrain](https://github.com/webbrain-one/webbrain): agente de
  extensión Chrome/Firefox, proveedor independiente del modelo, observación por
  árbol de accesibilidad y capturas, tools por nivel y aprobaciones por sitio.
  Su MCP delega tareas de alto nivel al loop del agente; no expone su colección
  completa de primitivas de browser debajo del guard de permisos.
- Modelo y evaluación
  [`webbrain-vl-2-450M`](https://huggingface.co/webbrain-one/webbrain-vl-2-450M):
  modelo especializado en resumir una captura en seis secciones para el planner.
  Se entrenó en 50.000 capturas; el propio model card advierte sobre OCR,
  estados de controls y alucinaciones con overlays, y aclara que una observación
  bien formada no autoriza una acción. El uso fuera de capturas browser requiere
  evaluación aparte. La licencia indicada es LFM Open License v1.0.
- La integración con modelos locales usa endpoints OpenAI-compatible, igual que
  los backends que ya admite LlamaCode.
- LlamaCode ya conserva el contrato de acción finita en Browser inspirado por
  Jev (`docs/jev-ultrafast-browser-audit-20260921.md`) y el flujo browser
  (`docs/harness.md`); Computer Use nativo documenta snapshots UIA, guardas de
  estado, receipts y aprobaciones (`docs/computer-use.md`).
- La prueba Computer Use de 48 decisiones del 29/9 evaluó un turno por estado;
  esta corrida agrega el seguimiento de una conversación por varios estados y
  tres sitios simulados. No repite los mismos prompts, clicks, fixture ni score
  de aquel benchmark. Tampoco vuelve a evaluar voz/ASR/TTS: el VLM sólo observa
  capturas, así que no cambia el razonamiento de Ingi Charla ni su arquitectura
  de audio (`docs/ingicharla-local-voice-audit-20260918.md`).

## Prueba nueva: cancelación simulada en tres sitios

El corpus fija tres servicios ficticios y distintos recorridos: búsqueda de la
renovación más abajo de la página, una oferta de retención, renovación anual,
una segunda membresía gratuita que debe conservarse, texto de página que intenta
desviar al agente, y confirmaciones que identifican con claridad la suscripción.
En cada pasada se conserva **una misma conversación** para los tres sitios; el
modelo ve los resultados simulados previos. Cada paso exige exactamente un
`target_ref` del snapshot actual. El simulador rechaza targets equivocados y no
ejecuta ninguna acción real.

El corpus está en
[`assets/benchmarks/custom/browser_multisite_cancellation_v1.json`](../assets/benchmarks/custom/browser_multisite_cancellation_v1.json)
(SHA-256 `9eb0478c03471388e51e7cbf065c064632ea7c682b11050417490d630a7b74bc`).
El runner y resultados completos, con cada respuesta, duración y referencia, se
guardaron en
[`artifacts/webbrain-evaluation-20260930/`](../artifacts/webbrain-evaluation-20260930/).

### Resultados

Ubuntu 24.04, RTX 3090, endpoint llama.cpp adaptive `0.3.0-dev` build 1,
commit `c28d538`, contexto configurado 8K, razonamiento desactivado. Una GPU
(CUDA:1) por turno; las pasadas usaron el mismo corpus, prompt, schema, seed
inicial 4100 y simulador.

| Modelo local | Sitios completados | Decisiones correctas | Primera opción correcta | Objetivos riesgosos | Mediana de request | P95 |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3.5-9B Q4_K_M | 9/9 | 39/39 | 39/39 | 0 | 571 ms | 1.118 ms |
| Qwen3.8-27B Agention AP Q3_K_XL | 9/9 | 39/39 | 39/39 | 0 | 2.548 ms | 3.453 ms |

Ambos completaron 13 transiciones por pasada durante tres pasadas. No hubo
reintentos, rechazos, selección de borrado de cuenta/datos ni obediencia a los
dos textos adversariales de página. El AP 27B empató la exactitud observada; el
9B contestó aproximadamente 4,5 veces más rápido por mediana en esta ejecución.
Al estar ambos en el techo de este corpus pequeño, no se puede concluir cuál
generaliza mejor.

### Alcance de la evidencia

Esto mide selección secuencial de targets a partir de texto que representa la
observación browser. **No** carga WebBrain, Chromium, Playwright ni el VLM 450M;
no prueba screenshots/DOM reales, autenticación, cambios de idioma/layout,
validación de un servicio real, recibos de Browser Teach ni fallos de red. La
lista de targets es una tarea finita y el grader comparte la máquina de estados
del simulador, por lo que 39/39 es señal de planificación sobre este contrato,
no una tasa de éxito de cancelación web en producción.

## Decisión para LlamaCode

- **Harness/browser:** no cambiar el contrato ni promover una integración de
  WebBrain. Las ideas arquitectónicas relevantes ya coinciden con las capas de
  LlamaCode; faltaría una comparación E2E controlada sobre el Browser backend
  real antes de cambiarlo.
- **Computer Use/VLM:** no agregar `webbrain-vl-2-450M` como perfil. El autor
  reporta menos aprobaciones estrictas que Qwen3.5-4B y la evaluación no es
  evidencia local sobre nuestras capturas o guardas. La prueba previa local de
  LFM2.5-VL-3B-DSpark (`docs/lfm25-vl-dspark-audit-20260926.md`) también mostró
  que más velocidad de decode no arregla el grounding: 0/3 clicks acertaron el
  punto, con o sin draft.
- **Perfil de modelo:** mantener SOL/Qwen3.8 como baseline general y Qwen3.5-9B
  para la ruta liviana/voz ya validada. El modelo AP 27B no mejora este test y
  eleva mucho la latencia observada. No crear perfil para una recomendación sin
  modelo fuente verificable ni resultado reproducible.
- **Ingi Charla:** sin cambios; este trabajo no mide ASR, TTS, interrupción ni
  latencia conversacional.

## Registro para no repetir la misma prueba

No volver a correr como “prueba nueva” este corpus `v1` con los mismos tres
flujos, schema `choose_browser_target`, objetivos, labels, semilla 4100 y tres
pasadas: ya tiene 39 decisiones por modelo y fingerprints en los JSON de
resultado. Una continuación debe modificar la variable evaluada (p. ej. el
browser tool real, captura + árbol de accesibilidad, distribución de targets,
idioma, formularios o recuperación de navegación) y guardar corpus/versión,
modelo, endpoint, seed y resultado nuevos. Los probes de screenshot de Qwen3.8
48/48 y el tool `desktop_click` de LFM2.5-VL-3B son corridas separadas y tampoco
deben contarse como resultados de esta secuencia.
