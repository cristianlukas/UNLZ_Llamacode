# Hardin22 Strata-DualGPU — auditoría local

Fecha: 2026-10-03
Estado: **mejora de velocidad prometedora; no promover todavía**.

## Hallazgo

El fork es útil como siguiente candidato para el runtime experimental ASTRA:
en el mismo hardware y con el mismo pack IQ3_S y drafter MTP que Strata 0.1.35,
aceleró la generación de código y mantuvo el corpus de decisiones de Computer
Use en 100%. No se cambiaron los perfiles, defaults, harness ni configuración de
Ingi-Charla. El modelo/quant exacto de esta prueba tampoco coincide con el ASTRA
Q4 del catálogo.

El autor del fork reporta 143 tok/s de código y 102 tok/s narrativos en RTX 5080
+ RTX 4060 Ti con Swift IQ2_XS. Esos valores no se trasladan a la notebook ni a
nuestro perfil. El README dice que no probó Linux ni otras tarjetas; aquí se
logró compilar y correr en Ubuntu, pero eso sólo valida este entorno.

## Corrida local

| Campo | Valor |
|---|---|
| Fork | `Hardin22/Strata-DualGPU`, commit `73bbf3861b48e258cfd076ba7970c078373b8e1a` (2026-10-03) |
| Base comparativa | Strata 0.1.35 local contra el fork derivado de Strata 0.1.38 |
| Hardware | Ryzen 9 9950X3D, 124 GiB RAM, 2× RTX 3090 24 GiB, driver 610.57, CUDA 13.0 para el fork |
| Modelo | Qwen3.8-Flash-Next-GSQ-RCO IQ3_S; los mismos dos GGUF, pack, MTP4 y expert profile local |
| Configuración | Contexto 131072, KV int8, 32768 celdas residentes, spec 4, `min_p 0.5`, sin prompt cache |
| Protocolo de velocidad | Greedy, reasoning desactivado, 4 repeticiones de 400 tokens para código y prosa; 2 de 31997 tokens de entrada con 128 de salida |
| Servicio | API OpenAI-compatible de Strata, requests seriales, GPU libres de otros modelos durante la segunda corrida del baseline y la corrida del fork |

El primer baseline corrió con otro `llama-server` ocupando parte de la segunda
GPU: código 85,7 tok/s, prosa 66,4 tok/s y salida con contexto largo 80,6 tok/s.
Se conserva separado como `speed-summary-baseline-0.1.35-concurrent-gpu-load.json`
y **no** se usa en la comparación principal. Se repitió después con las GPUs
libres. Los resultados comparables medidos fueron:

| Caso | Strata 0.1.35 | Fork 0.1.38 | Delta fork |
|---|---:|---:|---:|
| Código, 4×400 tokens | 106,3 tok/s | 122,5 tok/s | +15,2% |
| Prosa, 4×400 tokens | 81,8 tok/s | 81,6 tok/s | −0,2% |
| Prefill, 31997 tokens | 2698,8 tok/s | 2796,6 tok/s | +3,6% |
| Decode tras prompt de 31997, 2×128 tokens | 80,2 tok/s | 91,2 tok/s | +13,7% |

La comparación mide los autosplit/autocache propios de cada runtime: el baseline
cargó 13,33 GiB de caché de expertos y el fork 18,07 GiB. El fork seleccionó
orden de GPU `[1,0]` (GPU más rápida al final) y `K=29`, frente a `K=27` del
baseline. Esto es parte de lo que el fork cambia operacionalmente, pero impide
atribuir toda la diferencia a una única optimización aislada. Las dos variantes
completaron todas las longitudes solicitadas sin errores. La respuesta de código
principal coincidió en 3/4 repeticiones del fork; esto no es una prueba de
equivalencia de calidad.

### Computer Use y herramientas

La misma suite local `computer_use_prompt_order_hard_v1` pasó sus 216
decisiones (24 situaciones × 3 órdenes × 3 pasadas) con `temperature 0.6`,
`top_p 0.95`, `top_k 20`, thinking desactivado, semillas 11/42/77 y orden 4242:

| Variante | Exactitud | Validez | Seguridad | Mediana | P95 |
|---|---:|---:|---:|---:|---:|
| `state-first` | 100% | 100% | 100% | 569 ms | 641 ms |
| `question-first` | 100% | 100% | 100% | 559 ms | 623 ms |
| `sandwich` | 100% | 100% | 100% | 709 ms | 771 ms |

La corrida anterior de 0.1.35 pasó las mismas 216 decisiones con 100% de
exactitud/seguridad y medianas de 695/684/865 ms. El fork bajó la latencia, pero
el gate de promoción continúa en `FAIL`: la variante `sandwich` excede en más de
5% la mediana de `state-first`. Esta suite califica decisiones sobre estado
textual; no ejecuta la GUI, captura pantalla ni prueba clicks o recuperación.

Function calling también emitió `lookup_ticket({"ticket_id":"LC-42"})` con
JSON válido y redactó correctamente una respuesta al resultado simulado. Es un
smoke del contrato API, no un turno de agente LlamaCode.

## Relevancia para LlamaCode

- **Velocidad de generación:** sí, el resultado más claro es para código (+15%
  frente a baseline libre); prosa queda en paridad. La salida tras 32K mejora
  ~14% en esta muestra pequeña.
- **Computer Use:** el corpus textual sigue en 100% y responde más rápido; el
  gate global de latencia no pasa y falta usarlo desde el flujo real de
  automatización con escritorio.
- **Harness de coding:** LC-H1 ya pasó en Strata 0.1.35 en la corrida del
  2026-10-02, pero **no se repitió en este fork**. Como cambia el engine y el
  modelo puede dar respuestas distintas, esos puntajes no certifican el fork.
  Falta HE0 → HE20 → BCB8 y adversarial en LlamaCode antes de cambiar el perfil
  experimental ASTRA.
- **Ingi-Charla:** no aplica. El fork sirve el motor de texto/imagen; no añade
  ASR, TTS ni ruta de voz. No se repitió esa suite porque esta variante no
  modifica sus proveedores de audio.
- **Promoción:** no cambiar SOL, ASTRA, muestreo, harness ni defaults. Para
  integrar el fork en un perfil local haría falta repetir LC-H1 en el flujo de
  LlamaCode y validar la instalación objetivo; el post no prueba la ruta de
  Windows de este proyecto.

## Build y límites

El build oficial con CUDA 12.8 falló por incompatibilidad de APIs de CUDA Graph.
Se instaló el toolkit CUDA 13.0.1 de forma local en
`~/.cache/cuda-13.0.1` (sin reemplazar el driver ni el toolkit del sistema) y el
fork compiló con arquitectura 86. El primer arranque no pudo asignar caché
experta por presión de VRAM; se dejó intacto el proceso ajeno y se repitió con
reserva explícita para la GPU posterior. El segundo arranque cargó y respondió.
CUDA 13.0 y el proceso `strata` de prueba ya se cerraron; no se dejó un servidor
ocupando las GPUs.

Artefactos propios de la prueba están en
[`artifacts/strata-dualgpu-evaluation-20261003/`](../artifacts/strata-dualgpu-evaluation-20261003/): script y JSON de velocidad, suite Computer Use y function-calling. El primer baseline bajo carga GPU está conservado y rotulado por separado.

Referencias externas: [README del fork](https://github.com/Hardin22/Strata-DualGPU) y [documentación de diseño dual-GPU](https://github.com/Hardin22/Strata-DualGPU/blob/main/docs/DUAL_GPU.md).

## No repetir

- No volver a descargar ni compilar este commit para las pruebas anteriores: el artefacto permanece en `~/.cache/strata-dualgpu-eval-20261003/`.
- Para repetir sólo velocidad, comprobar primero la ocupación de las dos GPU y usar `benchmark.py`; consultar los resúmenes separados del baseline con y sin carga concurrente.
- No repetir Computer Use textual hasta cambiar el modelo/quant, sampling, corpus o motor. La limitación pendiente es GUI real, no el corpus ya pasado.
- No volver a usar los números del post como equivalentes a IQ3_S/RTX 3090 ni como prueba de calidad del harness.
