# Resultados — Q-20261010-STRATA-QUANTS-89TASKS

**Estado: auditoría documental completada; sin benchmark local ni promoción.** El post aporta una buena idea para presentar calidad, tiempo por tarea y tokens de salida, pero su clasificación de quants no está confirmada para LlamaCode.

## Resultado publicado

El gráfico del autor muestra 89 tareas con hidden-test grading, sampling mixto y hasta 40 turnos. Las tasas son un screening de una sola corrida por perfil:

| Perfil publicado | Thinking | Aciertos | Porcentaje del gráfico |
|---|---:|---:|---:|
| Base IQ3_S | high | 53/89 | 60% |
| Base IQ3_XXS | high | 57/89 | 64% |
| Base IQ3_XXS | medium | 46/89 | 52% |
| Base IQ3_XXS | low | 50/89 | 56% |
| Coder IQ1_M, expertos podados | high | 51/89 | 57% |
| Swift IQ3_XXS | high | 48/89 | 54% |
| Swift IQ3_XXS | medium | 47/89 | 53% |
| Swift IQ3_XXS | low | 42/89 | 47% |
| Tiel-Coder 35B A3B, UD-IQ4_XS | high | 33/89 | 37% |

El autor dice que los 89 casos son mayormente tareas Aider Polyglot de Python y JavaScript, más siete casos propios de trabajo sobre repositorios que no están listos para publicarse. El repositorio público Aider contiene ejercicios Exercism en seis lenguajes, así que el gráfico no equivale a ejecutar el suite público completo. La hoja del post además combina Strata 0.1.39/0.1.40/0.1.41 y un build identificado como `b1-27c5b4`; falta asociar cada punto a su fingerprint preciso.

Las barras usan Wilson 95% por tasa de tareas resueltas, según el autor. Se solapan para IQ3_XXS-high y IQ3_S-high; el autor mismo interpreta su diferencia como margen/ruido. Estos intervalos no son una comparación apareada por tarea ni incorporan variación entre semillas. Por ello, 57/89 frente a 53/89 no demuestra que IQ3_XXS supere a IQ3_S.

El autor informa aproximadamente cinco horas por una corrida completa y dice que más de 200 casos mejorarían la precisión, pero que no quiere invertir ese cómputo. El límite del usuario es ≤30 minutos por perfil para tres seeds: no ejecuté la suite. Además de exceder el presupuesto, faltan los siete prompts y verificadores privados y la configuración exacta del harness Pi, las seeds y los recibos por tarea. No hay una réplica que podamos reclamar.

## Qué sirve para LlamaCode

- **Sí adoptar como visualización complementaria:** presentar puntaje frente a tiempo de pared por tarea/perfil y tokens de salida por tarea, además del puntaje medio. Eso hace visibles los trade-offs de calidad, latencia y verbosidad.
- Mantener el máximo de contexto equivalente y documentar el thinking; la respuesta del autor confirma que intentó comparar su uso diario con contexto máximo fijo.
- Reportar incertidumbre, pero para nuestro A/B mantener seeds pareadas, resultados por escenario y seguridad; los Wilson del post son una referencia descriptiva, no el gate de promoción.
- **No adoptar sus números como ranking local:** suite parcialmente privada, mezcla de builds, runtime/hardware y harness diferentes, solo una observación por perfil.
- El Coder no es simplemente un modelo con pesos almacenados a 1 bit. La ficha oficial dice que elimina 256 de 512 expertos por capa y cuantiza a 3.5 bpw el resto (efectivo 1.89 bits por parámetro original). El score público está etiquetado IQ1_M, pero el tipo no describe el ancho de cada peso retenido.

## Comparación con evidencia ya medida en LlamaCode

La siguiente tabla conserva los 28 escenarios Hard Mode × 3 seeds que sí tenemos. Los tiempos de Q4, ASTRA y SOL son los totales de perfil aportados antes por el usuario; los recibos de esa campaña no conservan la división de pared por semilla. IQ2_XS sí tiene tiempo por semilla en su recibo. Los perfiles MTP-on/off se dejan fuera del conjunto de interés porque tardaron mucho más de 30 minutos en total. La columna de TPS es la de Hard Mode; las sondas de contexto se muestran aparte y no alteran puntajes ni tiempos de estas semillas.

| Perfil local completo | Semilla 42 · puntaje — tiempo | Semilla 43 · puntaje — tiempo | Semilla 44 · puntaje — tiempo | Media — tiempo total 3 seeds | TPS observados en Hard Mode | TC-92 | Probe de contexto | Archivos disponibles |
| --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| Flash-Next Q4 · Strata | 78,57 — n/d | 69,64 — n/d | 83,93 — n/d | **77,38 — 27:28** | 65,3 media; 64,9 mediana | Falló 3/3 | n/d | Sí · 4/4 shards |
| ASTRA IQ3_S calibrado · Strata | 73,21 — n/d | 75,00 — n/d | 66,07 — n/d | **71,43 — 13:09** | 133,1 media; 133,7 mediana | Falló 3/3 | n/d | Sí · 2/2 shards |
| SOL Qwen3.8-27B AutoRound INT4 · vLLM | 55,36 — n/d | 66,07 — n/d | 76,79 — n/d | **66,07 — 18:40** | 70,2 media; 77,6 mediana | Falló 1/3 | n/d | Sí · 7/7 shards |
| ISTA IQ2_XS · Strata | 80,36 — 3:37 | 76,79 — 3:30 | 76,79 — 3:58 | **77,98 — 11:05** | 154,19 media; 153,05 mediana en logs de esta suite | Falló 3/3 | 131K–1M; NIAH 10/10 en los cuatro puntos | Sí · 2/2 shards |

### Probe corto de contexto de ISTA IQ2_XS/Strata

Estas mediciones complementan la tabla Hard Mode; no son puntajes de calidad ni TPS de esa suite. Se usó una solicitud sintética por límite, `max_tokens=64`, greedy/seed 4242, sin caché, en serie sobre las dos RTX 3090. Los prompts ocuparon al menos 95% del contexto. 131K y 262K fueron nativos; 512K usó YaRN ×2 y 1M YaRN ×4 (contexto original 262.144).

| Contexto máximo | Prompt real / ocupación | Prefill / decode TPS | TTFT / tiempo de petición | RAM pico RSS / MemAvailable mínima | VRAM GPU0 total (Δ) / GPU1 total (Δ) |
|---:|---:|---:|---:|---:|---:|
| 131.072 nativo | 124.535 (95,013%) | 3.265,5 / 139,1 tok/s | 38,14 / 38,64 s | 39,23 / 68,35 GiB | 23.734 (+22.679) / 20.776 (+20.668) MiB |
| 262.144 nativo | 249.146 (95,042%) | 3.163,8 / 133,2 tok/s | 78,75 / 79,31 s | 40,89 / 66,60 GiB | 23.782 (+22.725) / 20.906 (+20.798) MiB |
| 524.288 · YaRN ×2 | 498.122 (95,009%) | 2.860,8 / 113,1 tok/s | 174,12 / 174,86 s | 44,31 / 63,22 GiB | 23.352 (+22.335) / 21.912 (+21.804) MiB |
| 1.048.576 · YaRN ×4 | 996.163 (95,002%) | 2.232,9 / 85,6 tok/s | 446,13 / 447,24 s | 51,14 / 55,64 GiB | 23.822 (+22.803) / 22.454 (+22.346) MiB |

El RSS es la suma de server y engine; MemAvailable es el mínimo de RAM disponible estimado por el sistema. La VRAM indica el pico total por tarjeta y, entre paréntesis, el incremento sobre el uso base. El tiempo total es el de la solicitud y excluye la carga inicial del modelo. Cada punto tiene una sola corrida; la respuesta terminó al tope de 64 tokens, así que el ensayo confirma carga y rendimiento de una solicitud corta, pero no aciertos de recuperación ni calidad semántica a 1M. El perfil ASTRA DEFAULT permanece configurado a 131.072 tokens. No se vació el swap; al terminar había 107,375 GiB de RAM disponible. [Informe completo y recibos crudos](../Q-20261014-ISTA-CONTEXT-SWEEP/RESULTS.md).

### Seguimiento de calidad: Needle in a Haystack sintético

El probe anterior sólo midió carga y TPS con 64 tokens de salida; no puntuaba recuperación. Este seguimiento usa los mismos prompts de 95% de ocupación y diez hechos distribuidos aproximadamente del 5% al 95%, y permite hasta 768 tokens para devolver el JSON completo. ISTA obtuvo 10/10 coincidencias exactas en cada tamaño. Es un screening sintético interno, con una corrida por punto; no equivale a una réplica de un benchmark externo ni demuestra calidad general a contexto largo.

| Contexto | Prompt / ocupación | Puntaje | Prefill / decode TPS | TTFT / solicitud / sesión total | RAM pico RSS / MemAvailable mínima | VRAM GPU0 total (Δ) / GPU1 total (Δ) |
|---|---:|---:|---:|---:|---:|---:|
| 131.072 nativo | 124.535 (95,013%) | **10/10** | 3.279,0 / 148,0 tok/s | 37,98 / 39,43 / 54,98 s | 39,17 / 68,05 GiB | 23.747 (+22.659) / 20.808 (+20.700) MiB |
| 262.144 nativo | 249.146 (95,042%) | **10/10** | 3.168,1 / 134,2 tok/s | 78,64 / 80,28 / 96,14 s | 40,89 / 66,32 GiB | 23.797 (+22.716) / 20.938 (+20.830) MiB |
| 524.288 YaRN ×2 | 498.122 (95,009%) | **10/10** | 2.850,7 / 120,5 tok/s | 174,74 / 176,64 / 194,49 s | 44,31 / 62,72 GiB | 23.371 (+22.251) / 21.944 (+21.836) MiB |
| 1.048.576 YaRN ×4 | 996.163 (95,002%) | **10/10** | 2.230,1 / 98,4 tok/s | 446,69 / 449,17 / 467,63 s | 51,14 / 55,73 GiB | 23.808 (+22.773) / 22.474 (+22.366) MiB |

Las corridas tardaron **13:33** en total incluyendo carga y cierre de cada servidor (solicitudes: **12:25**). Cada respuesta fue de 209 tokens y terminó normalmente. Sin swap-out ni presión PSI; el swap no se vació. Los fixtures mantuvieron las posiciones y hashes del probe anterior, cuyos recibos no incluían score de recuperación. [Informe completo y recibos](../Q-20261014-ISTA-NEEDLE-HAYSTACK/RESULTS.md).

El score perfecto sólo aplica a los diez hechos exactos de esta plantilla. No prueba preguntas paraphraseadas, contradicciones, recuperación multi-hop ni repetibilidad entre seeds. 512K/1M son YaRN ×2/×4 desde 262.144; ASTRA DEFAULT sigue configurado en 131.072.

**Disponibilidad local revisada el 2026-10-14:** los cuatro conjuntos de pesos están presentes en la partición `Disco local` (`/dev/nvme0n1p2`, NTFS). Se confirmó la presencia de todos los shards esperados; no se descargaron ni se volvieron a calcular sus hashes.

- Flash-Next Q4 · Strata: `/media/cristian/Disco local/Strata-UD-Q4-review-20261003/models/unsloth-UD-Q4_K_XL/` — 4 archivos GGUF, `Qwen3.8-Flash-Next-UD-Q4_K_XL-00001-of-00004.gguf` a `00004-of-00004.gguf`.
- ASTRA IQ3_S calibrado · Strata: `/media/cristian/Disco local/Models/ASTRA-IQ3_S-calibrated-20261006/models/IQ3_S/` — 2 archivos GGUF, `Qwen3.8-Flash-Next-GSQ-RCO-IQ3_S-00001-of-00002.gguf` y `00002-of-00002.gguf`.
- SOL Qwen3.8-27B AutoRound INT4 · vLLM: `/media/cristian/Disco local/Models/llamacpp/club-3090/qwen3.8-27b-autoround-int4/` — 7 shards safetensors y `model_extra_tensors.safetensors`.
- ISTA IQ2_XS · Strata: `/media/cristian/Disco local/Models/FlashNext-IQ2XS-ISTA-Strata-eval-20261012/IQ2_XS/` — 2 archivos GGUF, `Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS-00001-of-00002.gguf` y `00002-of-00002.gguf`.

**Lectura de la tabla local:** Q4, ASTRA y SOL cumplen el corte de tiempo. IQ2_XS también lo cumple y tuvo el score medio más alto, pero reveló datos de otro tenant en TC-92 en las tres semillas; no lo recomiendo para agentes con herramientas o permisos. Q4 falló el mismo aislamiento TC-92 en sus tres semillas; ASTRA también. SOL falló TC-92 una vez. Los tres perfiles tuvieron resultado parcial en TC-97 en todas sus semillas. El puntaje agregado no borra esos gates de seguridad.

Los tiempos/tok/s de estos perfiles no son una comparación pura de pesos: SOL corrió vLLM y los otros Strata; además hay diferencias de modelos y perfiles efectivos. Las semillas 42/43/44 se mantuvieron en la suite local Hard Mode 2.8.0. Esta tabla no mide las 89 tareas del post.

### Perfiles excluidos por tiempo

| Perfil | Score | Tiempo | Motivo |
|---|---:|---:|---|
| Q4 llama.cpp MTP-on | 82,14 | 1:59:27, tres seeds | Excede el límite de 30 min |
| Q4 llama.cpp MTP-off | 80,36 | 2:15:27, tres seeds | Excede el límite de 30 min |
| Saluki IQ2-mix | 76,79 en 2 seeds | 21:01; proyección de tres seeds 31:31 | Corrida incompleta y proyección sobre el límite; además fallos críticos de autorización/seguridad |

IQ3_XXS y Coder tienen evidencia local diferente y no entran a la tabla Hard Mode 28×3: IQ3_XXS/Strata hizo HE20+BCB8 24/28 en una corrida frente a 28/28 para ASTRA, obtuvo 11/13 final en TaskFlow y 126,59 tok/s en dos pasadas de Server Speed; el Coder IQ1_M tuvo un BCB-Hard-8 histórico de 2/8 en una corrida. Esas suites no predicen la tasa de 89 tareas.

## Conclusión y próxima acción

No descargar pesos, crear perfiles nuevos ni correr una prueba de cinco horas por brazo. No promover IQ3_XXS, Coder, Swift ni Tiel con base en este post. Ya existe evidencia local que responde mejor a la pregunta operacional y respeta el límite temporal; falta cerrar TC-92 antes de recomendar cualquiera de los perfiles para acciones con datos de tenants.

Si el autor libera los siete casos y los verificadores/harness, reconsiderar sólo una versión recortada de tres semillas cuya proyección completa no pase 30 minutos. Una futura tabla local debería incluir tiempo de pared y tokens por tarea junto al resultado y preservar las desgloses de cada seed.

## Artefactos y fuentes

- Plan y umbrales: [PLAN.md](PLAN.md).
- Transcripción de fuentes y métricas: [source-review.json](receipts/source-review.json).
- Decisión de no ejecutar: [local-preflight.json](receipts/local-preflight.json).
- Gráficos recibidos del post: [calidad por quant](receipts/charts/score-by-quant.png), [calidad vs tiempo](receipts/charts/quality-vs-time.png), [calidad vs tokens](receipts/charts/quality-vs-output-tokens.png).
- [Post original de Reddit](https://www.reddit.com/r/LocalLLM/comments/1x1pvkt/benchmarked_some_strata_qwen38flashnext_quants/), [card GSQ-RCO](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF), [card Coder](https://huggingface.co/ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF), [release Strata v0.1.38](https://github.com/Niko1221/Strata/releases/tag/v0.1.38), [Aider Polyglot](https://github.com/Aider-AI/polyglot-benchmark) y [documentación del runner Aider](https://github.com/Aider-AI/aider/blob/main/benchmark/README.md).
