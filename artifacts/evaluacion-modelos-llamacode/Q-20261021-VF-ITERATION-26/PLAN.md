# Q-20261021-VF-ITERATION-26 — Gates HE0/HE20 con huella actual

## Pregunta

¿El candidato UD-IQ4_XS completa HumanEval/0 y HumanEval/20 con la configuración actual del perfil aislado `q14-udiq4xs-he0` y el agente `agent-maximo` (fingerprint `a56c723fde568b4db160bbb48ccc9e378aa221bdcaffe544ee957e3ba666dd86`), usando los pesos ya locales, sin alterar producción?

## Prerregistro

1. Antes de iniciar inferencia, comprobar que no haya procesos/listeners de inference server en `8354` ni control app en `18766`; comprobar RAM, PSI/OOM, GPU0, espacio y que los pesos/runtime existentes sigan presentes. La GUI de escritorio puede seguir abierta; no finalizar procesos ajenos ni GUI.
2. Copiar el XDG runtime validado en Q24 a una carpeta nueva de Q26. No modificar el original Q24 ni configuración productiva. Confirmar que los IDs/JSON de HE0 y HE20 y sus SHA-256 coinciden con este preregistro.
3. Iniciar LlamaCode Debug en modo headless con los directorios privados de Q26, antes de cargar el modelo. Seleccionar `agent-maximo` por la ruta sin ejecución de `startCustomBenchmark` y consultar `benchmarkCoverage`; sólo continuar con fingerprint `a56c…`, HE0 válido y HE20/BCB pendientes, o con las tres etapas pendientes si se trata de una corrida nueva. Si difiere, detenerse sin iniciar Strata ni inferencia.
4. Sólo tras validar el perfil aislado, iniciar Strata 0.1.41 de evaluación, ligado a loopback/puerto `8354`, con los pesos del HDD existentes, `--max-context 32768`, KV INT8, MTP spec4 y presupuesto residente de expertos 55 GiB. Usar sólo GPU0, en serie; no descargar ni volver a verificar SHA-256 leyendo los 93 GB completos.
5. Si HE0 está pendiente, invocar `startProBenchmarks` sólo con el ID congelado `059b6f00-7b4b-48ff-a3a2-2a71f900c1c0` (HE0), un pase, target `agent`, `agent-maximo` y timeout de 5.400 s. Si HE0 ya está válido a la huella actual, conservar ese recibo y no repetirlo. La API ejecuta una cola sin gate condicional, por eso HE20 se invocará en una segunda llamada únicamente después de verificar HE0.
6. HE0 debe quedar válido, 1/1 y con fingerprint actual antes de permitir HE20. Entonces invocar `startProBenchmarks` con sólo el ID `267bb33d-4510-417b-ae3c-6dbbfb2cb08d` (HE20), mismo perfil/agente/configuración, un pase y timeout de 5.400 s. HE20 debe quedar válido, 20/20 y con el mismo fingerprint. Ante timeout, fallo de infraestructura, fingerprint distinto o salida inválida, detener la escalera y no lanzar BCB.
7. Al terminar, detener sólo los procesos Strata/LlamaCode creados por Q26; comprobar que no queden listeners 8354/18766 ni servidores de inferencia propios. Conservar los logs, EVAL, workspaces y recibos.

## Criterio de decisión

- Los gates sólo autorizan considerar un BCB8 nuevo en otra iteración; no demuestran superioridad frente a ASTRA/SOL ni autorizan promoción o borrado.
- Los fallos/incompletos por timeout o infraestructura no son un score de calidad.
- Todo resultado se añade a la pestaña `Inventario de modelos` antes de actualizar métricas del UD-IQ4_XS. No editar esa ficha con un resultado hasta leer el EVAL/recibo exacto.

## Invariantes

- No tocar ASTRA/SOL, sus perfiles o pesos; no cambiar PeritoSoft ni su catálogo; no modificar defaults productivos.
- No descargar, mover ni eliminar pesos. No usar GPU1. No terminar procesos ajenos.
- Sólo una carga de inferencia a la vez; dejar la GUI del usuario intacta.
- Precedencia de evidencia: resultados Q26 con huella actual > resultados históricos Q19/Q10, que permanecen preservados.

## Enmienda 01 — 2026-10-21

Se intercambió el orden de inicio de la app aislada y Strata: ahora se verifica la cobertura/fingerprint con CPU antes de cargar el modelo. Así, un perfil inesperado corta el intento sin reservar GPU ni leer el HDD durante el arranque. El alcance y los criterios de decisión no cambian.

## Enmienda 02 — 2026-10-21

HE0 y HE20 se lanzarán mediante invocaciones separadas. Aunque `startProBenchmarks` serializa una lista, no comprueba la validez de una etapa antes de iniciar la siguiente; dos llamadas permiten detener la escalera al fallar HE0. El orden, timeout, huella esperada y exclusión de BCB no cambian.

## Enmienda 03 — 2026-10-21

El primer gate de controlador no encontró el perfil porque `ProfileManager` usa `LLAMACODE_PROFILES_DIR`, independiente de XDG. El runner ahora señala explícitamente el directorio privado Q26; los JSON copiados siguen coincidiendo byte por byte con Q24. La huella y los criterios no cambian.

## Enmienda 04 — 2026-10-21

El segundo intento cargó el modelo y completó la preparación de caché, pero el ejecutable `strata --serve` es el motor stdin/stdout, no el endpoint HTTP. Al heredar EOF, informó su línea de protocolo READY y terminó; no recibió solicitudes de benchmark. El siguiente intento usa el `serve/server.py` que acompaña al mismo runtime 0.1.41 para exponer `/v1/models` en loopback. El binario, pesos, argumentos de inferencia, GPU0, fingerprint, suites, orden y gates permanecen iguales.

## Enmienda 05 — 2026-10-21

El wrapper cancela por defecto la espera del motor a los 900 s, antes del timeout de arranque Q26 de 1.800 s. El intento 03 agotó exactamente ese plazo con la caché host en 40/48 capas; el endpoint no recibió requests. El siguiente intento define `STRATA_ENGINE_READY_S=1800`, igualando ambos plazos. No cambian configuración, recursos, suites, criterios ni el límite total.

## Enmienda 06 — 2026-10-21

HE0 terminó válido (1/1, 718.655 s) bajo `agent-maximo`, fingerprint `a56c723fde568b4db160bbb48ccc9e378aa221bdcaffe544ee957e3ba666dd86`. El gate CPU inicial había calculado `f185867766d87d1051fa4a3769e29e3d59040592e87429e33e66a710f441f344` antes de que `startCustomBenchmark` seleccionara `agent-maximo`; el runner falló al comparar ambas huellas. Antes de cargar el modelo otra vez, se hará una comprobación CPU-only que fija `agent-maximo` y exige que la cobertura conserve HE0 válido, HE20 pendiente y la huella `a56c…`. Si pasa, se reanudará directamente en HE20, sin repetir HE0. La suite, modelo, contexto 32768, pesos, GPU0 y criterio de validez permanecen iguales.

## Enmienda 07 — 2026-10-21

La primera comprobación CPU-only no encontró la fila `q14-udiq4xs-he0` en `benchmarkCoverage`, aunque el perfil existe en el directorio configurado. Se hará una sonda CPU-only que conserve las respuestas JSON crudas de `/methods` y `/prop`, antes y después de seleccionar `agent-maximo`, para separar un problema de lectura de la API de un problema de carga del perfil. No se iniciará el servidor del modelo.

## Enmienda 08 — 2026-10-21

La sonda anterior usó sin querer una ruta relativa en `LLAMACODE_PROFILES_DIR`; por eso cargó los perfiles integrados (274 filas) y no Q26. La siguiente sonda usa rutas absolutas, como el runner original, y vuelve a leer coverage tras seleccionar `agent-maximo`. Es sólo controlador CPU, sin servidor de modelo.

## Enmienda 09 — 2026-10-21

Con rutas absolutas, la sonda CPU confirmó que el perfil `q14-udiq4xs-he0` pasa de fingerprint `f185…` y HE0 pendiente al fingerprint `a56…` con HE0 válido cuando se selecciona `agent-maximo`; HE20 y BCB permanecen pendientes. El resultado HE0 de Q26 está guardado bajo esa misma huella. Se reanudará en HE20 sin volver a gastar una corrida en HE0. El runner fijará el agente antes del gate; usará una suite inválida intencional sólo para fijar el estado del selector, que retorna antes de iniciar benchmark o modelo, y comprobará servidor detenido/benchmark inactivo. Si la cobertura no muestra exactamente HE0 válido y HE20 pendiente con `a56…`, cortará antes de cargar Strata. El siguiente experimento será HE20, un pase, `agent-maximo`, timeout 5400 s, mismo runtime/pesos y GPU0.

## Enmienda 10 — 2026-10-21

El intento HE20-01 se detuvo por el timeout preregistrado de 5400 s a las 16:53:42 UTC. La última cobertura aún estaba incompleta: el status llegó a `reparando fallos 3/3` después de avanzar hasta el prompt 20/20. No existe score final ni se considera validado. Para terminar HE20 se preregistra un segundo intento con límite de 7200 s y artefactos/runtime aislados en `attempts/he20-02/`; se conserva el timeout y todos los recibos del intento 01. Antes de cargar Strata, la nueva app aislada debe confirmar la huella `a56c…`, HE0 `valid`, HE20 `pending`, benchmark inactivo y ausencia de servidores/listeners. Se ejecutará sólo HE20; si el gate difiere, el intento termina antes de usar GPU. Modelo, pesos, Strata 0.1.41, agent-maximo, contexto 32768, GPU0, KV INT8, MTP4, suite de 20 prompts y criterio de validez no cambian. BCB sigue excluido.

## Enmienda 11 — 2026-10-21

La evidencia del kernel confirma que HE20-02 no terminó por un timeout normal: hubo un global OOM a las 18:36:24 UTC. El kernel mató el proceso `LlamaCode` PID 607779 con 79.084.828 KiB de RSS anónimo (~75,4 GiB) cuando quedaban sólo 184 KiB de swap; no quedó EVAL final y el intento sigue sin score. El log de Strata había mostrado un request sin tokens tras 514 s y un reinicio, seguido de la asignación de caché page-locked; la coincidencia temporal no determina por sí sola qué asignación causó el OOM.

Se preregistra HE20-03 en una carpeta aislada nueva con la misma suite, agente `agent-maximo`, fingerprint `a56c…`, GPU0 y timeout total 7.200 s, pero limitando `resident_budget_gib` a 20 (antes 55) y `engine_silence_s` a 600 s (antes el default 300 s). El aumento del watchdog se apoya en el log de lectura lenta; la reducción de RAM y un guard local (abort si `MemAvailable <24 GiB`, `SwapFree <1 GiB` o el árbol de LlamaCode alcanza 60 GiB RSS) protegen el escritorio ante otra presión global. El resultado, si completa, se reportará como una variante con presupuesto de RAM limitado; su rendimiento no se comparará directamente con el intento a 55 GiB. No se cambia perfil, fingerprint, pesos, configuración productiva ni modelo; BCB sigue excluido.


## Enmienda 12 — 2026-10-21 · reanudación explícita

El usuario pidió reanudar el lote después de pausar HE20-03. Se conserva el lock Q26 existente (`1dc495a1-68f8-4f9d-a14e-396864cd1f70`); no se crea ni reemplaza otro lock. HE20-03 se preserva completo como intento parcial en prompt 6/20, sin EVAL/score y sin checkpoint verificable; HE20-04 reinicia únicamente la etapa HE20 desde cero.

Antes de cualquier carga se requiere un preflight fresco: cero procesos/listeners de inferencia en 8352/8354/18766, MemAvailable ≥80 GiB, SwapFree ≥1 GiB, artefactos/rutas presentes; luego gate CPU aislado con `agent-maximo`, fingerprint exacto `a56c723fde568b4db160bbb48ccc9e378aa221bdcaffe544ee957e3ba666dd86`, HE0 válido y HE20 pendiente. Si cualquier gate no coincide, parar sin arrancar Strata.

Se reutiliza sin modificación el runner ya validado `scripts/run_he20_03.py` (SHA-256 calculado al preregistrar), con `Q26_ATTEMPT_ROOT=attempts/he20-04`, timeout por suite 14.400 s (máximo permitido por el runner), `resident_budget_gib=20`, `engine_silence_s=600`, el guard cada 5 s (abort con MemAvailable <24 GiB, SwapFree <1 GiB o RSS del árbol LlamaCode ≥60 GiB), mismo modelo/pesos, Strata 0.1.41, contexto 32.768, KV INT8, MTP4, `agent-maximo` y GPU0. El límite ampliado se apoya en HE20-01 que llegó a prompt 20/20 antes de agotar 5.400 s y HE20-02 que alcanzó prompt 13/20 antes del OOM; la variante de recursos sigue idéntica a HE20-03. Este test sólo puede validar HE20 para el fingerprint actual y, si pasa, habilitar una decisión/prerregistro separado para BCB8; no demuestra superioridad ni autoriza promoción o borrado. Ante guard, OOM, timeout, fingerprint distinto o score inválido, registrar el resultado y parar; no reintentar automáticamente. ASTRA, SOL, PeritoSoft y producción quedan intactos.

## Enmienda 13 — 2026-10-21T20:24:37Z · HE20-04 falló antes de inferencia; bloqueo de recursos

HE20-04 alcanzó READY a las 20:18:48Z, pero el runner terminó en la preparación previa a la suite porque esperaba `attempts/he20-04/receipts/he0-gate.json`, archivo ausente. La preregistración apuntaba a la fuente `attempts/he20-03/receipts/he0-gate.json`, pero no se materializó la copia dentro del intento. No se envió ninguna solicitud HE20: cobertura 0/20, sin EVAL y sin score. Es un fallo de setup/runner, no un resultado de calidad del modelo. El controlador y Strata propios del intento quedaron detenidos y su limpieza está recibida.

En la comprobación de recursos a 2026-10-21T20:24:37Z hay tres servidores de inferencia activos en las RTX 3090 (Qwen3.5-9B en 8033 y 8081; Gemma 4 12B en 8083). La siguiente prueba queda bloqueada hasta que todos los procesos/listeners de inferencia desaparezcan. No enviarles requests ni terminarlos. Para un nuevo intento HE20-05: crear preregistro propio, copiar y verificar hash del recibo HE0 dentro de su carpeta `receipts/he0-gate.json`, repetir preflight de servidor/memoria y gates de perfil, ejecutar sólo HE20 si todos pasan. Sin retry automático ni BCB en paralelo.

Recibos: `attempts/he20-04/receipts/runner-failure-20261021T201848Z.json`; `receipts/inference-server-blocker-20261021T202437Z.json`.



## Enmienda 14 — Reanudación explícita y HE20-05 (2026-10-21T21:32:34Z)

El usuario reanudó explícitamente el lote después de la pausa. HE20-04 sigue clasificado como fallo de setup (0/20, sin solicitud ni score). Se preregistra HE20-05 desde cero; se copió `attempts/he20-03/receipts/he0-gate.json` a `attempts/he20-05/receipts/he0-gate.json` y se verificó SHA-256 `fb512bc0afb5fdb9aecb2e475ecf820a662676794fb0656c850c745f5f5512b4`. El gate conserva HE0 válido 1/1, HE20 pendiente y fingerprint `a56c…`; el runner conserva SHA-256 `694712c6fef09d1fc1c1bbaab0d46a2f92d4f586856d69fffdb8856ab4815cbe`.

El preflight fresco de 2026-10-21T21:32:34Z detectó inference servers ajenos activos: llama-server Qwen3.5 en 8033/8081 y Gemma 4 12B en 8083. HE20-05 queda preregistrado pero no iniciado (0 requests, sin GPU/modelo cargado). No enviar requests ni terminar esos procesos. El gate nuevo inspeccionará procesos de serving y todos los listeners TCP, no sólo los puertos legacy 8352/8354/18766; la GUI de escritorio está permitida y no se cuenta como servidor.

Siguiente acción: esperar hasta que una comprobación fresca encuentre cero inference servers; volver a comprobar memoria/swap y el gate CPU del perfil inmediatamente antes de cargar Strata; ejecutar sólo HE20-05 en GPU0, serial, con los guards ya registrados. Sin retry automático ni BCB. ASTRA/SOL, PeritoSoft y producción permanecen intactos. Recibo: `attempts/he20-05/receipts/resume-blocker.json`.


## Revalidación de servidores — 2026-10-21T23:20:47Z

Sigue bloqueada la inferencia: Qwen3.5-9B permanece activo en `llama-server` PID 2173417, 2173751 (puertos correlacionados: ver recibo). Gemma 4 ya no apareció. MemAvailable=91.05 GiB; SwapFree=4.6 GiB. No se lanzó benchmark ni se detuvo proceso. El runner detecta procesos conocidos en cualquier puerto mediante `/proc`; la revisión de puertos reservados es adicional. Recibo `attempts/he20-05/receipts/resume-blocker.json`.
