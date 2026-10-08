# Auditoría ASTRA: visión y BCB

Fecha: 2026-09-14

## Objetivo

Se investigó si **ASTRA** —Qwen3.8 Flash-Next Q4 con cache de expertos 188 y
KV Q8— podía recuperar una salida válida para mejorar su BCB y habilitar
visión sin superar el límite del proyecto de Q8 para pesos y KV.

El modelo oficial sí declara un encoder visual y publica proyectores
`mmproj-BF16.gguf` y `mmproj-F16.gguf` en su [tarjeta oficial de
Hugging Face](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF). Por eso
se probó el proyector exacto del modelo, no el `mmproj` de Qwen3.8-27B que se
había usado antes.

## Artefactos y entorno

- Modelo: `/media/cristian/Disco local/Models/llamacpp/Qwen3.8-Flash-Next-UD-Q4_K_XL/UD-Q4_K_XL/`.
- Proyector compatible descargado: `/media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.8-Flash-Next/mmproj-BF16.gguf` (907.542.944 bytes).
- Backend: build `llama.cpp-phase-prefill-e06`, con soporte para
  `CUDA_Host`, cache de expertos y `mtmd`.
- CPU disponible: AMD Ryzen 9 9950X3D, 16 núcleos/32 hilos, con ~123 GiB de
  RAM disponible durante la campaña.
- P2P: `nvidia-smi topo -p2p r` y `nvidia-smi topo -p2p w` devuelven `OK` en
  ambas direcciones. La build tiene `GGML_CUDA_NO_PEER_COPY=OFF` y el perfil
  usa `--split-mode layer`, por lo que las copias entre las dos GPU no están
  deshabilitadas.
- KV: `q8_0`/`q8_0` en todas las recetas; el BF16 del `mmproj` es el proyector
  visual y no cambia el límite de cuantización de pesos ni del KV.
- Reparto: dos RTX 3090, cache de expertos 188, `--flash-attn on`,
  `--parallel 1`, contexto 196K, sin convertir ASTRA en un perfil MTP.

## Resultados

| Prueba | Resultado | Decisión |
|---|---|---|
| Arranque con el `mmproj` anterior de Qwen3.8-27B | Mismatch de dimensiones 2560/5120 | Artefacto incorrecto; descartado |
| Arranque con `mmproj-BF16.gguf` oficial de Flash-Next | Carga correcta y el servidor se anuncia como multimodal | **Carga reparada** |
| Texto con proyector en GPU | Salida corrupta: `/` repetido hasta `finish_reason=length`; una variante terminó además con `CUDA illegal memory access` | No usable |
| Imagen con proyector en GPU | `CUDA illegal memory access` dentro de `mtmd_helper_decode_image_chunk()` | Visión no validada |
| Imagen con proyector en CPU, ubatch reducido y límites visuales explícitos | Evita el aborto, pero devuelve `/` repetido | No usable |
| Receta histórica de ASTRA, sin `tensor-split` explícito | Texto vuelve a `/` repetido; imagen vuelve a abortar en CUDA | No es un problema de un único flag |
| ASTRA con reparto explícito por capas y P2P disponible | Las dos GPU asignan memoria y el servidor carga; el texto sigue en `/` repetido y la visión GPU vuelve a fallar en `mtmd` | P2P está activo, pero no corrige la corrupción |
| ASTRA + head MTP Q8, smoke corto | Python válido; aceptación 6/10 y 4,77 tok/s | No concluyente |
| ASTRA + head MTP Q8, control largo | `/` repetido; aceptación 0/251 y 5,74 tok/s | Rechazado; no mejora calidad ni velocidad útil |
| ASTRA sin MTP, mismo control largo | `/` repetido a 44,02 tok/s | El TPS bruto tampoco es utilizable |
| ASTRA + MTP Q8 + `mmproj` oficial | Carga multimodal OK; imagen produce `/` repetido, aceptación 0/123 y warnings de posiciones no consecutivas | Visión no usable |
| ASTRA texto, `ctx-size 262144`, KV Q8, sin MTP | `n_ctx_slot=262144`; smoke `CONTEXT_262K_OK` correcto | **262K cargable; contexto profundo aún no validado** |
| BCB/HE0 | No se ejecuta de forma válida: el smoke básico ya está corrupto | Mantener **BCB no válido** |

La carga del proyector correcto demuestra que el problema anterior de
dimensiones era reparable. No demuestra que la ruta visual sea funcional: en
el backend actual la combinación Flash-Next + cache de expertos + `mtmd` no
produce una secuencia válida. La incidencia pública de visión de
Flash-Next en llama.cpp también documenta resultados incompletos con entradas
largas; ver [llama.cpp issue #27886](https://github.com/ggml-org/llama.cpp/issues/27886).

## ¿Se puede mejorar el BCB?

No con honestidad mediante sampling, más contexto, `mmproj` o cambios de
cache. El modelo genera tokens repetitivos incluso en un prompt textual corto,
por lo que cualquier puntuación BCB sería un falso positivo. El decode bruto
observado en una variante rondó 47–49 tok/s, pero no se registra como mejora:
la salida no era utilizable.

El 9950X3D sí sirve como fallback de capacidad. Una campaña anterior con la
tabla PLE en CPU y `--n-cpu-moe 48` produjo texto válido a aproximadamente
7,54 tok/s usando `lazy-mode on-direct`, pero quedó muy por debajo del control
CUDA y no validó visión, tool-use ni BCB. El proyector en CPU de esta campaña
evitó el crash visual, pero siguió devolviendo `/`. En otras palabras, CPU es
útil para alojar memoria o expertos fríos; no es, por sí solo, la reparación de
la arquitectura visual ni de la salida agentiva.

P2P tampoco es el cuello principal de este caso. La topología PCIe permite
lectura y escritura peer-to-peer y la build lo deja habilitado; además, la
receta estable de ASTRA ya reparte por capas. No se agrega `tensor-split`: la
ruta tensorial experimental para `qwen4exp` ya había fallado antes y no ofrece
una base segura para comparar rendimiento.

También se probó el head MTP Q8 de Flash-Next. El resultado corto fue válido,
pero no se sostuvo en una generación de 128 tokens: la aceptación cayó a 0%
y el resultado volvió a `/`. Por tanto MTP no rescata ASTRA; DFlash2 tampoco
es intercambiable porque no hay un drafter compatible con Flash-Next.

El siguiente intento técnicamente razonable sería aislar un backend/commit de
llama.cpp con una reparación específica de Flash-Next/`mtmd`, sin cache de
expertos o con un runtime que valide explícitamente la arquitectura. Eso no se
promueve como cambio de perfil hasta que pase, en orden, smoke de texto,
smoke visual, tool-use y BCB.

## Decisión para LlamaCode

- ASTRA conserva **196K operativo**, **KV Q8**, **16–41 tok/s históricos** y
  **BCB no válido**. La misma receta de texto sin MTP ya carga a **262K** y
  responde a un smoke corto, pero todavía no se declara contexto profundo
  validado ni se cambia el lanzamiento predeterminado.
- No se agrega la marca de visión al dropdown ni a la tabla operativa.
- No se cambia SOL ni ningún otro perfil.
- Se conserva el `mmproj` correcto en `models/` para futuras pruebas; no se
  borra ni se activa automáticamente.
- No se modificaron Windows, los pesos del modelo ni los límites máximos de
  cuantización.
