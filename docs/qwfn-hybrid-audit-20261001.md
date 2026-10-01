# Auditoría de QwFN-hybrid para LlamaCode — 2026-10-01

## Decisión

**No cambiar perfiles, harness, Computer Use ni Ingi Charla.** QwFN-hybrid merece quedar registrado como runtime experimental para probar en máquinas con poca RAM y una GPU de 16 GB, pero en esta notebook no supera a `llama.cpp` en decode corto, no mantiene una latencia competitiva en Computer Use y obtuvo 2/8 en BCB-Hard. Sus ventajas locales en prefill largo y la cercanía numérica no compensan esos resultados.

No cambié perfiles ni código de LlamaCode. La configuración especial QwFN requiere su propio fork/engine, limita explícitamente la caché a 19 GiB de RAM y 12 GiB de VRAM, y depende de NVIDIA/CUDA; no es un preset de `llama.cpp` portable al catálogo de perfiles.

## Qué dice el post y qué implementa

El post compartido informa RTX 5060 Ti de 16 GB, 32 GB DDR5 y expertos distribuidos entre VRAM, RAM y NVMe. Publica 26,4 tok/s en código, 21,3 en agente, 21,8 en razonamiento, 17,7 a 21K; y 620 tok/s de prefill a 16K frente a 165 con llama.cpp. También indica que su release pasa 4/5 gates de paridad: el gate principal de razonamiento falla NLL shift (0,0031 frente a 0,0021); una repetición de 3.000 tokens entra en el límite.

El [README de QwFN-hybrid](https://github.com/thomaskleiven/QwFN-hybrid) describe un motor basado en ggml/llama.cpp, con cambios sustanciales para ubicar expertos por tier, hacer prelectura y usar snapshots/MTP. No se integra directamente como perfil upstream. El quant exacto, [GSQ-RCO IQ3_XXS](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF), ocupa 70,62 GiB en dos shards; el head [MTP Q8 compartido](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/tree/main/MTP) ocupa ~2,6 GiB. El [modelo oficial de Qwen](https://github.com/QwenLM/Qwen3.8-Flash-Next) confirma la arquitectura base. El fork tiene una API OpenAI/Anthropic y recepción de imagen, pero no implementa entrada de audio ni ejecución de escritorio.

## Validación local nueva

La prueba usó el modelo/quant y head MTP publicados. Compilé y ejecuté QwFN commit `6b26989f8a2bdefd6c541ba0d0586c80b9e3b011` y el `llama.cpp` upstream limpio, ambos basados en `ca1426903fabe9af26cd10c42034cb4bbd2e0e11`. El build QwFN pasó su `scripts/check_rules.sh` con warnings como errores. Equipo local: 2× RTX 3090 24 GiB y 123 GiB RAM; throughput comparativo limitado a una GPU. Los artefactos están en [`artifacts/qwfn-hybrid-evaluation-20261001/summary.json`](../artifacts/qwfn-hybrid-evaluation-20261001/summary.json).

| Prueba | Resultado | Referencia local / gate | Interpretación |
|---|---:|---:|---|
| BCB-Hard | 2/8; transporte 8/8 | Swift previo 1/8 en una corrida; no alcanza evidencia de mejora | Diferencia de un caso no es suficiente para promover |
| Contrato de tools | 5/5 | Swift previo 5/5 | Empate funcional; QwFN tarda más |
| Computer Use | 72/72 correctas, schemas/seguridad/transporte 100% | Swift previo 240/240 y p50 ~0,63–0,80 s | QwFN queda en p50 4,70–6,16 s y falla el gate de latencia; una repetición frente a cuatro previas |
| Acción visual `desktop_control_action` | 3/3 correctas | Otro quant Qwen previo 3/3; p50 ~0,98 s tras warmup | QwFN p50 25,27 s; no es competitiva. No se ejecutó la acción en el escritorio |
| Replay numérico, code/agent/reasoning | NLL shift −0,00083 / −0,00038 / −0,00024; KL top-k 0,000218 / 0,000873 / 0,001626; argmax 99,5% / 99,5% / 99,0% | Tres traces; 800/800/600 tokens, una repetición cada uno | Distribuciones cercanas en estos traces. No es el gate de paridad completo ni evalúa calidad funcional |
| Prefill/decode | QwFN gana prefill de 16K, pierde prefill 512 y decode a ambas profundidades | Bench oficial del fork, quant idéntica; config de memoria distinta | Ver tabla detallada debajo; no se promueve por throughput |
| Ingi Charla / voz | Sin prueba de audio | El servidor no acepta audio | No puede reemplazar el pipeline STT → LLM → TTS |

El [reporte de throughput](../artifacts/qwfn-hybrid-evaluation-20261001/throughput/README.md) contiene los valores exactos, configuración, repeticiones y logs. En pp512 QwFN dio 32,2–39,5 tok/s (MTP: 38,8–39,3) frente a llama.cpp 186,37; en decode corto dio 11,55–11,97 (MTP 12,86–12,99) frente a 19,11. En pp16K QwFN sin MTP dio 606,9–718,3 frente a 182,74, pero a profundidad 16K el decode fue 7,21–7,73 frente a 18,59. Con MTP hubo variación amplia en 16K (decode 1,77 y 9,38; la corrida lenta leyó expertos a 0,27 GB/s). El upstream pudo aprovechar page cache por encima de los 19 GiB explícitos de QwFN; por eso esta comparación no representa igualdad de RAM disponible, y las métricas se reportan con sus configuraciones, no como un ranking universal.

La fidelidad numérica es alentadora en los tres traces locales, pero el candidato no ha completado la campaña publicada de cinco escenarios y repeticiones/null-run. Tampoco ejecutamos HE20 a través de todo el agente LlamaCode: BCB-Hard y los traces sirven para la evaluación experimental del motor, no para afirmar que se reemplazó el harness de producción.

## Encaje por componente

| Área | Evidencia | Decisión |
|---|---|---|
| Modelo/perfil | Prefill 16K rápido; decode más lento que upstream y BCB no mejora de forma demostrada. El anfitrión tiene dos 3090 y mucha más RAM que la máquina objetivo del post. | No crear perfil de usuario. Conservar el artefacto como candidato experimental para equipos de 16 GB VRAM/32 GB RAM, con benchmark pareado nuevo en ese hardware. |
| Harness de coding | Tool schema 5/5 iguala al Swift previo; BCB-Hard 2/8 frente a 1/8 de una sola corrida anterior; no se completó HE20 end-to-end de LlamaCode. | No cambiar harness. Si se reabre la evaluación, correr primero HE0 → HE20 → BCB con la integración real, misma versión de harness y referencia apareada. |
| Computer Use | 72/72 en 1 pase, pero 4,7–6,2 s por decisión frente a 0,63–0,80 s del perfil Swift; visión correcta pero ~25 s por petición. | No seleccionar como backend Computer Use: el gate de latencia falla aunque acierte las etiquetas. Falta repetir 4× para igualar el tamaño de la muestra Swift. |
| Ingi Charla | El servidor recibe texto e imagen, sin audio; no hay WER/CER, latencia fin-habla→primer audio ni turnos de voz. | Sin cambios en STT/LLM/TTS. No inferir la latencia de voz a partir del decode de texto. |
| Backend | Linux + CUDA, engine específico; compiló y pasó reglas internas del fork. No se probó como proceso administrado por LlamaCode ni con recovery/stop del runtime de producto. | Mantener fuera de perfiles estables. |

## Historial ya evaluado; no repetir

- [Strata Qwen3.8-Flash-Next Q2_0, 2026-09-29](strata-qwen38-evaluation-20260930.md): BCB-Hard 1/8 en dos corridas con sampling conservador; needle 3/3 a 8K/32K/110K; un round-trip de tool. No hizo Computer Use ni audio. No repetir esa matriz con Q2_0.
- [Flash-Next frente a SOL, 2026-09-19](flash-next-vs-sol-iterative-audit-20260919.md): IQ1_S, IQ4_XS y EXL3 no superaron calidad agentiva validada de SOL (BCB 8/8, HE20 20/20 y tool-use estable).
- [Qwen3.8 GSQ-RCO + DFlash2, 2026-09-18](qwen38-gsq-rco-dflash2-q2-audit-20260918.md): DFlash2 mejoró decode, pero no completó LC-H1.
- [Ingi Charla, 2026-09-18](ingicharla-local-voice-audit-20260918.md): pipeline actual separado en STT/LLM/TTS; QwFN no se probó con audio.
- Las evaluaciones previas de [Computer Use](computer-use-sandwich.md) separan exactitud, validez, seguridad, transporte y latencia. Swift tuvo 240 requests con 100% en esos criterios funcionales; QwFN tuvo 72 en este test nuevo.

## Registro para no repetir exactamente

No volver a ejecutar como campaña nueva sobre el mismo candidato y host:

1. BCB-Hard-8 usando `run_bcb.py`, `--budget 2048 --max-tokens 6144`, sampling `temp=.6, top-p=.95, top-k=20, min-p=0`, thinking off: 2/8.
2. Contrato read→write, cinco pasadas, sampling determinista y thinking off: 5/5.
3. Computer Use no-thinking, seed 42, un pase, 24 casos por orden (state-first/question-first/sandwich): 72/72; gate de promoción falla sólo por latencia.
4. Captura visual Spanish settings, tres propuestas de acción: 3/3; acción nunca ejecutada.
5. Bench pp512/pp16K/tg128, misma quant, `ctx=73728`, KV Q8, QwFN con 12 GiB VRAM/19 GiB RAM/5 threads versus llama.cpp base con expertos en CPU y cache del host: resultados en `throughput/README.md` y `throughput/raw/`.
6. Replay tokenizado code/agent/reasoning, 800/800/600 tokens, KV Q8, `ubatch=1` upstream y QwFN sin MTP con 12 GiB VRAM/19 GiB RAM; una repetición. Traces, NLL, top-k y logs están en `parity/`.

Sólo repetir si cambian el engine/quant/flags o si se necesita igualar la cantidad de repeticiones (p. ej. cuatro para Computer Use). Una expansión justificada sería completar el gate de paridad de QwFN con null-run y ejecutar la campaña end-to-end integrada; no repetir un smoke ya cubierto para aumentar artificialmente el número de pruebas.

## Espacio en disco observado

La alerta adjunta era real para el volumen separado `/var/lib/containerd` (`/dev/loop25`): 63 GiB totales, 57 usados y 2,7 GiB libres al verificarlo. El volumen de modelos/repo tenía 125 GiB libres y la raíz 56 GiB; los shards se habían descargado antes de la alerta. No hice nuevas descargas ni builds después de verla. Los tests posteriores escribieron sólo JSON y logs pequeños fuera de `containerd`.
