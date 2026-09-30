# Auditoría del fork Strata `custom` — 2026-09-30

## Resultado ejecutivo

El fork merece seguimiento para **Qwen3.8-Flash-Next en el perfil de modelo**:
añade soporte para los GGUF UD de Unsloth, MTP/prompt lookup y una segunda GPU
como nivel de caché de expertos. Sus tablas reportan mejoras grandes de
prefill y decode. No es un cambio de parámetros trasladable a `llama.cpp`, ni
una mejora para Ingi-Charla o Computer Use.

No se promueve ni se cambia ningún perfil: el motor del fork **no llegó a
compilar en este equipo**. El build requiere CUDA 13, mientras que el entorno
tiene CUDA 12.8/12.0; falló al compilar `cudaMemcpyBatchAsync` y las estructuras
asociadas. La descarga aislada del toolchain 13 se canceló por transferencia
muy lenta. No se descargaron pesos nuevos ni se ejecutaron benchmarks con este
fork. Por lo tanto, sus números publicados no son resultados locales.

## Fuente y configuración publicada

- Post: <https://www.reddit.com/r/LocalLLM/comments/1wu6fka/qwen_38_flash_next_doubled_strata_throughput_on/>
- Código/PR: <https://github.com/eddoursul/Strata/tree/custom>, PR
  <https://github.com/Niko1221/Strata/pull/245>
- Tabla del autor: <https://github.com/eddoursul/Strata/blob/custom/docs/COMPARISON.md>
- Checkout evaluado: commit `25e86c762b569f8d4a5f434e3cb31b4b916ee50d`
  (`examples/: a launcher per config...`). Las tablas de comparación indican
  mediciones en `0bbd8f5`.

La tabla del autor compara en Windows 11 una RTX 3090 como GPU principal y una
RTX 5070 Ti como segundo nivel, con 160 GB DDR5 y Ryzen 7 9700X. Reporta IQ3_S
en dos GPU a 2.466–2.688 tok/s de prefill y hasta 167,7 tok/s de decode; para
UD-Q4_K_XL, 2.341–2.662 tok/s de prefill y hasta 160 tok/s de decode. En una
sola 3090 reporta 1.605–1.791 tok/s / 108–114 tok/s para IQ3_S y
1.099–1.221 tok/s / 68–114 tok/s para UD-Q4_K_XL. Son cifras del autor,
medidas con requests específicos y una pasada por configuración; no se deben
mezclar con nuestros benchmarks agentivos.

El autor midió acuerdo de argmax con `llama.cpp` en tres textos: IQ3_S quedó
entre 98,0 y 100%; UD-Q4_K_XL, entre 95,8 y 99,3%. La propia tabla atribuye
parte de la diferencia a redondeo y cuantización. Esto es una comprobación
parcial de fidelidad de siguiente token, no una validación de código, tools,
visión o Computer Use.

## Pruebas locales realizadas

Hardware detectado: **2× RTX 3090 (24 GB c/u), Ryzen 9 9950X3D, 124 GB RAM**,
Ubuntu 24.04 y driver 610.57.04. Ningún GGUF de Flash-Next ni MTP compatible
está disponible en las rutas de modelos consultadas. Los datos de Strata
descargados para la prueba upstream de 2026-09-29 ya no están presentes.

| Prueba | Resultado |
|---|---|
| `python3 setup.py --check` en el checkout aislado | **Pasa**; detecta ambas 3090, AVX-512 y confirma que sus opciones IQ3_S y menores caben en RAM. El preflight upstream no ofrece UD-Q4_K_XL. |
| Configuración CUDA de este fork para SM86 con CUDA 12 | CMake configura CUDA y acepta SM86; el build compila varias unidades CUDA y C++. |
| Build del engine | **Falla** en `src/core/expert_cache.cpp`: CUDA 12 no declara `cudaMemcpyAttributes`, `cudaMemcpySrcAccessOrderStream`, `cudaMemcpyFlagPreferOverlapWithCompute` ni `cudaMemcpyBatchAsync`. El fork documenta CUDA 13 para esta rama. |
| Configuración con `STRATA_BUILD_TESTS=ON` | **No disponible en el checkout**: `tests/CMakeLists.txt` no está incluido, aunque CMake intenta añadir ese subdirectorio. |
| API, tokens/s, contexto, BCB8, Computer Use, visión, Ingi-Charla | **No ejecutados** en el fork `custom`; sin engine y sin pesos locales. |

La salida previa de Strata upstream del día anterior no se repite aquí:
Q2_0 en una sola 3090 con MTP4 ya obtuvo **1/8 en BCB8** dos veces con el
sampling del proyecto, y la prueba de razonamiento también agotó el presupuesto
sin producir código. Eso fue otra rama y otra cuantización; no refuta el fork
`custom`, que ofrece UD-Q4_K_XL y optimizaciones nuevas. El detalle permanece
en [`strata-qwen38-audit-20260928.md`](strata-qwen38-audit-20260928.md) y
`artifacts/strata-evaluation-20260929/`.

## Aplicabilidad al proyecto

| Área | Evaluación |
|---|---|
| Qwen3.8-Flash-Next / modelo | **Candidato a prueba local**. UD-Q4_K_XL coincide con un formato que ya usamos y el fork promete una mejora de motor. No copiar sus `tok/s` ni argumentos al perfil `llama.cpp`. |
| Harness de agente | Sin resultado aún. El endpoint OpenAI-compatible podría conectarse por el backend local externo que se probó con upstream; antes de crear un perfil opt-in hay que validar BCB y tool loop completos, límites de contexto y una sola solicitud concurrente. |
| Computer Use | No evaluado y no se anuncia control de escritorio. La compatibilidad OpenAI/tools no sustituye el backend de automatización de escritorio. |
| Ingí-Charla | No aplica: no aporta STT, VAD, turn detection ni TTS. |

La conclusión coincide con la prueba previa de Strata: no cambiar el default
SOL, el harness ni los perfiles compartidos por una tabla externa. La rama
`custom` sí justifica una nueva campaña aislada cuando CUDA 13 esté disponible.

## Qué ejecutar cuando haya CUDA 13 y pesos

Para no duplicar trabajo, **no repetir** el preflight básico, los barridos
Qwen3.8-Flash-Next UD-Q2_K_XL de `artifacts/qwen38-q2-context-matrix-20260923.json`,
ni el BCB8 de Strata upstream GSQ-RCO Q2_0.

La siguiente campaña útil es el A/B del mismo GGUF **UD-Q4_K_XL** en el fork
`custom` y en el runtime productivo local, con el prompt de velocidad fijo y
la evaluación de agente existente:

1. Compilar CUDA 13 para SM86; guardar versión exacta del toolchain y commit.
2. Probar carga/estabilidad y 8K, 32K, 64K y 128K en la 3090 principal; luego
   repetir con la segunda 3090 habilitada. Mantener sampling y prompt idénticos.
3. Medir prefill, decode, TTFT, VRAM, RAM y aceptación MTP; separar prompt frío
   de prefijo reutilizado.
4. Correr HE0 → HE20 → BCB8 a través del harness de LlamaCode con el mismo
   cuantizado/contexto, y validar tool loop/cancelación antes de proponer un
   perfil externo opt-in.
5. Si supera las gates, hacer Computer Use con su suite específica. Ingi-Charla
   sólo merece prueba si aparece una integración de audio concreta.

Para que el test de velocidad sea comparable, el autor recomienda requests
greedy; nuestras gates agentivas conservan el sampling vigente del perfil. No
mezclar ambos resultados en una única cifra. El `COMPARISON.md` reporta una
sola toma por configuración y una PC 3090+5070 Ti/160 GB; registrar medianas y
repeticiones locales antes de atribuir el beneficio a nuestras dos 3090.
