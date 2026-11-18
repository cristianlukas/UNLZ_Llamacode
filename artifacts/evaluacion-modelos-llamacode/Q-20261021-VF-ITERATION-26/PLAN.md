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


## Enmienda 15 — pausa explícita y auditoría de Sheets (2026-10-21T23:29:12Z)

El usuario pidió pausar todos los tests. HE20-05 permanece preregistrada, con 0 requests y sin score; no iniciar inferencia aunque el bloqueo externo cambie mientras siga vigente la pausa. El último scan documentado (23:20:47Z) encontró dos `llama-server` Qwen3.5 en 8033/8081. No se detuvieron procesos ajenos.

Se auditó el Sheet autorizado sin lanzar pruebas. Se agregó el registro que faltaba de Q-20261016-CU-20-E2E (20/20 en el SHA certificado), se normalizaron los estados históricos de Evaluaciones LlamaCode!C156:C164 y se dejaron explícitos los resultados, bloqueos y pausa de Q26. Accionables contiene 41 tarjetas con resultados/evidencias/reconciliación; 28 fechas de creación no constan y no se inventaron. La pestaña Inventario de modelos conserva una sola ficha visible pese a la nota histórica de 53; quedan 52 por reconciliar. Evidencia de auditoría: `receipts/google-sheet-audit-20261021-02.json`.

El lock de Q26 se libera tras guardar este estado. Reanudar sólo tras una instrucción explícita del usuario y luego de un preflight fresco con cero inference servers, memoria/swap en umbral y gate CPU exacto; ejecutar únicamente HE20-05 en serie.


## Enmienda 16 — reanudación y orden P1–P5 (2026-10-21T23:50:32Z)

El usuario reanudó explícitamente todos los tests y ordenó evaluar primero Qwen3.8 Flash-Next, luego Qwen3.8-27B, RCO Coder, Swift y después claims de Strata/velocidad/calidad. Q26 HE20-05 queda P1 y se ejecutará en GPU0 sólo tras preflight fresco y gate CPU/fingerprint; HE0 sigue válido 1/1 y HE20 tiene 0 requests al preregistrar. Runner SHA-256 `36ce629670321ff778db271cd29114bee9465761b41bb4c7dd61f0c9be0bce07`. Sin BCB en paralelo, retry automático, promoción, borrado o cambios productivos. Los candidatos P2–P5 siguen secuenciales; RCO exige artefacto/hash/espacio/sharding verificables y Swift queda condicionado a licencia comercial habilitante. Recibo: `attempts/he20-05/receipts/amendment-02-preregistration.json`.


## Enmienda 17 — prioridad visible en Sheets y pruebas P2/P3 (2026-10-21)

El usuario reiteró que el trabajo siga el orden Flash-Next, Qwen3.8-27B, RCO, Swift y Strata/otros claims. Se sincronizaron 64 Q-ID omitidos y se agregaron Q28 (P2, Qwen3.8-27B: canario de tools y suite matched sólo si pasa) y Q27 (P3, RCO: factibilidad CPU-only antes de cualquier descarga). En Accionables se ordenó Q26 P1, MTP Q4 P1.1 bloqueado, Q28 P2, OpenJet P2.1 bloqueado por incompatibilidad MTP, Q27 P3, Swift P4 con gate de licencia y Strata P5. La lectura posterior confirmó 43 tarjetas, 249 Q-ID operativos con 0 duplicados entre las 66 filas importadas, y navegación en IA local. La conciliación documental no inició inferencia; HE20-05 sigue 0 requests/score.

Base de recomendación: los tests incompletos previos no producen score de calidad; el diagnóstico de tool-call para Qwen3.8-27B fue inválido; los resultados externos de RCO/OpenJet/Swift no son comparables directamente al setup local; los gates de compatibilidad, espacio y licencia preceden a descarga/inferencia. Recibo de reconciliación: `receipts/priority-order-sheet-sync-20261021.json`.


## Enmienda 18 — P1 HE20-05 en ejecución (2026-10-22T00:04Z)

Preflight inmediatamente antes del modelo: cero procesos de inferencia ajenos y cero listeners bloqueantes; el listener 18766 corresponde al controlador permitido. MemAvailable 109,75 GiB y SwapFree 4,62 GiB; el perfil exacto tuvo HE0 válido y HE20 pendiente. Runner SHA-256 `36ce629670321ff778db271cd29114bee9465761b41bb4c7dd61f0c9be0bce07`. Strata inició el modelo local sin descarga; tras ~466 s quedó ready e invocó HE20 con custom ID `267bb33d-4510-417b-ae3c-6dbbfb2cb08d`, un pase, agente `agent-maximo`, sin BCB. Último poll 00:04:46Z: prompt 1/20 en curso, aún sin respuesta ni score; guard 00:04:23Z MemAvailable 85,21 GiB, SwapFree 4,62 GiB, app RSS 0,06 GiB y server RSS 59,64 GiB. Continuar serialmente hasta resultado válido o gate/corte; sin retry automático. Recibo `attempts/he20-05/receipts/p1-progress-20261022T0004Z.json`.

## HE20-06 — variante contenida de memoria · 2026-10-22T01:09:21Z

Tras el abort seguro de HE20-05 (swap global 0,56 GiB; sin score), se preregistra una nueva ejecución materialmente distinta del mismo HE20: mantiene el modelo, la huella de perfil, los 32K, KV INT8, MTP4, agente y fixture; reduce sólo `resident_budget_gib` de 20 a 12 y contiene la copia aislada de LlamaCode + Strata en un scope propio (`MemoryHigh=86G`, `MemoryMax=96G`, `MemorySwapMax=1G`, `OOMPolicy=kill`). El wrapper compara el token del lock y hashes actuales de AGENTS/README/WORK_QUEUE, y exige que el cgroup v2 refleje exactamente esos límites antes de ejecutar el runner. Guardias globales 24 GiB MemAvailable / 1 GiB SwapFree permanecen iguales. No se mide velocidad comparativa ni se cambia producción. Si la suite no logra 20/20 válido, no habrá score y no habrá retry automático.

Prerregistro y copia aislada: `attempts/he20-06/receipts/preregistration.json`, `attempts/he20-06/receipts/runtime-copy.json`.


## Enmienda 19 — cerrar HE20 y preregistrar BCB8 · 2026-10-22T02:22:31Z

HE20-06 completó la etapa válida a la huella `a56c723f…`: 20/20 finales, 14/20 en el primer intento, dos reparaciones, 3.507,073 s, sin timeout ni fallo de infraestructura. La mejora automática `elapsedVsBaselinePct` no se toma como evidencia de velocidad: su baseline tiene fingerprint distinto (`185d…`). Se conserva el resultado de HE20 como una sola corrida con reparaciones; todavía no hay motivo para cambiar el modelo productivo.

Se preregistra `attempts/bcb-01/receipts/preregistration.json` para ejecutar únicamente BCB-Hard 8 ítems, que continúa pendiente y es la siguiente etapa autorizada de P1. Se revalidarán el mismo fingerprint, HE0/HE20 válidos y BCB pendiente antes de cargar el modelo; timeout máximo 1.800 s, recursos aislados en el mismo cgroup protector, resident budget 12 GiB, GPU0. Un score BCB aislado no demostrará superioridad; se requerirá un control ASTRA/SOL emparejado para cualquier recomendación de adopción. No se repetirá automáticamente si el gate falla o vence el tiempo.


## Enmienda 20 — corregir fallo previo a inferencia de BCB8 · 2026-10-22T02:25:20Z

El primer arranque de `bcb-01` superó los gates de cgroup, servidor/memoria y perfil: HE0 y HE20 válidos, BCB pendiente, fingerprint `a56c723f…`. Se detuvo antes de iniciar Strata al calcular SHA-256 del fixture por un `NameError` (`hashlib` no importado); no hubo carga de modelo, invocación de suite ni requests BCB. El controlador aislado fue terminado por el propio runner y el cleanup indica Strata no iniciado. Los recibos originales se conservaron en `attempts/bcb-01/receipts/pre-inference-failure-01/`.

Se corrigió únicamente el import estándar, se actualizó el hash del runner en el prerregistro y wrapper, y `py_compile` pasó. Esto corrige el setup antes del único pase previsto; no es un retry de suite. Se repetirá el preflight completo desde cero. La regla permanece: ejecutar BCB8 una vez, timeout máximo 1.800 s; si la suite inicia y falla o vence, no repetir sin un cambio material.

## Enmienda 21 — resultado del único pase BCB8 y siguiente prueba P1.1 · 2026-10-22T02:58:48Z

El pase BCB8 invocó la suite congelada y alcanzó 8/8 prompts, pero venció el timeout de 1.800 s con la reparación 2/3 pendiente. El prompt 2 agotó su presupuesto de razonamiento y terminó por repetición sin respuesta final; no hay grade ni score. La última guarda seguía dentro de los umbrales y la unidad propia se limpió; el postflight no encontró procesos de inferencia ni GPU. No se repetirá esta invocation.

HE20-06 permanece válido 20/20 con dos reparaciones; sus 3.507,073 s no se comparan con el baseline de otra huella. No basta para afirmar superioridad. La próxima prueba en orden es P1.1, MTP Q4/llama.cpp. Como TaskFlow MTP-on terminó 0/13 y MTP-off no cerró, se preregistró una pantalla pareada con una tarea reducida y primer paso de escritura explícito, idéntica entre ambos brazos. Cambia deliberadamente la tarea, así que sus puntuaciones no se compararán con TaskFlow ULTRA histórico; sólo se compararán MTP-off/on dentro de esta pantalla.

Prerregistro `attempts/mtp-taskflow-v2-01/receipts/preregistration.json`; suite congelada `attempts/mtp-taskflow-v2-01/spec/taskflow-mini-v2.json`. Un pase por brazo, MTP-off primero y MTP-on después, 1.800 s por suite, misma cuantización/runtime/agent/sampling/contexto; sólo cambia el sidecar MTP. Si pasa, repetir semillas emparejadas antes de afirmar ventaja de calidad o velocidad.



## Enmienda 22 — corrección de endpoint y gates antes de MTP-off · 2026-10-22T03:11:10Z

La revisión final del wrapper detectó una diferencia antes de arrancar el modelo: el daemon aislado se configura con `LLAMACODE_CONTROL_PORT=18119` y los recibos históricos usan `http://127.0.0.1:18119`, mientras que el script nuevo apuntaba a 8877. Se corrigió el endpoint a 18119 antes de iniciar una solicitud. El preflight ahora comprueba el `profileConfigFingerprint` exacto esperado para el brazo MTP-off/on y fija SHA-256 de LlamaCode y llama-server; además contrasta el hash de `/proc/<pid>/exe` tras abrir el daemon y antes de la carga. `py_compile`, hashes de binarios y chequeos estáticos de suite/perfiles/modelos pasan. No hubo inferencia ni uso de GPU. La corrección está incorporada en el prerregistro antes de la primera corrida.


## Enmienda 23 — dependencia del runner corregida antes de MTP-off · 2026-10-22T03:13:27Z

El primer intento MTP-off alcanzó el gate de perfil exacto y verificó el scope, pero el runner salió porque faltaba `scripts/run_taskflow.py` en el nuevo intento. No llegó a cargar el modelo: sin llama-server hijo, sin `benchmark_start`, cero procesos GPU y postflight limpio. Se preservaron recibos/logs bajo `attempts/mtp-taskflow-v2-01/receipts/preflight-failure-01/`. Se copió el runner histórico sin cambios, se fijó SHA-256 `1cf43f5cafbfd83ff6357bd3dbd1d6986b68ee1499f7008f8ea2bf8f67df484c`, y se agregó su validación estática; `py_compile` pasó. El pase de control preregistrado sigue disponible.


## Enmienda 24 — guardia de RSS desalineada corregida · 2026-10-22T03:18:32Z

El primer intento que sí inició MTP-off fue abortado al alcanzar RSS de árbol 60 GiB, límite que el wrapper había añadido sin prerregistro. En la activación host MemAvailable 115.73 GiB, swap libre 2.71 GiB, cgroup 76.11/96 GiB y eventos max/OOM en cero. No quedó score. El postflight inmediato vio el llama-server propio después de detener la API, pero el scope systemd terminó de limpiarlo al salir; el chequeo posterior confirmó cero servidores, listeners reservados y compute apps. La guarda se corrigió para seguir exactamente el preregistro (<20 GiB MemAvailable por 15 muestras, swap <1 GiB), con límites 86/96 GiB y aborto ante evento max/OOM del cgroup. No se repetirá como pase de calidad; es una continuación para obtener una corrida válida tras corregir una instrumentación no autorizada.


## Enmienda 25 — guardar última guarda y huellas de scripts · 2026-10-22T03:20:02Z



## Enmienda 26 — control MTP-off pasa Mini v2 · 2026-10-22T03:28:26Z

El brazo MTP-off completó el fixture y aprobó 7/7: cuatro archivos, compilación, ocho tests unitarios y self-test; cero reparaciones. Wall time 400,437 s; primera herramienta 157,224 s; primera escritura 157,456 s; cuatro llamadas. No hay TPS en la salida. Cleanup completo, sin servidores/puertos/GPU residuales ni eventos de cgroup/OOM. Este resultado confirma que el control puede realizar el fixture, pero una sola pantalla no establece ventaja de calidad/velocidad y no se compara con ULTRA. Actualizados accionable, Evaluaciones e Inventario en Sheets; el siguiente es MTP-on.


## Enmienda 27 — resultado MTP-on y tres pares de repetición · 2026-10-22T03:47Z

MTP-on también finalizó Mini v2 en 7/7, pero sólo después de dos reparaciones: 6/7 inicial, 14 tool calls y 850,805 s; primera herramienta/escritura 163,273/163,316 s. El control fue 7/7 a la primera con cuatro llamadas y 400,437 s. Ambos fingerprints y fixture coincidieron con el prerregistro; el MTP-on quedó 2,125× más lento E2E en esta única pareja. El campo `avgTps` 27,557 contra 20,957 es agregado y no desglosa prefill/decode, por lo que no revierte la lectura operativa. Recomendación provisional: mantener MTP-off y no migrar producción.

Como ambos brazos llegaron a 7/7 final y el prerregistro de pantalla pide decidir si hacen falta repeticiones, se abre un follow-up de tres pares para estimar variabilidad: seeds de llama.cpp 4243, 4244 y 4245; cada seed igual dentro del par; orden OFF→ON, ON→OFF, OFF→ON; mismo prompt/suite/harness/perfiles y límite 1.800 s; reinicio aislado entre brazos. Antes de cada brazo: lock/docs intactos, cero otros servidores de inferencia/listeners/compute apps, fingerprints exactos y guardias 40 GiB de memoria disponible/1 GiB swap al inicio, aborto si MemAvailable <20 GiB por 15 muestras, SwapFree <1 GiB o evento OOM/max del cgroup; GUI permitida. No hay cambios a perfiles productivos, ASTRA/SOL ni PeritoSoft. Detener el follow-up ante cualquier desvío de configuración, timeout/infraestructura o contaminación externa, sin seguir con el siguiente seed hasta registrar y limpiar.

Métricas: aceptación inicial/final, reparaciones, tool calls, wall E2E, primera herramienta/escritura, `avgTps` sólo como campo auxiliar, telemetría/cgroup y postflight. Gate de recomendación: mantener MTP-off salvo que el candidato repita 7/7 final sin regresión de aceptación inicial y mejore el tiempo E2E de modo consistente; tres pares no bastan para una afirmación estadística amplia. No comparar este fixture con TaskFlow ULTRA ni con Server Speed.


## Enmienda 28 — réplica MTP seed 4243 · 2026-10-22

El primer par repetido Mini v2 está completo y el segundo queda listo en orden ON→OFF. El seed 4243 favorece ON en aceptación (7/7 sin repair frente a 6/7 tras 3 repairs) y wall time (364,398 s frente a 1.161,152 s), pero contradice el primer screen y no aporta TPS desglosados. No activar MTP por un solo seed. Próximo: seed 4244 ON y luego OFF, usando fingerprints preregistrados, fresh server/memory gates y cleanup serial entre brazos. Gate de adopción sigue exigiendo consistencia entre pares sin regresión de calidad.
