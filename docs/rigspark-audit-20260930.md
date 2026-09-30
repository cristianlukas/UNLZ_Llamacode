# Auditoría de RigSpark frente a LlamaCode — 2026-09-30

## Alcance

Se contrastó el post de r/LocalLLM y el repositorio público de RigSpark con las
pruebas y capacidades ya presentes en este checkout. El objetivo fue detectar
una mejora demostrable para perfiles/modelos, Ingi Charla, Computer Use o el
harness, sin repetir campañas de calidad de modelos ya documentadas.

Fuentes externas revisadas:

- [Repositorio y README de RigSpark](https://github.com/shashankswe2020-ux/rigspark)
- [Guía de referencia, catálogo y método de recomendaciones](https://github.com/shashankswe2020-ux/rigspark/blob/main/docs/references/guide.md)
- [Post de r/LocalLLM](https://www.reddit.com/r/LocalLLM/comments/1wtm5qy/rigspark_hardware_aware_local_llm_management/)

La guía consultada describe recomendaciones `yes / slow / no`, rangos
estimados de tokens/s, coste de KV/contexto, procedencia de catálogo y varios
backends. Aclara que son estimaciones, no benchmarks; los datos desconocidos
permanecen como desconocidos. Su catálogo es curado y tiene una auditoría
semanal de frescura/cobertura; las novedades encontradas requieren revisión
antes de entrar al catálogo.

## Comparación con lo que ya tenemos

| Área | Evidencia actual de LlamaCode | Decisión |
|---|---|---|
| Recomendación por hardware | `ModelRootsPage` ya ordena un catálogo offline de ~900 GGUF por RAM/VRAM, modo de ajuste, velocidad estimada y caso de uso. Separa carriles general, reasoning y código. | RigSpark no justifica reemplazar este flujo ni importar su implementación. |
| Modelo señalado en el comentario | `assets/hwfit/hf_models.json` contiene Qwen3.6-27B y Qwen3.6-35B-A3B, además de fuentes GGUF. El perfil QWEN35-A3B registra el Qwen3.6-35B-A3B y tiene evidencia local: contexto 262K, visión 4/4, HE0 1/1 y HE20 histórico 20/20; BCB actual/histórico no alcanza evidencia para desplazar SOL. | No cambiar el perfil recomendado ni volver a probar Qwen3.6 sólo para comprobar su presencia: ya está registrado y medido. |
| Frescura del catálogo | LlamaCode actualiza Artificial Analysis en segundo plano, pero el catálogo hardware-fit y las prioridades curadas son datos empaquetados; no encontramos un estado visible equivalente de revisión/corte del catálogo. | Sí transferir el concepto de procedencia/frescura: en una futura mejora, mostrar fecha/revisión y distinguir catálogo inspeccionado de benchmarks locales. No automatizar la admisión de novedades. |
| Runtime | RigSpark puede enlazar Ollama, llama.cpp, MLX y LM Studio; LM Studio es attach-only. LlamaCode compone binarios/perfiles, vLLM y llama.cpp y conserva recetas locales medidas. | No añadir perfil: es gestión de backends, no evidencia de superioridad de un modelo. |
| Harness / Computer Use | Ya hay campañas de calidad/convergencia del Harness y pruebas de Computer Use de exactitud, seguridad, validez y latencia; el código de tools y las aprobaciones cubren ejecución real. | No trasladar agentes/MCP ni decisiones finitas de RigSpark: no son prueba de mejor harness o control de escritorio. |
| Ingi Charla | La auditoría de voz local del 2026-09-18 ya comparó arquitectura STT/LLM/TTS, estado de Parakeet/Pocket TTS y las pruebas nativas; falta corpus acústico español comparable para promover motores. | RigSpark no aporta evidencia de voz ni una mejora aplicable a Charla. |

## Pruebas anteriores que cubren la pregunta

No repetir en esta auditoría: LC-H1 de QWEN35-A3B ni la matriz de calidad de
perfiles. Las referencias son:

- [`docs/profile-validation-matrix-20260914.md`](profile-validation-matrix-20260914.md)
  y [`docs/harness-quality-campaign-20260915.md`](harness-quality-campaign-20260915.md)
  para HE0/HE20/BCB y promoción.
- [`docs/model-inventory-20260918.md`](model-inventory-20260918.md) para la
  identidad de los artefactos presentes, y
  [`docs/benchmark-final-table.md`](benchmark-final-table.md) para la lectura
  operativa de QWEN35-A3B frente a SOL y otros candidatos.
- [`docs/ingicharla-local-voice-audit-20260918.md`](ingicharla-local-voice-audit-20260918.md)
  para la evaluación previa de Ingi Charla.
- [`docs/computer-use-sandwich.md`](computer-use-sandwich.md) y
  [`docs/opensourcejev-computer-use-audit-20260921.md`](opensourcejev-computer-use-audit-20260921.md)
  para prompt-order, seguridad y decisiones tipadas de Computer Use.

En esta auditoría se verificó además que el catálogo hardware-fit parsea como
JSON, incluye Qwen3.6-35B-A3B con su variante GGUF y que el checkout registra el
perfil curado QWEN35-A3B. La máquina de validación reporta 2× RTX 3090 de 24
GiB. Estas verificaciones son de catálogo/configuración; no son una medición
nueva de calidad o throughput.

## Resultado de pruebas del checkout

Se ejecutó `./scripts/tests-linux.sh Release` para comprobar las pruebas de
catálogo/perfiles y el estado general de este checkout. `test_catalog` y
`test_system_profiles` pasaron. El resumen visible llegó a 76/77; `test_agent_tools`
falló en dos aserciones de mensajes de error para
`desktopControls_invalidWindowErrorsCleanly` y
`desktopLaunch_emptyAppErrorsCleanly` (43 casos pasaron, 2 fallaron). La
ejecución quedó esperando en `ctest` mientras había otra corrida
`tests-linux.sh` usando la misma caché/build, por lo que se interrumpió esta
invocación después de capturar ese resultado; el gate completo no se declara
pasado. La causa probable de esas dos aserciones es la colisión entre corridas:
Computer Use usa un lock de escritorio global por proceso de aplicación, y dos
CTest simultáneos comparten ese estado; la prueba espera el prefijo de error
específico de cada tool, mientras una sesión ocupada puede devolver el error
del guard global. Hace falta repetir `test_agent_tools` en serie cuando termine
la otra corrida para confirmarlo. Estas fallas no prueban ni refutan las
conclusiones sobre catálogo y no se atribuyen a RigSpark ni a esta comparación.

## Decisión y criterio para una prueba futura

No se modificaron perfiles, sampling, harness, Computer Use ni Ingi Charla: la
publicación no demuestra una receta superior, y la versión Qwen3.6 mencionada
ya está en nuestro catálogo/perfil con evidencia local. La mejora que sí vale
la pena preservar es el control de frescura del catálogo. Para reconsiderar una
integración, primero comparar el mismo hardware y objetivo de tarea con
recomendaciones explicables que registren versión, fecha, requerimiento de RAM/
VRAM/contexto, incertidumbre de la estimación y score local disponible; luego
probar una novedad propuesta con el flujo de evaluación existente antes de
promoverla.

## Comparación ejecutada: Rigspark 2.1.0 vs. LlamaCode — 2026-09-30

Se descargó a `/tmp` el archivo oficial Linux x86_64 de Rigspark v2.1.0 y se
verificó su SHA-256 contra el digest de la API pública de GitHub:
`c1ad24a36f2754b8e355e579b1f7949a809ad32436764cd5193808a474335c2f`. Se aisló
`RIGSPARK_HOME` bajo `/tmp/rigspark-comparison-20260930/state`; no se instalaron
modelos ni servidores y no se consultó ningún backend local.

Hardware observado: **2× RTX 3090, 24 GiB cada una**. Rigspark doctor informó
24,0 GiB de memoria utilizable para la recomendación general. En la salida de
`plan` sí enumeró ambas GPU.

Comandos de recomendación, en el mismo host y a 32K:

```bash
rigspark recommend --task code --context 32768 --backend llamacpp --json
rigspark recommend --task tools --context 32768 --backend llamacpp --json
rigspark can-run qwen3.6:35b --context 32768 --json
rigspark plan qwen3.6:35b --context 32768 --json
```

| Prueba | Resultado observado |
|---|---|
| `recommend --task code` | Qwen3:30B-A3B, rango estimado 256,6–476,5 tok/s, quedó primero. Qwen3.6-35B-A3B apareció en `wontFit` como `vram-bound`. |
| `recommend --task tools` | El mismo Qwen3:30B-A3B quedó primero con la misma estimación. |
| `can-run qwen3.6:35b` a 8K, 32K y 64K | `no`, `vram-bound`; requiere 26.014.498.092 bytes frente a 25.769.803.776 utilizables. En las tres ventanas informó `contextFitKnown=false` y el mismo requerimiento, así que esta consulta no pudo separar el coste de KV/contexto del tamaño base. |
| `plan qwen3.6:35b` a 32K | La ruta de una GPU no cabe; la ruta `multi-gpu` sí: 51.539.607.552 bytes utilizables, 2 GPU. Throughput y geometría KV quedaron `unknown`. |

Esto reproduce en la versión más reciente el síntoma del post, pero aclara su
causa: el catálogo ya incluye Qwen3.6 y la planificación individual encuentra
una ruta para dos GPU; el ranking general sigue decidiendo con la VRAM de una
sola tarjeta. El rango de throughput para Qwen3:30B-A3B es una estimación de
Rigspark, no una medición; la propia guía dice que sus estimates no son
benchmarks y que throughput desconocido debe seguir como `unknown`.

### Contraste con evidencia de LlamaCode

LlamaCode tiene el perfil local **QWEN35-A3B — Qwen3.6-35B-A3B AutoRound INT4,
vLLM TP2/P2P**: 262K validado, visión 4/4 y resultados de Harness registrados
(HE0 1/1, HE20 20/20 histórico; BCB 4/8 en la evidencia disponible). Las
mediciones de velocidad documentadas son 123,98 tok/s durante BCB y 134,4 tok/s
directos. No se usan como cifras equivalentes: el 123,98 viene del BCB y el
134,4 del test directo. Esta evidencia local permite elegir la receta
Qwen3.6 cuando se priorizan contexto, visión y una ruta TP2 ya medida; el
resultado de Harness no permite promoverla por encima de SOL.

La comparación también encontró dos superficies distintas dentro de
LlamaCode: `launchMenu()` suma `vramTotalGb` para mostrar perfiles multi-GPU,
mientras `rebuildModelRecommendations()` puntúa el catálogo usando
`vramGb` (la tarjeta de mayor memoria) y RAM. Además, `rescanHardware()` sólo
rellena `ramGb` en el bloque `Q_OS_WIN`; la ruta Linux deja ese valor en cero.
En este checkout Linux, eso puede esconder modelos que requieren más que la
VRAM de una sola tarjeta en la vista de recomendaciones, aunque la máquina
tenga RAM y dos GPU. El test comparativo no cambió ese código: hace falta una
corrección separada con prueba de regresión antes de afirmar que el catálogo
genérico de LlamaCode estima bien el fit multi-GPU/Linux.

### Decisión

Para el equipo 2×3090, **LlamaCode queda por delante en evidencia operativa del
perfil Qwen3.6 local**; Rigspark aporta una vista de planificación que explicita
el camino multi-GPU y conserva throughput/KV como desconocidos cuando no puede
estimarlos. Rigspark no es superior en la recomendación de este hardware: su
orden principal omite el candidato que su propia ruta multi-GPU declara
ejecutable. No repetir esta comparación con Qwen3:30B/Qwen3.6 en las mismas
ventanas salvo que cambien el catálogo, Rigspark corrija el ranking multi-GPU o
LlamaCode cambie su cálculo de hardware.
