# Resultados — Q-20261009-STRATA-NVFP4-POST

- **Estado:** completa como auditoría documental; sin nueva corrida local.
- **Fecha de cierre:** 2026-10-12.
- **Lock:** `b960e546-450c-4418-b633-30f435bc8e86`.
- **Uso evaluado:** coding/agentes, Computer Usage, visión, contexto y rendimiento.

## Qué afirma la publicación

El post describe una sola corrida de capacidad con Strata 0.1.35 y un fork NVFP4
experimental: RTX 4090 D de 48 GB más RTX 5070 Ti de 16 GB, 128 GB de RAM,
contexto 262.144, prompt de 256.018 tokens, KV int8, prefill W4A8, MTP K4 y sin
reutilización de prefijo. Reporta 4.112,65 tok/s de prefill y 125,17 tok/s de
decode para NVIDIA NVFP4; para el checkpoint abliterated, 4.071,39 y 92,05
tok/s, con aceptación de drafts 94,87% y 69,7%, respectivamente. El autor
advierte que el prompt repetía material de revisión de código, favoreciendo la
localidad y MTP, y presenta 125 tok/s como mejor caso sintético; los workloads
de agente reales variaron aproximadamente entre 108–144 y 105–145 tok/s.

Fuente: [post de r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1wwceh8/qwen38flashnext_nvfp4_at_256k_context_with_strata/).

## Identidad del modelo y transferencia

La publicación compara **NVIDIA NVFP4** con una variante abliterated. La prueba
local del 2026-10-05 usó específicamente **OrcaRouter Qwen3.8-Flash-Next
Uncensored ModelOpt NVFP4**, revisión `f24d2b68ff2814f24455ae86717be276619b5664`;
no fue el checkpoint NVIDIA que obtuvo la mayor cifra de decode. Ya se habían
verificado tensores NVFP4/escalas y se habían guardado los pesos y recibos: se
reutilizan, sin nueva descarga ni repetición del mismo fingerprint.

En esa corrida local, con el fork `sergqwer/strata-nvfp4` commit
`992195498c16ea2b26c08bf1ba2402291553136f` / engine 0.1.38-nvfp4.2, 2×RTX
3090, Linux/CUDA 12.0, KV int8, MTP4 y contexto 131.072, las llamadas directas
cortas de herramienta funcionaron. En LC-H1, los prefill `auto`/16K, 8K y 4K
activaron el watchdog; sólo el prefill fijo 2K permitió pasar HE0 1/1 tras una
reparación, en 355,284 s. No se ejecutaron HE20, BCB8 ni ADV; esto no es un
resultado integral de calidad ni una réplica del post. Detalle y recibos:
[`docs/strata-nvfp4-reddit-20261005.md`](../../../strata-nvfp4-reddit-20261005.md)
y [`artifacts/strata-nvfp4-reddit-20261005/`](../../../strata-nvfp4-reddit-20261005/).

La novedad posterior relevante es que el mantenedor declaró **retirado
`orca-nvfp4`**: en su tarea interactiva de Claude Code la variante hizo 10–70
pasos frente a 175 del Qwen original y produjo un resultado peor. Es evidencia
del mantenedor, no una evaluación independiente ni un benchmark de LlamaCode,
pero es una señal negativa específica para el checkpoint que evaluamos. Desde
la release `v0.1.41-nvfp4.5`, el fork usa por defecto un GPTQ del Qwen original;
una instalación Orca existente no se borra. La release `v0.1.42-nvfp4.1`
incorpora upstream Strata 0.1.42 y varios cambios, incluido dimensionamiento
de buffers de prompt para el layout usado. La `v0.1.42-nvfp4.2` posterior
añade otras variantes, pero no restaura Orca como candidato recomendado.

Fuentes primarias: [release que retira Orca](https://github.com/sergqwer/strata-nvfp4/releases/tag/v0.1.41-nvfp4.5), [release 0.1.42-nvfp4.1](https://github.com/sergqwer/strata-nvfp4/releases/tag/v0.1.42-nvfp4.1), [release 0.1.42-nvfp4.2](https://github.com/sergqwer/strata-nvfp4/releases/tag/v0.1.42-nvfp4.2), [model card del checkpoint OrcaRouter](https://huggingface.co/jpezzulli/OrcaRouter-Qwen3.8-Flash-Next-Uncensored-ModelOpt-NVFP4).

La actualización de buffers no prueba que se haya corregido el stall concreto
observado en el primer chunk del prefill batched. El build local disponible
corresponde al commit viejo; el checkout actualizado 0.1.42 no está instalado.
El `nvcc` activo reporta CUDA 12.0 y la documentación de la release presenta
su ruta Windows/CUDA 13; no hay un build Linux/CUDA compatible listo para
probar. No se compiló otro fork, no se instaló un toolchain ni se usó GPU. La
fix de buffers no basta para justificar reinstalar el checkpoint Orca ya
retirado ni para atribuirle la mejora del checkpoint NVIDIA.

## Lectura por caso de uso

- **Coding/agentes:** el post no mide calidad de coding; su flujo de agente es
  una anécdota de throughput. La retirada posterior de Orca reduce su interés
  como candidato. No cambia las recomendaciones locales.
- **Computer Usage:** no hay ejecución E2E verificable de apps, capturas ni
  estado final comprobado.
- **Visión:** el model card anuncia una interfaz imagen-texto, pero ni el post
  ni el ensayo local prueban calidad visual.
- **Contexto largo:** el post sí reporta un prompt efectivo cercano a 256K,
  pero repetitivo y de localidad favorable; no prueba recuperación de hechos
  variados. La corrida local se limitó a contexto 131K y tuvo stalls de prefill.
- **Rendimiento:** las cifras son plausibles sólo para ese hardware, fork,
  prompt, KV y MTP. No se comparan directamente con las mediciones de LlamaCode
  sobre 2×RTX 3090 ni con otros perfiles. El resultado de Orca fue además
  sustancialmente más lento en decode que el checkpoint NVIDIA dentro del mismo
  post.
- **Ingi-Charla/audio:** no se probó audio, ASR ni TTS.

## Decisión

Completar como revisión documental. No promover OrcaRouter NVFP4, no cambiar
perfil, HarnessSpec ni defaults, y no iniciar un nuevo A/B del mismo checkpoint.
Para reconsiderar la idea hace falta un candidato distinto con identidad y
licencia compatibles (por ejemplo, el Qwen original GPTQ/NVFP4 que hoy
recomienda el fork), una build reproducible para Linux/RTX 3090, y un protocolo
local que pase el gate de prefill antes de habilitar HE20/BCB8. Esto sería una
nueva huella/candidato, no una repetición del benchmark del post.

No hubo descarga, inferencia, uso de GPU ni cambios productivos. **SOL ya estaba
descargado y disponible para la comparación anterior; no se descargó de nuevo**
ni esta tarea necesitó sus pesos.
