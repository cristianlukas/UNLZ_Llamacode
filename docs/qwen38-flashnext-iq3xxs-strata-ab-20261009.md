# A/B Qwen3.8-Flash-Next IQ3_XXS vs ASTRA IQ3_S — 2026-10-09

## Resultado

No promover IQ3_XXS a un perfil productivo. En LC-H1 completo (HE20, BCB8 y
Intelligence Adversarial v1) más TaskFlow ULTRA obtuvo 45/51 criterios
finales; ASTRA IQ3_S calibrado obtuvo 51/51. La primera pasada formal fue
42/51 para IQ3_XXS y 41/51 para ASTRA. HE0, corrido como prerrequisito
separado, pasó 1/1 para ambos.

ASTRA cerró las cuatro suites principales unos 306 s antes. IQ3_XXS tuvo una
ventaja de TTFT en las dos corridas de Server Speed v1, pero la diferencia
media de decode fue sólo 3,7% y los rangos de tok/s se solapan. La evidencia
de calidad no respalda cambiar el perfil.

## Calidad

Los dos modelos usaron la misma definición de suite, Strata v0.1.41 y la misma
configuración efectiva por pareja. La tabla separa el score de la primera
pasada del resultado final. Los tiempos muestran segundos hasta completar la
primera pasada y segundos totales, incluidas las reparaciones.

| Suite | IQ3_XXS: primera → final | Reparaciones; primera / total (s) | IQ3_XXS tok/s; TTFT | ASTRA: primera → final | Reparaciones; primera / total (s) | ASTRA tok/s; TTFT |
|---|---:|---:|---:|---:|---:|---:|
| HE0 prerrequisito, fuera de LC-H1 | 1/1 → 1/1 | 0; 9,762 / 10,062 | 148,02; 58,00 ms | 1/1 → 1/1 | 0; 10,762 / 11,063 | 140,06; 59,50 ms |
| LC-H1 · HumanEval 20 | 20/20 → 20/20 | 0; 694,943 / 695,244 | 133,38; 52,07 ms | 20/20 → 20/20 | 0; 703,204 / 703,505 | 124,20; 55,31 ms |
| LC-H1 · BigCodeBench-Hard 8 | 4/8 → 4/8 | 3; 290,095 / 324,900 | 127,43; 128,87 ms | 3/8 → 8/8 | 2; 318,929 / 565,300 | 123,88; 158,14 ms |
| LC-H1 · Intelligence Adversarial 10 | 7/10 → 10/10 | 2; 791,855 / 977,519 | 130,54; 69,54 ms | 8/10 → 10/10 | 2; 679,610 / 773,404 | 124,33; 71,15 ms |
| **LC-H1 subtotal (38 criterios)** | **31/38 → 34/38** | **5; 1.776,893 / 1.997,663** | — | **31/38 → 38/38** | **4; 1.701,743 / 2.042,209** | — |
| TaskFlow ULTRA (13 criterios) | 11/13 → 11/13 | 3; 194,221 / 693,392 | 139,36; 92,54 ms | 10/13 → 13/13 | 2; 237,987 / 342,831 | 123,80; 71,70 ms |
| **LC-H1 + TaskFlow (51 criterios)** | **42/51 → 45/51** | **8; 1.971,114 / 2.691,055** | — | **41/51 → 51/51** | **6; 1.939,730 / 2.385,040** | — |

IQ3_XXS terminó con cuatro fallos en BCB8 y dos en TaskFlow. ASTRA reparó
ambos grupos hasta 8/8 y 13/13, respectivamente, con el mismo tope de tres
reparaciones. En adversarial, ambos acabaron 10/10; IQ3_XXS tardó 977,519 s
y ASTRA 773,404 s. Los seis fallos finales del candidato se clasifican como
calidad, no como problemas de carga o infraestructura.

TaskFlow comparte la misma suite y HarnessSpec
sha256:cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef
que el historial. Sus criterios incluyen presencia de archivos, compilación,
unittest escrito por el modelo y self-test; estos dos últimos no son
verificadores independientes del contenido. La puntuación se presenta tal
cual, con esa limitación explícita.

### SOL Qwen3.8-27B AutoRound INT4

El recibo histórico válido disponible de SOL para TaskFlow ULTRA dio 0/13 en
primera pasada y 7/13 final, con tres reparaciones, 138,365 s, 42,90 tok/s y
TTFT 4.766,5 ms. Usó agent-maximo, reasoning budget 8192, temperatura 0,1,
semilla 4242 y la misma suite/HarnessSpec. Es una corrida única en vLLM TP2,
por lo que no iguala el backend Strata y no tiene medición de Server Speed
comparable en esta campaña. Fallos CUDA/MTP de intentos separados permanecen
clasificados como infraestructura y no entran al score.

No hay recibo SOL válido de LC-H1 con estas condiciones. Se informa SOL sólo
para TaskFlow y no se extrapola su resultado a otras suites.

## Server Speed v1

Dos corridas base por modelo usaron el benchmark nativo de LlamaCode, el mismo
corpus, dos pasadas, un calentamiento, sin concurrencia y sweep de prefill
habilitado. Cada corrida tiene 32/32 muestras válidas y cero fallidas. El
sweep solicitó hasta 65.536 tokens; el prompt más largo medido tuvo 38.804.

| Perfil | Decode tok/s (pasada 1, pasada 2; media y rango) | TTFT medio (pasada 1, pasada 2; media y rango) | Prefill tok/s medio |
|---|---:|---:|---:|
| ISTA IQ3_XXS, spec-min-p 0,70 | 133,40; 119,78 (126,59; 119,78–133,40) | 363,75; 377,50 ms (370,63; 363,75–377,50) | 1.924,30 |
| ASTRA IQ3_S, spec-min-p 0,70 | 120,32; 123,86 (122,09; 120,32–123,86) | 452,16; 449,84 ms (451,00; 449,84–452,16) | 1.874,18 |

IQ3_XXS mejoró TTFT 17,8% en media y fue menor en las dos pasadas. Su decode
medio fue 3,7% mayor, dentro de la variación observada entre corridas. Prefill
medio fue 2,7% mayor. El sweep no alcanza 255K, así que no valida el resultado
de contexto largo reportado en el post.

### Ablations de runtime

Cada variante de abajo se ejecutó una vez. Ninguna reemplaza la configuración
base:

| IQ3_XXS | Decode tok/s | TTFT medio | Observación |
|---|---:|---:|---|
| Control: spec-min-p 0,70, PCIe fraction 0,00, prefill auto | 133,40 | 363,75 ms | La repetición base fue 119,78 tok/s |
| spec-min-p 0,50 | 112,88 | 378,50 ms | Menor que el control |
| PCIe fraction 0,55 | 129,48 | 363,20 ms | Dentro de la variación del control |
| Prefill chunk 32.768 | 116,20 | 732,80 ms | Menor decode y mayor TTFT |

### Sondas de sampling

Se cambiaron temperatura y top-p de forma aislada en HumanEval/0, seed 4242,
top-k 20, min-p 0, repeat penalty 1 y presence penalty 0. Cada celda es una
respuesta sobre un solo ítem y no debe leerse como score de suite.

| Condición | IQ3_XXS | ASTRA IQ3_S |
|---|---:|---:|
| temp 0,6 / top-p 0,95 | pasa | falla |
| Sólo temp 0,7 | pasa | falla |
| Sólo top-p 0,8 | pasa | pasa |
| receta del post: temp 0,7 / top-p 0,8 | pasa | falla |

IQ3_XXS pasó las cuatro variantes en ese ítem. ASTRA produjo tres respuestas
sintácticamente inválidas y una válida con top-p 0,8. No se cambia el sampling
productivo con esta muestra. En las suites, la temperatura efectiva fue 0,1;
ambos perfiles conservaron top-p 0,95, top-k 20, min-p 0, repeat penalty 1 y
presence penalty 0.

## Entorno, memoria y preparación

- Hardware: dos NVIDIA RTX 3090 de 24 GiB, 123,6 GiB RAM y driver 610.57.04.
- Modelo nuevo: ISTA-DASLab Qwen3.8-Flash-Next GSQ-RCO IQ3_XXS, revisión
  1c04b8102ca5346f1faf4d9914503e378d713021, dos shards por 75.839.998.528 B.
- Runtime: Strata v0.1.41, commit fb58e0dbc8399662c0e47c76578c6e878b14f6cf,
  compilación local CUDA Toolkit 12.8.93 para sm_86. El asset del release dio
  HTTP 404, por lo que se compiló el source fijado.
- Config base común: max context 131.072, KV int8, 32.768 KV resident,
  MTP/spec 4, expert-cache auto, prefill auto, spec-min-p 0,70 y PCIe fraction
  0,00. Strata distribuyó capas 26/22. LC-H1 usó agent-maximo, thinking on,
  reasoning budget 4.096, semilla 4242 y tres reparaciones máximas; TaskFlow
  conservó esos valores con reasoning budget 8.192.
- Carga de expertos: IQ3_XXS 39,97 GiB a 2,50 GiB/s en 46 s; ASTRA 46,84 GiB
  a 1,63 GiB/s en 42 s. La lectura de /proc registró VmHWM de 47.818.136 KiB
  (45,60 GiB) para IQ3_XXS y 55.547.060 KiB (52,95 GiB) para ASTRA; swap del
  proceso en 0 KiB. Strata ocupó aproximadamente 23,6–24,0 GiB por GPU.
  Los recibos de aplicación no informaron RAM (0 MiB); /proc es suplementario.
- D terminó con 210.716.770.304 B libres. No se borraron pesos existentes ni
  se tocaron perfiles productivos. Los modelos y configuración temporal
  permanecen aislados.

La configuración de evaluación mantuvo Strata en contexto 131.072. El post
reporta prefill profundo y generación a 255K/262K sobre un RTX 5060 Ti 16 GB
CUDA y un R9700 32 GB HIP en contenedores separados, con Ryzen 5 7600 y 93 GB
RAM. Menciona 62 tok/s CUDA a contexto corto y 31–57 tok/s a 255K; en HIP,
40–52 tok/s y 18–31 tok/s a 255K. También atribuye 78–83% de aceptación MTP
al CUDA, 73% al HIP y 15/18 empates en su batería anecdótica. No hay recibos
crudos ni protocolo alineado; estos números no son una referencia directa
para dos RTX 3090.

Dos errores recuperables se resolvieron antes de cerrar las corridas: PEP 668
al invocar setup.py directamente se evitó usando setup.sh y su venv; la URL
base temporal se corrigió para que LlamaCode añada /v1. La prueba inicial de
readiness con /v1 duplicado fue cancelada y queda fuera de los resultados.
No hubo cambios de C++, QML, harness ni perfiles productivos, así que no
aplicaban build ni gates Linux. Al terminar se cerraron los servidores Strata
y el endpoint headless temporal.

## Recibos

Resultados normalizados y manifiesto de hashes:
[RESULTS.md del artefacto](../artifacts/qwen38-flashnext-iq3xxs-strata-20261009/RESULTS.md),
[results.json](../artifacts/qwen38-flashnext-iq3xxs-strata-20261009/results.json),
[manifest.json](../artifacts/qwen38-flashnext-iq3xxs-strata-20261009/manifest.json).
El snapshot de la fuente entregada por el usuario es
[Texto pegado.txt](/home/cristian/.codex/attachments/5f480279-e45d-4bcc-93bd-ca4d17ce623b/Texto%20pegado.txt).
Los shards IQ3_XXS corresponden al [árbol de Hugging Face fijado a revisión](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF/tree/1c04b8102ca5346f1faf4d9914503e378d713021/IQ3_XXS).
