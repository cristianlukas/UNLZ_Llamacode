# Revisión de recomendaciones de modelos locales — 2026-10-03

## Alcance

Se revisó el texto pegado sobre Qwen3.8-27B, Qwen3.8-Flash-Next, Strata,
NInfer y rendimiento de modelos agentivos contra la máquina local: Ryzen 9
9950X3D, 124 GiB RAM y 2× RTX 3090 de 24 GiB (48 GiB VRAM total). La referencia
describe experiencias de terceros con GPUs, cuantizaciones, runtimes y tareas
distintos; sus tok/s no son una predicción válida para este equipo.

La documentación oficial confirma que Strata sirve Qwen3.8-Flash-Next y
Swift 1.5 mediante una API local, y que NInfer mantiene rutas especializadas
para Qwen3.8-27B y decodificación especulativa. Ninguna de esas descripciones
reemplaza una comparación de calidad con nuestro harness:
[Strata](https://github.com/Niko1221/Strata),
[Qwen3.8-Flash-Next](https://github.com/QwenLM/Qwen3.8-Flash-Next),
[NInfer: rendimiento Qwen3.8-27B](https://github.com/Neroued/ninfer/blob/master/docs/performance/qwen3.8-27b.md).

## Evidencia local existente

No se descargaron pesos ni se repitieron corridas: los experimentos relevantes
ya están guardados con sus entradas y recibos.

| Pregunta | Evidencia local | Lectura para este equipo |
|---|---|---|
| ¿Flash-Next/Strata supera a 27B para coding? | En la comparación LC-H1 del 3/10, SOL terminó 37/38, Swift 1.5 38/38 y ASTRA/Strata IQ3_S 38/38 tras reparaciones. Tiempos: SOL 1.534 s, ASTRA 1.841 s, Swift 2.196 s. En BCB8, SOL logró 7/8 final, Swift y ASTRA 8/8; los tres necesitaron reparaciones. | No hay superioridad robusta que justifique cambiar SOL: ganó en tiempo total y la diferencia de una tarea final no tuvo repetición entre semillas. ASTRA queda como alternativa experimental. |
| ¿Los números comunitarios de Flash-Next aplican acá? | La auditoría 0.1.35 midió Qwen Flash-Next IQ3_S; una prueba directa aislada dio 1/8 BCB. La comparación agentiva posterior obtuvo 38/38 tras reparación, pero tomó 20% más que SOL. El informe de Swift 1.5 midió otro quant/modelo y tampoco fue más rápido en el total LC-H1. | Las cifras de Strata publicadas y los resultados de calidad dependen de quant, runtime y harness. No extrapolar decodificación de otro equipo ni tratar IQ3_S, IQ3_XXS y Q4 como equivalentes. |
| ¿Mejora Computer Use? | Swift Genesis NVFP4 obtuvo 100% en 48 decisiones × 5 pasadas, incluidos casos de seguridad, pero no pasó la compuerta de latencia entre órdenes de prompt. ASTRA IQ3_S obtuvo 72/72 y 63/63 en las tres variantes, igual que el control histórico Qwen3.8-27B Q6; esa suite evalúa decisiones textuales, no control visual real. | Empate de exactitud; no hay motivo probado para cambiar el prompt o el motor productivo. Ninguno de estos resultados demuestra interacción de escritorio E2E. |
| ¿Sirve para Ingi-Charla? | Las auditorías de Strata evaluaron texto, tools y visión; no ASR, TTS ni voz-a-voz. Ingi-Charla usa componentes STT/TTS locales separados. | Sin evidencia aplicable; no alterar perfil de voz por una comparación de LLM textual. |
| ¿NInfer mejora el perfil de 27B en nuestras GPU? | El port local SM86 de RTX 3090 generó 73–75 tok/s a 8K y 50–63 tok/s a 80–120K, pero obtuvo BCB 3/8. El artefacto actual que incorpora DFlash2 no carga con ese runtime. El informe de 5090/NVFP4 corresponde a Blackwell, no a estas RTX 3090. | NInfer-3090 sigue experimental. No descargar el artefacto Blackwell ni aplicar sus flags/quant a SM86. |

## Decisión

- Conservar SOL como perfil principal para coding y el harness; no cambiar sus
  sampling, concurrencia, contexto ni plantilla a partir del post.
- Conservar ASTRA/Strata IQ3_S como perfil alternativo local ya integrado; usarlo
  cuando la prioridad sea probar Flash-Next o su capacidad de contexto, aceptando
  el coste de latencia observado.
- Mantener los perfiles Genesis y NInfer en evaluación/manuales. Sus resultados
  no justifican convertirlos en defaults.
- No modificar Ingi-Charla ni el motor general de Computer Use. La suite de
  decisiones y las pruebas E2E de desktop miden propiedades distintas.

## Registro para no repetir

- **No repetir** LC-H1 SOL/Swift 1.5/ASTRA IQ3_S con las mismas suites, seed 4242,
  `HarnessSpec` `sha256:cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`
  y una pasada: recibos en
  [`artifacts/strata-swift-vs-sol-lch1-20261003`](../artifacts/strata-swift-vs-sol-lch1-20261003/).
- **No repetir** Strata 0.1.35 IQ3_S BCB8 ni Computer Use hard prompt-order:
  [`docs/strata-v0135-vs-sol-astra-audit-20261002.md`](strata-v0135-vs-sol-astra-audit-20261002.md)
  y sus recibos en `artifacts/strata-v0135-vs-sol-astra-20261002/`.
- **No repetir** Swift Genesis tool contract ni las 720 decisiones de Computer
  Use: recibos `tool_contract_64k.json` y `computer_use_64k.json` en
  [`artifacts/swift-genesis-evaluation-20260929`](../artifacts/swift-genesis-evaluation-20260929/).
  Swift Genesis no es Swift 1.5; ver
  [`docs/swift-genesis-qwen38-evaluation-20260929.md`](swift-genesis-qwen38-evaluation-20260929.md).
- **No repetir** NInfer-3090 Qwen3.8 hasta que se publique un artefacto/rutime
  SM86 compatible con DFlash2 o una versión del motor que cargue el artefacto
  actual: [`docs/ninfer-3090-linux-evaluation-20260908.md`](ninfer-3090-linux-evaluation-20260908.md).

Una nueva campaña sólo aporta evidencia si cambia un factor concreto (modelo o
quant distinto, runtime compatible nuevo, harness/suite actualizado, semilla
adicional para resolver la diferencia de una tarea, o una tarea E2E de desktop
real). No inferir voz, seguridad visual ni superioridad general desde estas
comparaciones de texto.
