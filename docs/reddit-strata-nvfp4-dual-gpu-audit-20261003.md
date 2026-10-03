# Auditoría del post: Qwen3.8 NVFP4 + Strata en dos GPU

Fecha: 2026-10-03  
Estado: investigación cerrada; sin descarga ni promoción local.

## Decisión

El post no demuestra una mejora aplicable a los perfiles ni harness de LlamaCode.
No se modifican ASTRA, SOL, Ingi-Charla, Computer Use, `HarnessSpec` ni los
perfiles de coding. El resultado de hasta 125 tok/s es una medición publicada
para otra PC, otro checkpoint y un fork experimental; no es comparable con
nuestros scores agentivos.

No se descargó el checkpoint NVFP4 ni se intentó compilar ese fork: el volumen
de modelos tiene 90 GB libres, mientras que el README público del fork describe
un checkpoint de 126 GiB, además de una tabla PLE de 51,2 GB y un pack de
expertos de 63 GiB. El uso pico requiere bastante más espacio que el disponible.
La computadora de este ensayo tiene 2×RTX 3090 (SM 8.6), CUDA Toolkit 12.0 y
124 GiB de RAM; el post usa RTX 4090 D + RTX 5070 Ti y 128 GB RAM. La ruta W4A8
descrita por el fork es específica de Blackwell/sm_120 y requiere CUDA 13; su
README no documenta la configuración dual GPU del post. Aunque el fork se
presenta como compatible con varias generaciones de GPU, no hay aquí una receta
verificada que permita reproducir ese resultado con nuestras dos 3090.

## Qué informa el post y qué puede concluirse

El autor reporta contexto de 262.144 tokens, KV INT8, prefill W4A8, MTP K4 y
unos 256.018 tokens de prompt. El checkpoint NVIDIA alcanza 4.112,65 tok/s de
prefill y 125,17 tok/s de decode, con 94,87% de aceptación del draft. El modelo
abliterado alcanza 4.071,39 y 92,05 tok/s, con 69,7% de aceptación. El propio
post advierte que fue una sola prueba con contexto repetido sintético; no es
una medida típica de coding agent ni una comparación contra SOL.

El fork público enlazado describe una implementación NVFP4 de Strata distinta
en varios detalles: su README identifica como checkpoint de ejemplo uno
abliterado de OrcaRouter, describe 126 GiB para la fuente, 51,2 GB para PLE y
una build medida en RTX 5090. No se debe asumir que reproduce el fork dual GPU
experimental del post ni que evalúa el checkpoint NVIDIA citado allí.

## Evidencia local ya existente — no repetir

Las siguientes pruebas responden a preguntas cercanas y no necesitan repetirse
para decidir sobre este post:

| Ruta | Evidencia guardada | Resultado relevante |
|---|---|---|
| ASTRA IQ3_S / Qwen3.8 Flash-Next, coding directo | [`strata-v0135-vs-sol-astra-audit-20261002.md`](strata-v0135-vs-sol-astra-audit-20261002.md) | BCB-Hard 1/8 en la primera evaluación; no supera el baseline de 8/8. |
| ASTRA IQ3_S vs SOL y Swift, loop LC-H1 | [`strata-swift-vs-sol-lch1-20261003.md`](strata-swift-vs-sol-lch1-20261003.md) | ASTRA termina 38/38 tras reparaciones, iguala Swift y tarda 20% más que SOL. Una pasada por candidato; no promover por una diferencia pequeña. |
| Computer Use, decisiones y seguridad | El audit anterior de Strata y `artifacts/strata-v0135-vs-sol-astra-20261002/computer-use-hard-thinking-off.json` | 72/72 decisiones y 63/63 decisiones seguras: empate con Qwen3.8-27B Q6; no mide ejecución real de GUI ni NVFP4. |
| Ingi-Charla | [`ingicharla-local-voice-audit-20260918.md`](ingicharla-local-voice-audit-20260918.md) | Strata no es STT/TTS y no se probó voz-a-voz; las suites agentivas no miden ASR, TTS ni latencia acústica. |
| Contexto, MTP y PLE del setup Strata local | `artifacts/strata-post-evaluation-20261003/ple_io_measurements.json` | Medición de calibración local de I/O PLE; no evalúa NVFP4, calidad agentiva ni sustituye el A/B del post. |

Las pruebas anteriores usan IQ3_S/Swift y runtimes distintos de NVFP4. Sirven
para conservar el estado de ASTRA y evitar repetir suites completas sin
necesidad; no permiten atribuirle al NVFP4 sus resultados.

## Condiciones para una nueva evaluación

Reabrir sólo cuando haya espacio rápido suficiente para el checkpoint y los
artefactos intermedios, un fork/configuración dual que declare soporte para
SM 8.6 y una receta reproducible del checkpoint NVIDIA original. Entonces:

1. Guardar commit/hash del engine, revisión y hashes del modelo, config y prompts.
2. Hacer primero un smoke de carga, API, salida válida, MTP y estabilidad; medir
   PP/TG, TTFT, aceptación MTP, VRAM por GPU, RAM y latencia de disco.
3. Comparar contra SOL y ASTRA bajo el mismo harness, paquete LC-H1 y límites de
   reparación; repetir los casos que decidan promoción con semillas fijadas.
4. Para Computer Use, correr el corpus de decisiones y una prueba E2E separada
   sobre escritorio. Para Ingi-Charla, exigir un corpus acústico en español y
   medir WER/CER, fin-de-habla→transcripción y fin-de-habla→primer audio; la
   velocidad de generación sola no justifica cambios de voz.
5. Promover sólo el perfil/modelo que gane una comparación pareada de calidad y
   latencia. Mantener el throughput del post como referencia externa hasta que
   exista un recibo local equivalente.

Fuentes:

- [Post de Reddit con los resultados y la configuración](https://www.reddit.com/r/LocalLLM/comments/1wwceh8/qwen38flashnext_nvfp4_at_256k_context_with_strata/)
- [Fork Strata NVFP4 enlazado en los comentarios](https://github.com/sergqwer/strata-nvfp4)
- [Strata upstream](https://github.com/Niko1221/Strata)
- [Model card NVIDIA Qwen3.8-Flash-Next NVFP4](https://huggingface.co/nvidia/Qwen3.8-Flash-Next-NVFP4)
