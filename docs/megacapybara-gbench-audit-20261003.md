# MegaCapybara y G.bench — evaluación de aplicabilidad, 2026-10-03

## Veredicto

No hay una mejora verificable que incorporar hoy a los perfiles, al harness,
a Ingi-Charla ni a Computer Use. No se cambió ningún perfil o default y no se
inició una descarga de pesos ni se ejecutó un binario del proyecto externo.

La comparación del motor no es ejecutable de forma válida en este equipo: la
publicación requiere una RTX 5090 y entrega pesos `.megacapibara` para un runtime
propietario. Este checkout tiene Ubuntu 24.04 (glibc 2.39), dos RTX 3090 de
24 GiB, 123 GiB de RAM y driver 610.57.04. Aunque el sistema operativo cumple
la condición Linux publicada, no cumple el requisito de GPU ni permite probar
el formato de pesos con los runtimes locales. El repositorio upstream confirma
que su fuente aún no está publicada; los enlaces de source code de GitHub son
sólo la instantánea documental. Descargar el paquete Linux (~11,5 MB) o pesos
de 12,7–23,6 GiB no produciría una comparación representativa en esta máquina.

## Lectura de las afirmaciones

MegaCapybara anuncia hasta 540 tok/s en un stream y 1.890 tok/s agregados con
ocho streams para su modelo Tiny. La propia tabla acota la medición a RTX 5090
con overclock de memoria de +20%, greedy decoding y thinking desactivado. La
publicación presenta cinco quants MXFP4/MXFP6 propios, el drafter DFlash2,
confidence scheduling inspirado en DSpark y una piscina de contexto compartida.
Reporta acuerdo top-1 y KL contra Qwen3.8 BF16 sobre 81.880 tokens para
caracterizar fidelidad de quant; esas métricas no sustituyen pruebas agentivas
de calidad, tool-use o visión. Los comentarios del hilo expresan dudas sobre
métricas y código cerrado, pero no aportan una reproducción que refute los
números.

No se trasladan los tok/s a SOL ni a NInfer-3090: son GPUs, kernels, formato de
pesos, condición de reloj, carga y métrica distintos. Tampoco se importa el
algoritmo de cache/scheduler a una preferencia de perfil: gestiona memoria y
batching dentro del motor, una capa que LlamaCode no controla al conectarse a
vLLM/NInfer.

## Qué sí encaja con LlamaCode

| Idea | Estado local y decisión |
|---|---|
| Comparar fidelidad de quant frente a BF16 con acuerdo top-1/KL | El [manual de benchmarking](benchmark-manual.md) ya especifica replay teacher-forced, NLL, KL top-k y acuerdo top-1, además de advertir que esto no acredita calidad agentiva. No añadir otra prueba de quant hasta tener el artefacto y la referencia BF16 accesibles en hardware compatible. |
| Separar decode, prefill, TTFT, contexto y concurrencia | Ya se miden por separado; el manual registra PP/TG, cold/warm y concurrencia agregada. Las campañas previas incluyen NInfer en una RTX 3090 y SOL/DFlash2 en 2× RTX 3090. |
| Cache de prefijo y carga caliente | Ya existe una evaluación cold/warm; no combinarla con latencia de prompt frío. La medida de G.bench favorece explícitamente prefix reuse, por lo que sólo sirve como categoría warm-cache. |
| Pool compartido, desalojo y reanudación RAM/disco | Requiere implementación y evidencia del motor; no se puede activar con una receta OpenAI-compatible ni inferir desde un pico de throughput. No cambiar concurrencia local. |
| Loop guard que aumenta repetición hasta detener | Sin fuente ni protocolo reproducible para verificar falsos positivos, impacto en distribución o la señal de detención. No copiarlo a sampling/harness. |
| Quant MXFP4/MXFP6 y kernels SM120 | Formato y optimización declarados para RTX 5090. No son intercambiables con GGUF, NInfer SM86 o los pesos de SOL. |
| APIs OpenAI/Anthropic, tools e imágenes | Podría ser un endpoint para un cliente, pero no demuestra compatibilidad con el HarnessSpec, seguridad/confirmación de tools ni control de escritorio de LlamaCode. No se ejecutaron pruebas de contrato. |
| Ingi-Charla / audio | La documentación sólo anuncia texto, tools, thinking e imágenes; no presenta endpoints STT/TTS ni evaluación ASR/audio. Sin motivo para descargar o cambiar motores de voz. |

## G.bench (Sectile Research Laboratories)

La página abierta es G.bench, una tabla de resultados de **GInfer Standard
Benchmark** para GChat. No es un benchmark de calidad de modelos tipo coding ni
una suite de Computer Use. La tabla separa prefill frío, PP, TG agregado y TG
por request, y asocia concurrencia con GPU, modelo, engine, sistema operativo y
telemetría opcional de reloj, potencia, temperatura y throttling. Esa separación
es útil al reportar throughput concurrente.

La página describe su prueba como un prompt repetido que ejercita KV, prefix
cache, DFlash y kernels afinados; aclara que favorece la reutilización de
prefijo y **no** representa prompt frío ni carga de producción mixta. También
dice que los resultados son reportados por la comunidad y no verificados de
forma independiente, y que publicar es opt-in. En LlamaCode ya se guardan
métricas diferenciadas de prompt, generación y concurrencia, junto con
configuración de máquina y comando efectivo; no se adoptan las cifras ni el
runner GInfer.

## Pruebas locales previas que no se repiten

- [NInfer Windows/RTX 5090 vs evidencia local](ninfer-5090-windows-post-audit-20260918.md): el port SM120 no se traslada a las RTX 3090; NInfer-3090 ya fue evaluado localmente y no reemplaza SOL por calidad.
- [NInfer-3090 en Ubuntu](ninfer-3090-linux-evaluation-20260908.md): genera y atiende concurrencia corta, pero obtuvo BCB 3/8; es experimental.
- [SOL + DFlash2](sol-dflash2-local-audit-20260918.md): el decode subió frente a controles locales, pero la calidad estructurada/harness no superó a SOL y quedan fallos xgrammar.
- [SOL, Swift y ASTRA con LC-H1](strata-swift-vs-sol-lch1-20261003.md): comparación reciente de HE20, BCB8 y adversarial en este host; no es una prueba de MegaCapybara ni de G.bench.

No se vuelven a ejecutar estas mismas suites/perfiles para concluir sobre un
runtime que no se puede arrancar aquí. Tampoco se consideran los comentarios de
Reddit como una medición local.

## Condiciones para reabrir

Repetir la evaluación si se dispone de una RTX 5090 compatible y se cumple al
menos una de estas condiciones: se publica el código para auditar el motor, o
se obtiene una build cuyo binario y procedencia puedan revisarse y aprobarse en
el entorno de prueba. Congelar clocks/power y registrar si hay overclock; correr
el mismo workload en MegaCapybara y SOL/NInfer, distinguiendo cold PP, warm PP,
TG por request, TG agregado y concurrencia; después comparar calidad con el
mismo prompt/harness, tools, thinking, sampling y graders. La promoción requiere
superar las gates agentivas de LlamaCode; el throughput aislado no basta.

G.bench sólo amerita una prueba separada cuando exista una build/hardware
compatible de GInfer/GChat. Su workload warm-prefix no debe mezclarse con los
resultados cold-cache de LlamaCode.

## Fuentes

- [MegaCapybara: README y requisitos](https://github.com/perkel666/MegaCapybara)
- [MegaCapybara v1.04 y detalles del release](https://github.com/perkel666/MegaCapybara/releases/tag/v1.04)
- [Modelo MegaCapybara Qwen3.8-27B](https://huggingface.co/perkel/Qwen3.8-27B-MC)
- Publicación y comentarios de LocalLLaMA suministrados en el adjunto del usuario (el texto pegado no conserva el permalink).
- [G.bench — Sectile Research Laboratories](https://sectilelabs.ai/gbench/)
