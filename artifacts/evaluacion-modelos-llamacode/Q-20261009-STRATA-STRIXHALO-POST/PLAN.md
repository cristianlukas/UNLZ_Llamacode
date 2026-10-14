# Evaluación de la señal Strix Halo en el hilo de Strata

- **ID:** `Q-20261009-STRATA-STRIXHALO-POST`
- **Lock:** `7fb76834-11ad-4dfc-909c-4fe3cbb162d0`, iniciado 2026-10-13T04:00:00Z; cerrado tras auditoría documental.
- **Objetivo:** verificar el comentario sobre Strix Halo/Ryzen AI Max en el hilo de r/LocalLLM y decidir si la señal aporta a modelos, perfiles o harness de LlamaCode, especialmente rendimiento sostenido y contexto.
- **Fuente primaria:** [hilo r/LocalLLM “Strata takes the promise…”](https://www.reddit.com/r/LocalLLM/comments/1wx3g89/strata_takes_the_promise_of_moe_models_just_need/). El comentario citado por el material pegado dice: “I have a 5070 and a strix halo. I just the largest quant with highs in the 50s never falling below 35 tok/sec for 515 minutes. It’s absurdly consistent. I’m about to audit the .json for the session…”. No especifica qué quant, el modelo, contexto, si RTX 5070 y Strix Halo corrieron simultáneamente, configuración de MTP, duración exacta de inferencia, ni comparte el JSON en el material.

## Candidatos, controles y alcance

- Candidato externo: Strata en un Strix Halo/Ryzen AI Max, más una RTX 5070 según el comentario. Modelo/quant y distribución del trabajo entre ambos dispositivos no especificados.
- Contexto del post padre: Qwen3.8-Flash-Next Q4, KV q8, contexto configurado a 262K en cuatro P100. No atribuir esas especificaciones al comentario Strix Halo sin evidencia.
- Control local: resultados existentes para Flash-Next/Strata y las auditorías locales de contexto; sólo evidencia contextual. No forman un A/B con Strix Halo por diferencias de GPU, memoria unificada, quant y configuración.
- Revisado el hilo, Strata `docs/STRIX_HALO.md`, el benchmark comunitario publicado por Strata y la ficha oficial Qwen. El comentario no aporta quant/config ni el JSON; el informe medido de Strata sí detalla UD-IQ4_XS sobre gfx1151, pero sólo probó prompts hasta 131.072 tokens.

## Pruebas condicionales

- No descargar modelos ni iniciar GPU antes de identificar un modelo/quant y configuración reproducibles, revisar los fingerprints existentes y confirmar hardware/runtime compatibles.
- Un A/B de rendimiento sólo sería directo en un Strix Halo con el mismo modelo, quant, contexto efectivo, KV, runtime/build, sampling y carga; registrar TTFT/prefill/decode, telemetría, throttling y temperatura durante una ventana equivalente.
- Para valorar contexto 1M hacen falta prompt y datos de 1M realmente procesados, posiciones sembradas, recuperación verificable, uso de RAM/VRAM y una respuesta de contenido; `max-context=1M` o RoPE scaling no cuentan como recuperación efectiva.
- Sin hardware Strix Halo local o sin recibo/config completo del autor, cerrar como auditoría documental. No promover por velocidad, estabilidad subjetiva o contexto configurado.

## Recursos y seguridad

- GPU visible en este host: 2× RTX 3090; CPU Ryzen 9 9950X3D; hay un controlador AMD `1002:13c0`, sin confirmación de Strix Halo/gfx1151. No se usó GPU para intentar emular una topología de memoria distinta.
- Resultado: auditoría documental cerrada. No se validó 1M en el hardware citado, no hay A/B local compatible y no se cambia perfil/contexto. Informe y recibos en este directorio.
