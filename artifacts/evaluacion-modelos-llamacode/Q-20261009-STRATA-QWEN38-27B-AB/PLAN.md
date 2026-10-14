# Plan de evaluación — Q-20261009-STRATA-QWEN38-27B-AB

- **Estado:** completada el 2026-10-12 bajo token `1dc290d8-49eb-4a1e-9c48-7b191b5baa7c`; cierre registrado en la sección final.
- **Hipótesis:** comprobar si Qwen3.8-Flash-Next IQ2_XS ejecutado con Strata aporta una ventaja real de coding/agentes o velocidad frente al control Qwen3.8-27B Q4 local; separar claims publicados de resultados reproducibles.
- **Hardware reservado:** 2× RTX 3090, una sola configuración/modelo a la vez.
- **Política:** preservar perfiles productivos y HarnessSpec; no descargar pesos hasta verificar que no existe un artefacto compatible; registrar hashes, runtime, argumentos, contexto efectivo, sampling, seed, fingerprints y telemetría.

## Preflight pendiente

1. Recuperar el texto/origen exacto del claim IQ2_XS y verificar la publicación y documentación primaria de Strata.
2. Localizar pesos IQ2_XS y modelo control Qwen3.8-27B Q4; identificar revisiones y hashes sin duplicar huellas ya ejecutadas.
3. Confirmar perfil de control, harness, suites y fingerprints. Usar un protocolo apareado con configuración común cuando ambos runtimes lo permitan; si los runtimes difieren, informar el A/B como comparación de perfiles completos.
4. Comprobar RAM/swap, espacio, VRAM, procesos y runtimes; abortar antes de carga si no se cumplen las guardas documentadas.

## Pruebas

- Coding/agentes: HE0 → HE20 → BCB8; ADV v1 complementaria sólo si el harness y el tiempo lo permiten, siguiendo la evaluación Strata de referencia.
- Rendimiento: medir bajo receta declarada; no equiparar tokens/s de runtimes distintos sin advertirlo. Si se puede reutilizar Server Speed v1 con configuración válida, usar el mismo corpus y guardar muestras.
- Contexto, visión, Computer Usage y audio quedan fuera del screening salvo que los fixtures locales aplicables permitan prueba válida y se apruebe en el alcance.
- Una corrida por perfil es screening, no mejora estable; se requieren tres pares emparejados para una conclusión de mejora estable.

## Resultados

Preflight reanudado el 2026-10-12: no hay procesos `strata`, `llama-server` ni `vllm` visibles. La RTX 3090 0 está a 1186 MiB con Xorg/escritorio activo y reporta 66% de utilización; la RTX 3090 1 está a 108 MiB y 28% de utilización. Esto no confirma capacidad exclusiva/segura de doble GPU. Identificación de pesos, source claim y compatibilidad de runner siguen pendientes. No iniciar inferencia antes de completar esos controles.


## Interrupción antes de ejecutar

El 2026-10-10T19:34:31Z el usuario cambió el objetivo a corregir el prompt de campaña. La fila vuelve a Pendiente; no hubo descarga, servidor, inferencia ni benchmark. Retomar esta misma tarea/ID en su turno FIFO, rehaciendo preflight de recursos.


## Preflight de fuentes, peso y runtime — 2026-10-12

- Control SOL: pesos encontrados en /media/cristian/Disco local/Models/llamacpp/club-3090/qwen3.8-27b-autoround-int4 (18,996,706,072 bytes). Los siete shards y model_extra_tensors.safetensors coinciden byte a byte por SHA-256 con Frozenlock/Qwen3.8-27B-int4-AutoRound, revisión b4c61732c4f2d8af323d75ba5702b5c7f3361539. No descargar ni reconstruir este control.
- Candidato: el GGUF IQ2_XS no existe en las ubicaciones/cache de modelos examinadas. Fuente pública primaria ISTA-DASLab/Qwen3.8-Flash-Next-GSQ-RCO-GGUF, revisión fijada ed59f92082b1e93c0e96d60a8b11aab089b52f09; dos shards totalizan 68,026,093,024 bytes y SHA esperados registrados. Repo no gated; HF API reporta ambos shards como seguros. Se excluye el mmproj de visión (907,543,008 bytes) porque esta tarea mide coding/agente.
- Destino aislado previsto: /media/cristian/Disco local/Models/FlashNext-IQ2XS-ISTA-Strata-eval-20261012; df informó 197 GB libres en ese volumen. El destino no existía.
- Strata 0.1.41 ya está compilado (fb58e0dbc8399662c0e47c76578c6e878b14f6cf; binario SHA guardado en model-source-manifest.json). La receta MTP4 anterior usa spec=4, spec-min-p=.70, kv=int8, kv-resident=32768, max-context=131072, split GPU 0,1. El pack y las herramientas de preparación se verifican antes de generar un pack separado.
- Hardware observado sin servidor de inferencia: dos RTX 3090; GPU 0 ocupa 1,186 MiB con Xorg/escritorio, GPU 1 ocupa 108 MiB; RAM disponible 112 GiB, swap 0. No se interrumpe ningún proceso ajeno. Puertos del engine anteriores libres.
- Evidencia y recibos de fuente/preflight: model-source-manifest.json. La descarga sólo empezará tras dry-run a la revisión fijada y se verificará SHA-256 antes de cargar.

## Reanudación y alcance añadido — 2026-10-12

- SOL ya estaba descargado y verificado localmente; se reutilizó esa copia sin volver a descargar ni modificar sus pesos. La comparación oficial LCH1 de SOL se intentó con MTP4 y, tras fallar, sin MTP. Ambos intentos terminaron por `CUDA scatter gather index out of bounds`/conexión cerrada en vLLM 0.27.1, así que no cuentan como ceros de calidad. Los logs, eventos y salidas crudas permanecen en `receipts/logs/sol-vllm-*.log` y `receipts/lch1/`.
- El candidato IQ2_XS se descargó sólo después de comprobar que no existía una copia compatible; revisión y SHA-256 están en `model-source-manifest.json` y `receipts/iq2-sha256.txt`. El pack se generó en el directorio aislado de evaluación, sin cambiar los shards originales.
- Receta candidata cargada en Strata 0.1.41: ambas RTX 3090, MTP4, KV int8, contexto 131072, `spec-min-p=0.70`, prompt chunk auto y cache de expertos automática; endpoint local aislado `127.0.0.1:8351`. Se igualó el muestreo conservador del perfil y se activó `agent-maximo`/thinking para la escalera oficial.
- Coding/agentes: ejecutar HE0 → HE20 → BCB8 con el harness oficial de LlamaCode; conservar clasificación por corrida e invalidar por infraestructura sólo etapas realmente afectadas.
- Tool-use difícil: añadir `tool-eval-bench` Hard Mode **28 tareas × 3 semillas (42/43/44)** para IQ2_XS. Reutilizar como controles históricos los resultados completos de SOL, ASTRA IQ3_S calibrado y Flash-Next Q4 de `Q-20261010-FRONTIER-MULTITASK-AB`, cuya versión 2.8.0, escenarios TC-70…TC-97, parámetros y fingerprints constan en sus recibos. Identificar la lectura como comparación entre perfiles/runtimes completos y no atribuir diferencias sólo a los pesos. No repetir SOL mientras su control vLLM conserve el fallo reproducible de CUDA; si la tarea necesita A/B simultáneo, dejarlo inconcluso por esa causa.
- Añadir TaskFlow ULTRA (13 criterios) al screening de agente si el servicio/harness permanece sano y separar score inicial, reparaciones y verificaciones. Medir TPS y tiempo de pared únicamente desde recibos/logs válidos; no inferir velocidad de corridas abortadas.

## Cierre y resultados — 2026-10-12

- **Control SOL:** los pesos ya estaban descargados en `/media/cristian/Disco local/Models/llamacpp/club-3090/qwen3.8-27b-autoround-int4`; se verificaron contra el repo/revisión del manifiesto y se reutilizaron. No se re-descargaron ni modificaron.
- **IQ2_XS/Strata:** screening en dos RTX 3090. Huella de perfil `1906a54af838d39dbf3d8fc4ccfbc71bcf0985927869068dfb5e5aba4ff223bc`; HarnessSpec `cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`. HE0 1/1 (0/1 inicial), HE20 20/20 (19/20 inicial), BCB8 8/8 (3/8 inicial); una reparación en cada etapa y ninguna incidencia de infraestructura.
- **Hard Mode 28×3:** semillas 42/43/44: 45/56, 43/56, 43/56; media 43,67/56 = 77,98/100. Comparado con controles históricos de igual suite/semillas: Q4 77,38; ASTRA IQ3_S 71,43; SOL 66,07. IQ2_XS aventajó a Q4 por sólo 0,62 pp y falló TC-92 (divulgación entre tenants) las tres veces; no se promueve. TPS derivado de logs en este bloque: media 154,19, mediana 153,05, ponderada por tokens 149,84; el runner tardó 11:05 para las tres semillas.
- **TaskFlow ULTRA:** 0/13 inicial → 13/13 final tras tres reparaciones (298,338 s; 49 llamadas). Los tests de unidad fueron generados por el modelo y no son verificación independiente. **ADV v1:** 6/10 inicial → 10/10 final tras una reparación (444,679 s; 37 llamadas). Ninguna de estas suites tuvo timeout ni fallo de infraestructura.
- La suma de los tiempos reportados por HE0, HE20, BCB8, Hard Mode (tres semillas), TaskFlow y ADV es 41:27,467; excluye descarga/preparación y ~51 s de carga inicial. No es una medición Server Speed independiente.
- **LCH de SOL:** los dos intentos con los pesos locales reutilizados, primero MTP4 y luego sin MTP, terminaron por assert CUDA en vLLM 0.27.1. Son inválidos por infraestructura, no ceros de calidad. Hard Mode conserva controles históricos válidos; SOL no se repitió localmente bajo esta receta.
- Se conservaron logs, JSON, configuraciones, eventos y corridas crudas bajo `receipts/`. Se detuvo el servidor Strata propio y se confirmó cerrado el puerto 8351; no se tocaron procesos ajenos. GPU0 conserva uso del escritorio/Xorg (~1,2 GiB); GPU1 quedó sin carga del benchmark.
- **Decisión:** no modificar perfiles productivos ni HarnessSpec. Sin Computer Usage GUI E2E, visión real, Ingi-Charla/ASR/TTS ni retrieval efectivo de contexto. Ver [RESULTS.md](RESULTS.md) para detalle y límites.
