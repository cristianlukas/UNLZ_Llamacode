# Q31 — Flash-Next · habilitar reparación Python aislada en BCB/765

**Prioridad:** P1, primero en el orden solicitado.
**Estado:** completada; grader válido pero fallido; cerrada la ruta de repetición del mismo caso.
**Pregunta:** al hacer que `python` resuelva a `python3` sólo en el entorno aislado de LlamaCode, ¿el mismo caso BCB/765 puede ejecutar el self-check, reparar su solución y devolver el grade original dentro del mismo límite de 1.800 s?

## Por qué esta prueba puede cambiar la decisión

Q30 no obtuvo grade: la solución inicial falló los tres asserts de archivos copiados y el agente intentó ejecutar la reparación con `python -m py_compile`; `/bin/sh` respondió `python: not found`. En el host sí existe `/usr/bin/python3`. `AgentToolRunner::startShell` usa `QProcess` con `sh -c` y no reemplaza el entorno del proceso; la copia aislada de LlamaCode permite inyectar un alias de compatibilidad sin cambiar el producto ni el entorno global. Así la reparación puede ejecutar el self-check que Q30 no llegó a ejecutar. La vuelta pretende determinar si la incidencia fue sólo de acceso al intérprete; no compara modelos ni autoriza adopción.

## Diseño preregistrado

- Candidato fijo: Qwen3.8 Flash-Next Unsloth UD-IQ4_XS, Strata 0.1.41, fingerprint `a56c723fde568b4db160bbb48ccc9e378aa221bdcaffe544ee957e3ba666dd86`.
- Fixture original: `BigCodeBench/765`, acceptance/grader original y código inicial del prompt idénticos a Q30; máximo de 2.400 tokens también idéntico.
- Único cambio deliberado frente a Q30: anteponer al `PATH` de la copia aislada una carpeta que contiene `python` como wrapper de `/usr/bin/python3`. No se altera `PATH` del usuario, el controlador productivo, perfiles, pesos, ASTRA, SOL ni PeritoSoft.
- Una sola tarea, una pasada, sin reintentos automáticos, mismo límite total de 1.800 s. La carpeta shim se usa tanto por la app como por `sh -c`; un smoke CPU verifica que `python -c ...` llega a `/usr/bin/python3` antes de iniciar modelo. El preflight también exige que el backend seleccionado por el perfil apunte al mismo endpoint de Strata.
- GPU0 únicamente; scope propio systemd (MemoryHigh=86 GiB, MemoryMax=96 GiB, MemorySwapMax=1 GiB, OOMPolicy=kill); modelos, app y Strata ya locales; sin descargas ni builds.
- Preflight final: lock exclusivo token actual; hashes de AGENTS/README/WORK_QUEUE; binarios/pesos y SHA del runner/suite/shim; cero procesos/listeners de inferencia ajenos; cero NVIDIA compute apps ajenas; MemAvailable≥80 GiB y SwapFree≥1 GiB antes de modelo; guardia en curso: MemAvailable≥24 GiB, SwapFree≥1 GiB, árbol LlamaCode <60 GiB; puertos de prueba 18767/8355 disponibles.

## Criterio y límites

Pasa el diagnóstico sólo si el grader original devuelve resultado válido para BCB/765 con respuesta final antes de 1.800 s. Si termina en fallo de calidad, error de infraestructura o timeout, cerrar la ruta del mismo caso; no repetirla. Si pasa, preregistrar como prueba separada el BCB8 completo y un control ASTRA/SOL compatible antes de considerar cualquier claim. Incluso un pase no demuestra calidad/velocidad general ni cambia un perfil productivo.

## Integridad

Fixture y runtime se copian desde los recibos locales Q26/Q30. El recibo `preparation.json` demuestra que acceptance, prompt y `maxTokens=2400` son iguales a Q30; el prerregistro fija los SHA-256 antes del inicio. Mantener los resultados de Q30 y Q31 separados.


### Incidencias de preparación antes del único pase válido

El primer runner se detuvo antes de iniciar la app por una referencia de JSON incorrecta en el prerregistro. El segundo cargó Strata, pero el perfil del clon apuntaba a `127.0.0.1:8354` y el runner había elegido `8355`; se canceló desde el propio controlador a los 107 s de espera, sin respuesta ni grade. La limpieza confirmó cero procesos/listeners ajenos y OOM=0. Ninguno cuenta como resultado del modelo. El pase válido usa el endpoint heredado `8354`, compara backend→servidor antes de carga y permite una sola inferencia puntuable.
