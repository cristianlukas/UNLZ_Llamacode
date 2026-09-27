# Agention AP Q3_K_XL — benchmark local · 2026-09-26

## Dictamen

El perfil local queda **SUPERIOR en perplexity local** frente a los controles
de tamaño parecido UD-Q3_K_XL y ByteShape IQ4_XS, en los dos corpus abiertos
probados. Queda **en paridad en coding smoke y Computer Use** con ByteShape.
La velocidad de AP y UD es prácticamente igual; AP es **inferior en decode
bruto a Qwen3.5-9B**, que es un modelo mucho más pequeño.

El resultado no justifica reemplazar SOL, cambiar Ingi-Charla ni promover AP
como agente principal. HE20 y BCB de LC-H1 siguen pendientes. El perfil conserva
manualOnly=true, benchmark=true, best=false.

| Dimensión | Agention AP Q3_K_XL | Comparación local | Estado |
|---|---:|---:|---|
| PPL · mixedweb-v1, 60 × 2048 | 11,0283 ± 0,11911 | UD 11,0631; ByteShape 11,1020 | **SUPERIOR en PPL local** |
| PPL · corpus Wiki del proyecto, 40 × 512 | 6,0887 ± 0,14585 | UD 6,1278; ByteShape 6,2170 | **SUPERIOR en PPL local** |
| llama-bench, pp2048 | 1131,45 ± 12,43 tok/s | UD 1135,74; ByteShape 1108,86 | **Paridad entre quants 27B** |
| llama-bench, tg128 | 37,16 ± 0,07 tok/s | UD 37,62; ByteShape 36,20 | **Paridad entre quants 27B** |
| Fixture visual, propuesta de acción | 3/3 | ByteShape 3/3 | **Paridad** |
| Computer Use state-first | 24/24 | ByteShape 24/24 | **Paridad** |
| Computer Use adversarial | 24/24; seguridad 21/21 | ByteShape 24/24; seguridad 21/21 | **Paridad** |
| Coding smoke | 3/3 tras corregir dos anclas de idioma | ByteShape 3/3 | **Paridad; smoke, no ejecución de código** |
| Ingi-Charla / audio | Sin medición | Qwen3.8 consume texto e imagen | No es un modelo ASR/TTS |
| HE0 → HE20 → BCB LC-H1 | Pendiente | — | Sin promoción agentiva |

## Máquina, runtime y modelos

- Windows, dos RTX 3090 de 24 GiB; llama.cpp b29c606e2 (build 10964).
- La corrida estuvo fijada a CUDA1. Un llama-server de PeritoSoft siguió
  activo en CUDA0; no se detuvo ni se compartió la GPU usada para las medidas.
- AP: Qwen3.8-27B-AP-Q3_K_XL.gguf, 13.146.392.480 bytes,
  SHA-256 b5b35d550712f01fcaa0a982f281b7bcf47f6309c541450ca0e064c945c1c8fc.
- Control UD: Qwen3.8-27B-UD-Q3_K_XL.gguf, 13.146.393.504 bytes,
  SHA-256 8c2a45ff85e7674ca185ec8eb6cdeab0e617ed9d8018caed0b64380eb2a67a5e.
- Control ByteShape local: Qwen3.8-27B-IQ4_XS-3.84bpw.gguf,
  13.083.052.416 bytes,
  SHA-256 89434f23dc89c5f990894e3fe9fdad19d88c370f0d3638a176f29933f218b78b.
- AP usa el mmproj BF16 oficial de 931.146.432 bytes. ByteShape usa su propio
  mmproj BF16 de 931.146.528 bytes. El test visual cargó ambos.
- El perfil persistido usa contexto 32K, KV Q8, batch/ubatch 512/128, Flash
  Attention, template qwen38-tools-fixed.jinja y MTP apagado.

La medición de velocidad aislada usó llama-bench con -ngl 999, -fa 1,
-ctk f16, -ctv f16, -sm none, -mg 0, -dev CUDA1, pp2048/tg128 y tres
repeticiones. Los flags explícitos de KV de esa prueba fueron F16 para
mantener una condición igual y corta entre GGUF; no equivalen al KV Q8 del
perfil persistente. llama-bench etiquetó ByteShape como «guessed all F32»;
la identidad de la tabla viene del archivo IQ4_XS verificado, no de esa
conjetura interna del detector.

El PPL de mixedweb usó llama-perplexity, 60 bloques de 2048 tokens y batch
2048. El Wiki del
proyecto usó el protocolo existente de 40 bloques de 512 tokens. MTP no
participó; llama-perplexity avisó que ignoró los tensores MTP adicionales del
GGUF ByteShape.

## Fidelidad de siguiente token

El dataset público mixedweb-v1.txt se fijó a la revisión
e71c458859813276ba2881ace8e25f2b792abefe. Su MD5
51e0045e8cabf37922aa82766a25b7b4 coincide con el publicado; el SHA-256 local
es efcdc8974f9e0ccd94eba18e754e266c70609c88298762ad4506cd06b2f6d87a.
No se usó para calibrar los pesos.

La PPL final fue menor para AP que para ambos controles. En el análisis pareado
de los mismos bloques, la diferencia media AP−control fue:

| Corpus | Control | Diferencia PPL por bloque | IC 95% t, descriptivo |
|---|---|---:|---:|
| mixedweb, n=60 | UD-Q3_K_XL | −0,0478 | [−0,0528; −0,0428] |
| mixedweb, n=60 | ByteShape IQ4_XS | −0,0956 | [−0,1014; −0,0899] |
| Wiki del proyecto, n=40 | UD-Q3_K_XL | −0,0861 | [−0,1015; −0,0707] |
| Wiki del proyecto, n=40 | ByteShape IQ4_XS | −0,1845 | [−0,2023; −0,1668] |

Los intervalos pareados son descriptivos: los bloques consecutivos de un corpus
no son muestras independientes. Los errores de las PPL agregadas se solapan,
así que la ventaja se etiqueta como **superior en PPL local**, sin convertirla
en garantía de mejor calidad de tareas.

El autor compara KLD contra una referencia Qwen3.8 BF16 común: reporta AP
0,0250 frente a UD 0,0270 en mixedweb, y AP 0,0359 frente a UD 0,0337 en
WikiText-2. Esta corrida no reprodujo ese KLD. PPL del modelo y KLD contra BF16
son métricas diferentes. Además, el wiki.test.raw local tiene SHA-256
A6F23DF4148D59AE891819F5B155171AED6295BBD97A77216418155696F83C9A, distinto
del archivo WikiText-2 citado por el autor. No se descargó la referencia BF16
de 54.657.733.888 bytes ni se generó una base KLD. Con el servidor de otra
aplicación activo, esa referencia dejaría casi sin margen la memoria libre de
GPU/RAM; no hacía falta para la comparación directa de PPL entre los quants.

## Rendimiento

| Modelo | Tamaño de archivo | pp2048 | tg128 |
|---|---:|---:|---:|
| Agention AP Q3_K_XL | 12,23 GiB | 1131,45 ± 12,43 | 37,16 ± 0,07 |
| Unsloth UD Q3_K_XL | 12,23 GiB | 1135,74 ± 12,38 | 37,62 ± 0,12 |
| ByteShape IQ4_XS | 12,17 GiB | 1108,86 ± 13,27 | 36,20 ± 0,33 |
| Qwen3.5-9B Q4_K_M | 5,28 GiB | 3398,23 ± 86,66 | 101,36 ± 3,08 |

AP y UD empatan dentro de la variación medida. Frente al 9B, AP genera 2,73
veces más lento en este test directo; es una comparación de throughput, no de
calidad equivalente. SOL tampoco se midió con este binario: sus cifras
históricas provienen de vLLM/AutoRound y no son una comparación A/B válida.

## Coding, Computer Use y voz

Se reutilizó llamacode_local_coding_smoke.json con el mismo template Qwen y
sampling conservador. Al revisar las respuestas apareció un defecto en dos
anclas del dataset: esperaba atom y validacion en respuestas españolas.
El benchmark pasó a buscar atómica y validación, que corresponden al enunciado
español. Las generaciones ya guardadas se reevaluaron; no se repitió inferencia
para cambiar la nota. AP y ByteShape pasan 3/3 con las anclas corregidas. La
suite sólo comprueba fragmentos de respuesta: no ejecuta la función ni valida
razonamiento de forma completa.

La nueva fixture
assets/benchmarks/custom/computer_use_vision_settings_v1.json contiene una
captura sintética y la acción semántica esperada. AP y ByteShape propusieron
3/3 veces la llamada desktop_control_action correcta para activar Tema oscuro
y preservar los controles de privacidad. La acción no se ejecutó.

Las suites de decisiones existentes dieron 24/24 en
computer_use_prompt_order_v1 y 24/24 en
computer_use_prompt_order_hard_v1 para ambos modelos. En la suite difícil cada
uno acertó los 21 casos etiquetados como sensibles. Son pruebas de selección de
opción a partir de estado textual; la fixture visual cubre sólo una tarea.
Ninguna mide todavía la resolución de controles UIA, freshness guard, receipt,
ejecución real, grounding de coordenadas ni resistencia a inyecciones dibujadas
dentro de imágenes. La sección nueva de docs/computer-use.md deja separadas
esas compuertas.

Qwen3.8 AP aquí se probó como modelo texto+imagen. No tiene encoder de audio ni
prueba de ASR, WER, TTS o diarización. No modifica perfiles ni harness de
Ingi-Charla.

## Perfil y archivos reproducibles

El catálogo ya contiene sys-bench-qwen38-agention-ap-q3kxl-32k. Actualicé su
etiqueta a **SUPERIOR PPL local · PARIDAD en Computer Use** y guardé los
resultados en el comentario del perfil. Sigue manual/benchmark, fuera de BEST
hasta cerrar HE20 y BCB con LC-H1.

Los comandos, hashes, salidas completas y herramientas de reproducción están
en [artifacts/qwen38-agention-ap-local-benchmark-20260926](../artifacts/qwen38-agention-ap-local-benchmark-20260926/):

- ppl-mixedweb-manifest.json y las tres salidas de llama-perplexity.
- Speed logs de llama-bench para AP, UD, ByteShape y Qwen3.5-9B.
- vision_tool_smoke.py, el JSON con respuestas y resultados, y los logs de
  servidor de ambas variantes.
- run_mixedweb_ppl.py.

## Fuentes

- [Ficha Agention Precision Qwen3.8-27B](https://huggingface.co/agentionai/Qwen3.8-27B-AP-GGUF)
- [Dataset público quant-fidelity-corpora](https://huggingface.co/datasets/agentionai/quant-fidelity-corpora)
- Auditoría inicial: [qwen38-agention-ap-quant-audit-20260926.md](qwen38-agention-ap-quant-audit-20260926.md)
