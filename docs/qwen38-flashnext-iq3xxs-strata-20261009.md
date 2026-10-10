# Evaluación Qwen3.8-Flash-Next IQ3_XXS con Strata — 2026-10-09

## Resultado

No promuevo IQ3_XXS a un perfil productivo. En HE20 + BCB8, IQ3_XXS terminó
24/28 y ASTRA IQ3_S calibrado 28/28. ADV v1 es complementaria y ambos cerraron
10/10 después de reparaciones; TaskFlow ULTRA dio 11/13 y 13/13,
respectivamente. La suma descriptiva de criterios es 45/51 y 51/51; primera
pasada 42/51 y 41/51. No es un ranking estable: hay una corrida válida por
perfil. ASTRA completó estas cuatro mediciones unos 306 s antes en conjunto.
HE0, prerrequisito separado, pasó 1/1 para ambos.

El benchmark nativo Server Speed v1 da una señal mixta: IQ3_XXS promedió
126,59 tok/s y ASTRA 122,09 tok/s, con rangos de las dos pasadas que se
superponen. IQ3_XXS sí tuvo menor TTFT en ambas pasadas: media de 370,63 ms
contra 451,00 ms. Es una mejora de latencia inicial repetida en esta muestra,
pero no compensa la diferencia de calidad para promover el perfil.

## Calidad con LlamaCode

Todos los recibos de IQ3_XXS y ASTRA se obtuvieron con Strata v0.1.41, la
misma compilación local, suite copiada byte por byte y perfil de agente
equivalente. Primera pasada y resultado final se muestran por separado.

| Suite | IQ3_XXS: primera → final | Reparaciones; 1.ª pasada / total | IQ3_XXS: tok/s; TTFT | ASTRA: primera → final | Reparaciones; 1.ª pasada / total | ASTRA: tok/s; TTFT |
|---|---:|---:|---:|---:|---:|---:|
| Prerrequisito HE0 · fuera de LC-H1 | 1/1 → 1/1 | 0; 9,762 / 10,062 s | 148,02; 58,00 ms | 1/1 → 1/1 | 0; 10,762 / 11,063 s | 140,06; 59,50 ms |
| LC-H1 · HumanEval 20 | 20/20 → 20/20 | 0; 694,943 / 695,244 s | 133,38; 52,07 ms | 20/20 → 20/20 | 0; 703,204 / 703,505 s | 124,20; 55,31 ms |
| LC-H1 · BigCodeBench-Hard 8 | 4/8 → 4/8 | 3; 290,095 / 324,900 s | 127,43; 128,87 ms | 3/8 → 8/8 | 2; 318,929 / 565,300 s | 123,88; 158,14 ms |
| Complementaria · Intelligence Adversarial 10 | 7/10 → 10/10 | 2; 791,855 / 977,519 s | 130,54; 69,54 ms | 8/10 → 10/10 | 2; 679,610 / 773,404 s | 124,33; 71,15 ms |
| **HE20 + BCB8 subtotal** | **24/28 → 24/28** | **3; 985,038 / 1.020,144 s** | — | **23/28 → 28/28** | **2; 1.022,133 / 1.268,805 s** | — |
| TaskFlow ULTRA (criterios aparte) | 11/13 → 11/13 | 3; 194,221 / 693,392 s | 139,36; 92,54 ms | 10/13 → 13/13 | 2; 237,987 / 342,831 s | 123,80; 71,70 ms |
| **Suma descriptiva HE20 + BCB8 + ADV + TaskFlow** | **42/51 → 45/51** | **8; 1.971,114 / 2.691,055 s** | — | **41/51 → 51/51** | **6; 1.939,730 / 2.385,040 s** | — |

Los fallos funcionales finales de IQ3_XXS fueron 4/8 en BCB8 y 11/13 en
TaskFlow ULTRA. En ADV v1 ambos perfiles cerraron 10/10 después de dos
reparaciones; al primer intento IQ3_XXS obtuvo 7/10 y ASTRA 8/10. Todos los
recibos fueron válidos, sin timeout ni caída. HE0 pasó para ambos como
prerrequisito y se excluye de estos subtotales. No se redujeron gates ni se
cambiaron criterios. El 13/13 de TaskFlow incluye un unittest generado por el
modelo y un self-test; no son verificadores independientes del contenido.

Hashes de las definiciones preservadas en el artefacto: HE0
7883f319c341fa82eb40fa4d1b665bbbf8c4b67b980fc93a28ad25d7eae64330; HE20
ed91a742cc8dca01bfe893933de5ed66fc4e4c2b529e53943a2bf1d939ffc3d7; BCB8
42771136b447b7b5619e04a1ea211f663222cd6752ca38d995083b5a4d207574;
Intelligence Adversarial v1
2f0f30c863606fd443a161ac6946658129b31d874229a61ffd719f75df36ee87.
TaskFlow ULTRA suite sha256:f04febb440208d5bf74c01e84d78f5127e57c164fabece2acbfb346215dc0c17,
HarnessSpec sha256:cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef.

TaskFlow ULTRA suma 13 criterios: diez verificaciones de existencia de archivos,
`py_compile`, un `unittest` escrito por el propio modelo y `--self-test`. La
comparación conserva el protocolo y los recibos, pero el unittest propio y el
self-test no son verificadores independientes del contenido. Por eso el 13/13
final de ASTRA no sustituye la lectura del resultado de BCB8 ni demuestra por sí
solo calidad general.

### Referencia SOL Qwen3.8-27B INT4

El recibo histórico comparable de TaskFlow ULTRA es SOL AutoRound INT4 con
0/13 en primera pasada y 7/13 final, tres reparaciones, 138,365 s,
42,90 tok/s y TTFT medio de 4.766,5 ms. Usa la misma suite y HarnessSpec
sha256:cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef,
agente agent-maximo, reasoning budget 8192, semilla 4242 y temperatura 0,1.
Es una corrida válida, pero única y de vLLM TP2; no es una comparación de
backend idéntico ni se repitió el servidor SOL. Sus fallas históricas de MTP
CUDA se guardan separadas y no se cuentan como calidad.

No existe en este ensayo un recibo SOL válido para LC-H1. Por eso SOL se
incluye sólo en TaskFlow ULTRA y no se le atribuye un puntaje LC-H1.

ADV v1 usó la misma suite oculta, HarnessSpec `cca4645b…`, seed 4242,
agent-maximo, thinking ON y timeout 1800 s en ambos perfiles. IQ3_XXS tuvo
105 tool calls y 977,519 s; ASTRA 63 tool calls y 773,404 s. Aunque los dos
cerraron 10/10, el candidato tardó 26,4% más en esta única pareja. El decode y
TTFT medios del runner no sustituyen el tiempo E2E. Recibos:
[IQ3_XXS ADV10](../artifacts/evaluacion-modelos-llamacode/Q-20261009-FLASHNEXT-IQ3XXS-AB/receipts/quality/iq3xxs/LC-H1/ADV10.json),
[ASTRA ADV10](../artifacts/evaluacion-modelos-llamacode/Q-20261009-FLASHNEXT-IQ3XXS-AB/receipts/quality/iq3s/LC-H1/ADV10.json).

## Velocidad de servidor

Se ejecutó el benchmark nativo LlamaCode Server Speed v1 con dos pasadas,
una de calentamiento, sin concurrencia, sweep de prefill habilitado y el mismo
corpus sha256:4bad8a5d24ce11096eb9634f7d03f24b83734c3f454031efb28d5fa259c996e9.
Cada recibo tiene 32/32 muestras válidas y cero fallidas. El sweep solicitó
hasta 65.536 tokens, pero el mayor prompt medido fue de 38.804 tokens.

| Modelo/configuración | Decode tok/s, pasadas 1 y 2 (media; rango) | TTFT medio, pasadas 1 y 2 (media; rango) | Prefill tok/s medio |
|---|---:|---:|---:|
| ISTA IQ3_XXS, spec-min-p 0,70 | 133,40; 119,78 (126,59; 119,78–133,40) | 363,75; 377,50 ms (370,63; 363,75–377,50) | 2.126,98; 1.721,62 (1.924,30) |
| ASTRA IQ3_S, spec-min-p 0,70 | 120,32; 123,86 (122,09; 120,32–123,86) | 452,16; 449,84 ms (451,00; 449,84–452,16) | 1.879,64; 1.868,72 (1.874,18) |

La media decode de IQ3_XXS supera a ASTRA 3,7%, menor que la variación entre
sus dos pasadas; no la considero una mejora demostrada. TTFT fue 17,8% menor
en media y menor en ambas pasadas. El prefill medio fue 2,7% mayor; el barrido
no alcanza 255K y no es comparable con los valores del post a contexto 262K.
No hay una medición Server Speed de SOL para esta configuración.

### Variantes aisladas

Las variantes de flags se midieron una vez cada una, con el mismo corpus:

| IQ3_XXS | Decode tok/s | TTFT medio | Lectura |
|---|---:|---:|---|
| Control: spec-min-p 0,70, PCIe 0,00, prefill auto | 133,40 | 363,75 ms | Recibo principal; se repitió a 119,78 tok/s |
| spec-min-p 0,50 | 112,88 | 378,50 ms | Más lento en esta pasada |
| PCIe fraction 0,55 | 129,48 | 363,20 ms | Dentro de la variación del control |
| prefill chunk 32.768 | 116,20 | 732,80 ms | Más lento y con TTFT mayor |

No se elige ninguno de esos flags alternativos. Los JSON de Strata y recibos
individuales están en el directorio de artefactos.

## Sampling

Se aisló temperatura y top-p con el mismo HumanEval/0, seed 4242, top-k 20,
min-p 0, repeat penalty 1 y presence penalty 0. Cada celda representa una
única respuesta del mismo problema; es una sonda diagnóstica, no una suite de
calidad.

| Condición | IQ3_XXS | ASTRA IQ3_S |
|---|---:|---:|
| LlamaCode: temp 0,6 / top-p 0,95 | pasa | falla |
| Sólo temp 0,7 | pasa | falla |
| Sólo top-p 0,8 | pasa | pasa |
| Receta del post: temp 0,7 / top-p 0,8 | pasa | falla |

En ASTRA, los fallos de tres variantes fueron respuestas de código Python
sintácticamente inválidas; top-p 0,8 pasó este ejemplo. En IQ3_XXS las cuatro
respuestas pasaron. La muestra no justifica cambiar el sampling productivo.
En las suites LlamaCode la temperatura efectiva registrada fue 0,1 para
ambos modelos; las demás opciones lanzadas fueron temp 0,6, top-p 0,95,
top-k 20, min-p 0, repeat penalty 1 y presence penalty 0.

## Configuración, hardware y memoria

- Pesos ISTA IQ3_XXS, revisión `1c04b8102ca5346f1faf4d9914503e378d713021`:
  shard 1 SHA-256 `219ea929900dfa9ef091f3aa473fdba6874b65fcb36526d7d851ac9e95856d15`;
  shard 2 `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.
  ASTRA calibrado IQ3_S, shard 1 SHA-256
  `4c1eb2ceb4915e1192f4f386021897bde56a97f40a0bb78bb86465e0f7d2aca3`;
  shard 2 coincide byte por byte con el shard 2 de IQ3_XXS y tiene el mismo
  SHA-256 `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.
- Strata v0.1.41, commit fb58e0dbc8399662c0e47c76578c6e878b14f6cf, compilado
  localmente con CUDA Toolkit 12.8.93 para sm_86 en ambas RTX 3090.
- Dos RTX 3090 de 24 GiB, RAM física 123,6 GiB, driver NVIDIA 610.57.04.
  Strata usó MTP/spec 4, expert cache auto, max context 131.072, KV int8,
  KV resident 32.768, prefill auto, spec-min-p 0,70 y PCIe fraction 0,00
  para las comparaciones base. La división automática de capas fue 26/22.
- LC-H1 usó agent-maximo, thinking habilitado, reasoning budget 4.096,
  semilla 4242 y máximo de tres reparaciones. TaskFlow ULTRA usó el mismo
  agente/semilla/tope, con reasoning budget 8.192. La suite y HarnessSpec
  TaskFlow tienen el mismo hash en ambos perfiles.
- Tiempo hasta cargar los expertos: IQ3_XXS 39,97 GiB a 2,50 GiB/s
  (46 s); ASTRA 46,84 GiB a 1,63 GiB/s (42 s). Tras cargar, los dos
  ocuparon alrededor de 23,6–24,0 GiB de VRAM en cada GPU.
- Muestreo de /proc del proceso Strata: IQ3_XXS alcanzó VmHWM 47.818.136
  KiB (45,60 GiB); ASTRA 55.547.060 KiB (52,95 GiB). Swap del proceso
  0 KiB en ambos. La telemetría de RAM del recibo de la aplicación informa
  0; se conserva esta medición suplementaria del proceso.
- D terminó con 210.716.770.304 bytes libres. Ningún modelo existente se
  borró y los perfiles productivos no se tocaron.

## Post y limitaciones

El material recibido es el post de [r/Qwen_AI sobre IQ3_XXS en una laptop de
8 GB](https://www.reddit.com/r/Qwen_AI/comments/1x097l9/strata_is_the_best_magic_qwen38_fn_iq3_xxs_on_a/).
El autor declara Ryzen 7 7840HS, 64 GB DDR5, RTX 4060 Laptop de 8 GB,
NVMe y Windows; con IQ3_XXS, visión en CPU y contexto configurado en 131.072,
reporta aproximadamente 180 tok/s de entrada y 27–32 tok/s de salida. Con
IQ2_XS declara 430 tok/s de entrada y 29–35 tok/s de salida. Son cifras de un
usuario, sin recibo de prompt, longitud efectiva, estado de caché, concurrencia
ni protocolo; no las tratamos como mediciones reproducibles. El texto indica
contexto configurado, no demuestra que una solicitud haya consumido 131K.

En comentarios, el autor explica que movió visión a CPU/RAM con `"gpu": false`.
Otro usuario declara cerca de 250 tok/s de prefill y 24 tok/s de generación en
una laptop i7; un usuario con 32 GB de RAM y dos RTX 3090 Ti comenta que obtuvo
mejor coding y análisis con Qwen3.6-35B-A3B o Qwen3.8-27B que con IQ3_XXS.
Son experiencias heterogéneas y no controles A/B. La documentación de Strata
describe soporte de CPU para visión, y Qwen publica 262.144 como longitud de
contexto nativa de Flash-Next; ninguno de esos datos valida la calidad local
de visión o retrieval largo en esta configuración.

Esta campaña local usó dos RTX 3090, Strata v0.1.41 y `max-context` 131.072,
pero el mayor prompt medido por Server Speed fue 38.804 tokens. Se intentó una
sonda sintética de retrieval de 115.015 tokens: el transporte se cortó cuando el
servidor procesaba 65.536 tokens, sin respuesta ni `usage` válido. No hay una
medición efectiva de 131K ni resultado de retrieval. La calidad y la velocidad
de contexto largo quedan **no evaluadas**; el valor configurado no equivale a
capacidad efectiva demostrada. Tampoco se midieron imágenes con
IQ3_XXS, Computer Usage E2E ni audio de Ingi-Charla. El árbol público de IQ3_XXS
está fijado a la revisión usada en esta prueba.

Fuentes de contexto: [modelo oficial Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next),
[configuración de visión y memoria de Strata](https://github.com/Niko1221/Strata/blob/main/docs/AI_SETUP.md)
y [tabla de modelos de Strata](https://github.com/Niko1221/Strata/blob/main/docs/MODELS.md).
Los datos publicados por otros usuarios —incluidos los de otro hardware y
runtime— no son un baseline directo para este A/B.

Dos problemas de preparación se corrigieron antes de contar resultados:
llamar setup.py con Python del sistema chocó con PEP 668 y se resolvió con
setup.sh y su entorno virtual; el asset binario v0.1.41 no estaba publicado
(HTTP 404) y el engine se compiló desde el commit fijado. También se corrigió
en los perfiles temporales la URL base del servidor: LlamaCode espera la raíz
del servicio y añade /v1 en sus llamadas. El intento previo con /v1 en la URL
fue cancelado y quedó fuera de los resultados.

No hubo cambios de C++, QML, harness ni perfiles productivos; por eso no
aplicaban build ni gates Linux. Los perfiles y modelos de evaluación quedaron
aislados. Informe y recibos completos: [artifacts/qwen38-flashnext-iq3xxs-strata-20261009/RESULTS.md](../artifacts/evaluacion-modelos-llamacode/Q-20261009-FLASHNEXT-IQ3XXS-AB/RESULTS.md).

Fuentes técnicas verificadas: [árbol IQ3_XXS fijado en Hugging Face](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/tree/1c04b8102ca5346f1faf4d9914503e378d713021/IQ3_XXS) y [reporte Strata #1616](https://github.com/Niko1221/Strata/issues/1616).

## Aclaración para el post de r/LocalLLM sobre 4×P100

La campaña de este informe se inició para un post diferente: Flash-Next IQ3_XXS en RTX 5060 Ti + Radeon R9700. La solicitud actual aporta [otro post](https://www.reddit.com/r/LocalLLM/comments/1wx3g89/strata_takes_the_promise_of_moe_models_just_need/), con Flash-Next Q4, KV q8, 262K, cuatro P100 PCIe 3 x8, 128 GB DDR4-2133 y E5-2683 v4, que afirma aproximadamente 2× frente a Qwen 27B y 5× frente a Flash-Next con llama.cpp modificado. Se conserva el mismo A/B IQ3_XXS/ASTRA como evidencia local relacionada, pero **no** se tratará como réplica: quant, hardware, contexto, backend/control, configuración y medición difieren. No hay una corrida local Q4/4×P100 ni una comparación apareada con la variante llama.cpp mencionada. El análisis acumulativo y el material de fuente están en [evaluación canónica](evaluacion-modelos-llamacode.md) y [artefactos de la tarea](../artifacts/evaluacion-modelos-llamacode/Q-20261009-FLASHNEXT-IQ3XXS-AB/).

| Uso | Qué aporta el post | Veredicto para LlamaCode |
|---|---|---|
| Coding/agentes | No incluye tareas, harness ni verificador reproducible. | No aporta evidencia para cambiar SOL/ASTRA; el A/B local de IQ3_XXS es otra quant y otra receta, y no se promueve. |
| Computer Usage | No reporta acciones en GUI ni estado final verificable. | No evaluado. |
| Ingi-Charla | No incluye audio, ASR ni TTS. | No evaluado; no se infiere calidad de voz desde texto. |
| Visión | El reclamo no reporta corpus ni métricas visuales. | No evaluado; soporte de visión en CPU es una ruta de ejecución, no una medida de calidad. |
| Contexto | Declara 262K configurado, sin longitud efectiva ni retrieval verificable. | Smoke local bloqueado por la guarda de recursos; no hay resultado para IQ3_XXS en 262K ni réplica Q4/4×P100. |
| Rendimiento | Afirma aproximadamente 2× y 5×, sin datos crudos/configuración que permitan reconstruirlos. | No verificable. La prueba local de Server Speed fue 2×3090, contexto máximo 131K y prompts hasta 38.804 tokens: no es baseline compatible. |

El probe de contexto a 262K quedó **bloqueado por precondición de recursos** antes de cargar el engine: MemAvailable era 110,564 GiB, pero swap usado 3,253 GiB, por encima del límite preregistrado de 2 GiB. No se generó ni envió el prompt; no hay score de contexto. Config: [iq3_xxs-context262k.json](../artifacts/evaluacion-modelos-llamacode/Q-20261009-FLASHNEXT-IQ3XXS-AB/receipts/configs/iq3_xxs-context262k.json); plan y recibo del guard en el directorio canónico.
