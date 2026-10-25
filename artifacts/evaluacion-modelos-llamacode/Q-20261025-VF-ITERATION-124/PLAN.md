# Q124 · screen real de OCR español XFUND vs Tesseract · 2026-10-25

## Pregunta de decisión

¿Unlimited-OCR aporta una mejora material sobre Tesseract para leer formularios escaneados en español, suficiente para justificar un holdout mayor y una integración opcional en Data Lab? Esta prueba no decide adopción ni calidad legal/general.

## Fuente y licencia

- XFUND oficial, release v1.0: https://github.com/doc-analysis/XFUND/releases/tag/v1.0
- Repo/README oficial: https://github.com/doc-analysis/XFUND
- Assets fijados: `es.val.zip` (82,540,990 B) y `es.val.json` (1,262,584 B), con URL de release y SHA-256 anotados tras descarga.
- El README lista 90 formularios españoles en testing; el release nombra el asset `val`. Se documentará como `es.val` y no se presentará como test externo independiente.
- El README declara CC BY-NC-SA 4.0 para el contenido del proyecto. Uso exclusivamente académico/no comercial autorizado por el usuario; se conserva atribución local y no se redistribuye el conjunto.

## Prerregistro de muestra y comparación

- Antes de ver salidas, tomar 12 páginas distintas de `es.val`: ordenar por `SHA256("Q124-XFUND-es.val-v1|" + nombre_de_imagen)` ascendente y elegir las primeras 12. Guardar IDs, nombres, ordinales, hash del JSON y del ZIP en un manifest inmutable antes de cualquier inferencia.
- Baseline por cada página: Tesseract 5.3.4, `spa+eng`, `--psm 6`, imagen original, una ejecución por página.
- Candidate: Baidu Unlimited-OCR local, revision `8249d20b2822a7d8a4c22c8d8c9069b5ac36bda3`, BF16, `infer_multi`, prompt Q49 congelado, image_size 1024, max_length 32768, temperature 0, no_repeat_ngram_size 35 y ngram_window 1024. Inferencia offline, con las predicciones sin revisar hasta congelar los 12 IDs.
- Ejecutar en serie, primero seis páginas en la RTX 3090 física 0 y luego seis en la RTX 3090 física 1. La implementación del candidato usa `.cuda()` explícito y no implementa tensor parallel; por eso no se afirmará un benchmark dual-GPU concurrente. El host completo sigue siendo 2×RTX 3090 + 128 GiB y ambas GPU se prueban por separado.
- Usar el guard AMD05 aprobado Q117 (SHA `b4d42302e7d405abd5c59df5aa86bb7de6ef3bb91aef487b49acbebd1d24270e`) y el preflight Q121. El guard es de campaña y no un detector de cierres de Codex ni el guard productivo.
- Congelar parser, scorer y runner con SHA-256 en `receipts/preregistration.json` y verificar el preflight Q121 antes de ejecutar cada proceso. No ajustar umbrales, prompts ni parser luego de mirar resultados.

## Métricas y regla del screen

- Métrica principal: CER por página contra la secuencia anotada por XFUND, usando el parser estructurado Q49 sin cambios; informar media, mediana, pares por página y resultado agregado. Si el esquema del JSON contradice esta secuencia, no inferir una reordenación después de mirar outputs: pausar y preregistrar una enmienda.
- Métricas secundarias: recall exacto de palabras anotadas y tiempo por página (modelo y Tesseract separado). Guardar texto crudo y texto parseado como evidencia restringida al directorio local.
- Avanzar a un holdout real mayor/estudio de integración sólo si Unlimited-OCR reduce CER medio relativo ≥15% frente a Tesseract y gana en ≥8/12 páginas. Si no alcanza, no integrar. Si queda en zona intermedia, resultado inconcluso y decidir una extensión preregistrada de muestra; no cambiar producción.

## Límites y salvaguardas

- Dataset público de formularios; no documentos privados ni entrenamiento/fine-tuning.
- Sin endpoint o servidor de inferencia; llamadas directas al modelo en subprocess aislado y por turnos.
- Preflight de cero servidores, RAM disponible/PSI/OOM, cgroup efectivo, espacio, versión CUDA y ambas GPU; abortar antes de cargar el modelo ante cualquier fallo.
- Sin cambios a ASTRA DEFAULT, Flash-Next, SOL, PeritoSoft, perfiles productivos, RAM, swap o código de producto. Limpiar sólo procesos/archivos temporales de Q124.
- Subir a Google Sheets el prerregistro antes de descargar assets y resultados/readback al cerrar. Resultados locales y hashes canónicos.


## Avance registrado · baseline

Tesseract 5.3.4 CPU completó la muestra congelada de 12 páginas: media CER 0,2291; mediana 0,2196; recall exacto de palabras 0,8468; 1,041 s/página. Métricas por página y SHA-256 del resultado: `receipts/tesseract-baseline.json`. No se ejecutó modelo/GPU.


## Enmienda 03 · runner candidato bajo AMD05/Q121

Registrada 2026-10-25T03:37:45.946281Z antes de verificar o lanzar el candidato. El runner original Q121 valida hashes exactos de AMD05 y del proceso supervisado; por eso esta enmienda fija el runner directo de Q124, el worker, el launcher, el guard copiado byte por byte y el scorer. El verifier Q121 se ejecutará con `--runner` y `--guard` exactos antes del servicio.

- Cada proceso vive en `background.slice/llamacode-q124-unlimitedocr-screen.service`, con cgroup calculado para conservar 16 GiB de host y AMD05 monitorizando antes del primer worker. Un proceso independiente usa una GPU visible por vez: seis páginas en la GPU física 0, después seis en la física 1; timeout por grupo de 1800 s.
- Bubblewrap crea un network namespace aislado; Hugging Face queda offline y carga sólo pesos locales. Se llama al `infer_multi` ya fijado; no se inicia server ni endpoint. Los textos OCR quedan bajo `outputs/<attempt>/` local y no se suben al Sheet.
- El monitor corta solamente el grupo del worker Q124 y ante los gates AMD05; no mata GUI, ArtCraft, procesos ajenos ni servicios existentes. El preflight exige ambos adaptadores con ≥23.000 MiB libres, ≥80 GiB MemAvailable, ≥1 GiB SwapFree, telemetría válida, cgroup verificado y ≥5 GiB en los volúmenes.
- Hashes de runner/worker/launcher/guard/verifier/scorer y de los assets se fijaron en `receipts/amendment-03-guarded-runner-preregistration.json`. Primero se ejecuta compile + Q121 verify-only + servicio preflight-only; inferencia sólo si los tres pasan y Sheets contiene el readback de esta enmienda.
- Se conserva intacto el criterio original: sólo avanzar a un holdout mayor si reducción relativa de CER ≥15% y gana ≥8/12; no se cambia producción.


## Intento de verificación 01 y enmienda 04

2026-10-25T03:38:58.158614Z: Q121 bloqueó antes de lanzar nada porque el guard AMD05 cargado desde la carpeta Q124 requiere `q108_guard_core.py` y `q116_composite_psi.py`; el primer paquete sólo contenía el módulo principal. Intento registrado en `receipts/attempt01-q121-verifier-failure.json`. No se cargó el modelo, no se abrió servidor y no se usó CUDA/GPU.

Enmienda 04 prerregistrada antes del retry: copiar sin modificación las dos dependencias de `Q117/guard_sources`, verificar sus hashes, compilar y repetir sólo `Q121 --verify-only` con el runner Q124/guard AMD05 exactos. Los hashes y el criterio están en `receipts/amendment-04-q121-dependency-preregistration.json`.

Q121 verify-only intento 02 pasó después de A04: seis módulos compilaron, el verifier validó los hashes exactos del runner/AMD05 y confirmó que el monitor comienza antes del server. No cargó modelo, no inicializó CUDA y no usó GPU. Recibo `receipts/q121-verify-only-attempt02.json`.

## Enmienda 05 · variables y entorno del launcher

Prerregistrada 2026-10-25T03:41:30Z, antes de la validación y el servicio. La revisión estática detectó un desajuste: el launcher enviaba `Q124_EXPECTED_MEMORY_*`, pero el runner exige `LLAMACODE_EXPECTED_MEMORY_*`. Se corrigieron los tres nombres y se pasa explícitamente al hijo de Bubblewrap el entorno runtime (`PATH`, `LANG`, `LD_LIBRARY_PATH`, `LC_ALL`), `HOME` aislado y `PYTHONNOUSERSITE=1`. No se inició servicio ni se cargó el modelo/GPU al encontrar el defecto.

El chequeo de hash inicial encontró una transcripción incorrecta en el pin A05 (no en el archivo); siete módulos compilaron y el mapeo de variables pasó, pero el gate de fingerprint bloqueó antes del servicio. Recibo `receipts/attempt01-launcher-static-validation.json`. Enmienda06 corrige únicamente el hash del launcher a `406f7bef4de5ab00cdd76a53c908b4c5154e12f2668d3548bcd11dea69dd5eae`; los demás pins y el código permanecen iguales. El próximo intento repetirá hashes/sintaxis y después ejecutará `--mode preflight-only` en cgroup transitorio y namespace sin red, sin inferencia ni cómputo GPU. Ver `receipts/amendment-06-launcher-pin-correction-preregistration.json`.

Sólo después de pasar syntax + preflight completo se habilita la corrida ya preregistrada de 12 páginas, GPU física 0 y luego GPU física 1, seis por turno. El criterio CER ≥15% y ≥8/12, la configuración del modelo y todos los perfiles productivos siguen intactos.

## Estado de la guarda de memoria y preflight Q124

La revisión de Q113–Q117 confirma que RSS alta por sí sola no detiene la campaña. ASTRA DEFAULT 1M terminó con 51,14 GiB RSS y 55,64–55,728 GiB disponibles; Flash-Next 1M completó 3/3 con 64,98–65,06 GiB disponibles; SOL Q34 terminó en las dos RTX 3090 sin OOM, aunque no guardó PSI continua. Q97 vio PSI global moderada durante el screen ASTRA y avisó sin abortar. El guard Q124 AMD05 detiene ante telemetría ausente, MemAvailable <32 GiB o nuevo OOM global; también ante PSI global severa compuesta (full ≥60% OR some ≥80%) simultánea con MemAvailable <48 GiB durante 15 muestras. No usa RSS/porcentaje de RAM como umbral, ni vigila la GUI de Codex.

El preflight-only A04 pasó la inspección del host (110,24 GiB disponibles, GPU0/1 con 23.622/24.466 MiB libres, cero servidores), pero Bubblewrap 0.9 falló al configurar loopback (`RTM_NEWADDR: Operation not permitted`) bajo Ubuntu 24.04.5 con `apparmor_restrict_unprivileged_userns=1`. Falló antes de ejecutar Python Q124: AMD05 no llegó a iniciar y no hubo modelo/CUDA/GPU compute. El servicio transitorio ya no existe y ArtCraft quedó intacto. Evidencia `receipts/attempt01-preflight-only-network-setup.json`. Próxima enmienda: mover la creación de network namespace al systemd root manager (`PrivateNetwork=yes`) y retirar sólo `bwrap --unshare-net`; mantener Bubblewrap para el mount namespace/read-only FS y comprobar el namespace distinto antes de inferencia.

## Enmienda 07 · network namespace creado por systemd

Prerregistrada 2026-10-25T03:47:50Z antes de Q121/compile/preflight. A04 mostró que el lanzamiento fallaba al pedirle a Bubblewrap que asigne loopback, antes de invocar el runner. A07 mueve la creación del namespace privado al systemd root manager con `PrivateNetwork=yes` (sin interfaces externas) y deja Bubblewrap a cargo del filesystem read-only. El runner sigue comparando el inode de `/proc/self/ns/net` con el del host; el recibo ahora nombra correctamente la capa de aislamiento. No se cambia sysctl/AppArmor, configuración persistente de systemd, producto, modelo, thresholds ni contexto. Pins y gates en `receipts/amendment-07-systemd-network-namespace-preregistration.json`; inferencia permanece deshabilitada hasta Q121 + preflight-only PASS.

A07 validación CPU PASS: siete módulos compilan, pins launcher/runner exactos, check estático confirma `PrivateNetwork=yes` y ausencia de `--unshare-net`; Q121 verify-only confirma el runner/AMD05 actualizado y que el monitor antecede al worker. Recibos `receipts/attempt02-a07-static-validation.json` y `receipts/q121-verify-only-attempt03.json`. Siguiente: únicamente `--mode preflight-only` en servicio transient; el modelo sigue bloqueado.

## Intento A07 de preflight-only y enmienda 08

El intento preflight-only `a05-preflight` pasó el preflight del host (110,24 GiB disponibles, 4,37 GiB swap libre, PSI global 0, GPU0/1 con 23.598/24.466 MiB libres, cero servidores), y systemd aceptó `PrivateNetwork=yes`. Bubblewrap falló después al crear su mapa de usuario no privilegiado (`setting up uid map: Permission denied`), antes del verifier Q121, del runner y del monitor AMD05. No hubo modelo, inicialización CUDA ni cómputo GPU; la unidad transitoria fue recolectada. Esto es un fallo del sandbox de usuario, no un rechazo por presión de memoria. Ver `receipts/attempt02-preflight-only-bwrap-uid-map.json` y `receipts/launch-preflight-only-a05-preflight.json`.

Enmienda 08 prerregistrada antes de los siguientes gates: eliminar Bubblewrap del camino y dejar que el systemd root manager cree el namespace de red y el mount namespace. La unidad directa conserva `PrivateNetwork=yes`, `ProtectSystem=strict`, `ReadWritePaths` restringido al directorio único del intento, `PrivateTmp=yes`, `NoNewPrivileges=yes`, límites cgroup y KillMode de grupo. HOME/caches/TMPDIR quedan dentro del intento; inputs del modelo/datos sólo se leen; inferencia sigue bloqueada. No se altera AppArmor, sysctl ni configuración global. Pins y criterios exactos: `receipts/amendment-08-systemd-only-sandbox-preregistration.json`. Siguiente gate: sintaxis/hashes + Q121 verify-only y luego un nuevo preflight-only `a08-preflight`; no iniciar modelo/CUDA/GPU compute hasta que pase.


## Enmienda 09 · corrección del pin del scorer

Registrada 2026-10-25T03:55:41Z tras el fallo estático A08: el pin del scorer se transcribió mal, mientras el SHA del archivo local permaneció `76347fb3060dfa8d147f777a8dc0538f153b7b26ec3906e50c7b53c9d9e373b1`. No se modificó ningún archivo de código. Q121 verify-only se ejecutó de forma independiente por el shell no fail-fast y pasó; no equivale al gate estático completo. A09 corrige el registro y exige repetir hashes, compilación, check del sandbox y Q121 con comportamiento fail-fast antes de lanzar el preflight. Receipts: `receipts/amendment-09-scorer-pin-correction-preregistration.json`, `receipts/attempt03-a08-static-validation.json` y `receipts/q121-verify-only-attempt04.json`.


A09 static retry completed 2026-10-25T03:56:49Z: all eight preregistered SHA pins matched; eight Python modules compiled; the launcher has no Bubblewrap call and statically retains PrivateNetwork, ProtectSystem=strict, attempt-only ReadWritePaths, PrivateTmp and NoNewPrivileges; Q121 verify-only passed for the exact runner/AMD05 and confirms monitor-before-worker. Receipt `receipts/attempt04-a09-static-validation.json`. Next, after Sheet readback and a fresh lock check, run only preflight-only `a08-preflight`; inference remains disabled.

A09 static result was synchronized and read back in Sheets `Evaluaciones LlamaCode!A345:J345` and `Accionables!A17:N17`; WRAP and neighboring rows are preserved. Receipt `receipts/sheet-a09-static-result-readback.json`. The only next allowed service is preflight-only `a08-preflight`.


## Preflight-only A08 y enmienda 10 · import AMD05 Monitor

El intento A08 de preflight-only pasó el host scan (110,18 GiB disponibles, 23.619/24.466 MiB libres en las RTX 3090, cero inference servers) y systemd aceptó las propiedades sandbox. Q121 imprimió PASS para los hashes del runner/AMD05. El runner falló al importar `Monitor` desde `q117_pressure_guard_attempt05.py`; la clase vive en `run_context_holdout_attempt05.py`. Falló antes de la comprobación de inode de red, del inicio del monitor AMD05 y de cualquier worker/modelo. No hubo CUDA ni GPU compute. Evidencia `receipts/attempt03-preflight-only-monitor-import.json`, `outputs/a08-preflight/systemd-unit.log` y `receipts/launch-preflight-only-a08-preflight.json`.

A10 preregistra cambiar únicamente el import a `run_context_holdout_attempt05.Monitor` y fijar el nuevo SHA del runner/launcher, además de pinnear el runtime Q117 y su helper de aislamiento. Ejecutar hashes/compilación/Q121 fail-fast; actualizar/readback del Sheet; releer lock; después sólo un preflight-only nuevo `a10-preflight`. El modelo continúa bloqueado hasta PASS completo. Pins y criterios `receipts/amendment-10-monitor-import-preregistration.json`.

El primer intento del gate A10 se detuvo antes de hashes/compilación porque la ruta preregistrada al verificador Q121 apuntaba fuera del repositorio; no se lanzó Q121, servicio, guard ni inferencia. A11 registra únicamente la corrección de metadatos a `../../../tools/evaluation_guard_preflight.py`, conserva el SHA ya fijado y repite el gate fail-fast antes de un preflight-only `a11-preflight`. Evidencia `receipts/attempt05-a10-static-prereg-path-block.json`; preregistro `receipts/amendment-11-q121-verifier-path-preregistration.json`. Sin CUDA/GPU compute; el modelo sigue bloqueado.

A11 sí alcanzó los diez pins, las diez compilaciones y los checks estáticos. Q121 bloqueó porque también exige que el runner declare un `ImportFrom` del módulo AMD05; la clase `Monitor` correctamente proviene de Q117 `run_context`, y desde allí se importan dinámicamente las funciones del helper AMD05 al muestrear. A12 preregistra un import explícito de esos tres exports, conserva ambas funciones y fija los nuevos hashes. La falla ocurrió en AST validation antes del preimport AMD05 o el servicio; no hubo GPU. Evidencia `receipts/attempt06-a11-q121-import-contract-block.json`; preregistro `receipts/amendment-12-explicit-amd05-import-preregistration.json`. Repetir gates CPU y Q121; sólo después podría ejecutarse preflight-only `a12-preflight`.

A12 static/hash/compile PASS: diez pins coinciden, diez módulos compilan a `/tmp/q124-a12-pycache`, el launcher conserva propiedades de systemd y no invoca Bubblewrap, los imports del Monitor Q117 y de los exports AMD05 son explícitos, y Q121 verify-only acepta exactamente el runner/guard con `monitorStartsBeforeServer=true`. No se cargó modelo, no se inicializó CUDA ni hubo compute GPU. Recibos `receipts/attempt07-a12-static-validation.json` y `receipts/q121-verify-only-attempt07.json`. Siguiente, tras Sheet readback y lock fresco, únicamente preflight-only `a12-preflight`.

A12 preflight-only PASS en systemd directo: MemAvailable 109,93 GiB, swap libre 4,37 GiB, PSI global 0, OOM 0, sin inference servers, namespace privado distinto del host, cgroup efectivo verificado y dos muestras AMD05 PASS; el worker sólo usó ~22 MiB y 0 swap, y la unidad quedó inactiva. No cargó el modelo, no inicializó CUDA ni hizo GPU compute. Esto valida el camino aislado, no un stress test de RSS ni el crash de Codex. Recibo `receipts/postflight-a12-preflight.json` y outputs bajo `outputs/a12-preflight/`.

A13 preregistra el screen real de 12 páginas XFUND: seis secuenciales en GPU física 0 y luego seis en GPU 1, AMD05 activo y timeout de 1800 s por worker, sin concurrencia ni cambios de producción. Criterio sin cambios: reducción media CER ≥15% y al menos 8/12 victorias; resultado mixto requiere preregistrar extensión aparte. Preregistro `receipts/amendment-13-xfund-run-screen-preregistration.json`. No iniciar hasta sincronizar/readback en Sheets y confirmar lock.

A13 alcanzó el worker de GPU0 y consultó disponibilidad CUDA/BF16; falló en `AutoModel.from_pretrained` al crear el HF modules cache en `TASK/outputs/hf-home`, que está fuera del `ReadWritePaths` del intento. No cargó pesos, no ejecutó `.cuda()` ni OCR de página; GPU1 no se inició y no hay resultado de calidad. La guarda no abortó: 9 muestras, MemAvailable mínima 109,15 GiB, PSI/OOM 0, RSS de árbol máx. 845 MiB, cgroup máx. 1.103 MiB. Unidad inactiva y sin worker residual; ArtCraft intacto. Evidencia `receipts/attempt08-a13-hf-cache-readonly-failure.json`. A14 preregistra dirigir las cuatro cachés a `RUN_DIR/hf-home`, actualizar pins, repetir gate CPU/Q121 y luego correr un intento nuevo `a14-xfund-screen` tras Sheets/readback/lock. El fallo A13 no se atribuye a presión de memoria ni a calidad del modelo.

## A15–A17 · hash/readback y gates tras el ajuste de caché

A15 detuvo el gate antes de compilación/Q121 por un hash del worker mal transcrito en metadata; A16 corrigió el registro. El siguiente gate se detuvo por un literal mal construido en el harness estático, no por código del runner; A17 fija esa comprobación sin cambios de código. Evidencia: `receipts/attempt09-a15-worker-pin-metadata-block.json`, `receipts/attempt10-a16-static-assertion-harness-block.json` y enmiendas 15–17.

2026-10-25T04:12:15Z: A17 superó 10/10 SHA pins, 10/10 compilaciones a `/tmp/q124-a17-pycache`, las cuatro rutas de caché bajo `RUN_DIR/hf-home`, el sandbox systemd estático y Q121 verify-only (`monitorStartsBeforeServer=true`). Sin servicio, modelo, CUDA ni compute GPU. Recibo `receipts/attempt11-a17-static-validation.json`.

2026-10-25T04:12:53Z: el preflight-only `a17-preflight` pasó en servicio transitorio systemd: MemAvailable 109,91 GiB, swap libre 4,37 GiB, PSI/OOM 0, dos muestras AMD05 sin abortar y cgroup del intento ~25,7 MiB con 0 swap. Sin servidores de inferencia; no cargó modelo, no inicializó CUDA ni hizo inferencia. La unidad quedó inactiva, Q124 sin procesos residuales; se observó ArtCraft 207 MiB y quedó intacto. Recibo `receipts/postflight-a17-preflight.json`. Próximo gate elegible: readback de Sheet + lock fresco, luego el screen XFUND original 6 páginas por GPU0 y después 6 por GPU1, bajo AMD05/Q121.

2026-10-25T04:14:52Z: el screen `a14-xfund-screen` pasó host y servicio, pero se detuvo antes de `subprocess.Popen`: `run_dir` no existía en ese ámbito; el nombre correcto del intento es la constante `RUN_DIR`. No hubo worker, pesos, OCR, GPU1 ni stop del guard; MemAvailable fue 110,40 GiB, PSI/OOM 0 y el cgroup quedó en ~26,4 MiB. Evidencia `receipts/attempt12-a14-run-screen-run-dir-nameerror.json`. A18 cambió sólo los cuatro destinos de caché a `RUN_DIR/hf-home` y actualizó el pin.

2026-10-25T04:16:05Z: A18 static/hash/compile/Q121 pasó (10/10, 10/10, rutas bajo `RUN_DIR`, `monitorStartsBeforeServer=true`), sin inferencia. A18 preflight-only `a18-preflight` pasó a 04:16:45Z: MemAvailable 110,40 GiB, swap libre 4,37 GiB, PSI/OOM 0, dos muestras limpias, cgroup 20,94 MiB/0 swap, unidad inactiva, sin servidores ni procesos Q124. ArtCraft 207 MiB intacto. Recibo `receipts/postflight-a18-preflight.json`. Próximo gate: Sheet readback + lock fresco y luego `a18-xfund-screen` 6+6 secuencial.

## Enmienda 19 · reconciliación offline del resultado A18

Prerregistrada 2026-10-25T04:22:39Z, después de completar las 12 inferencias A18 y antes de cualquier nuevo cálculo comparativo. El launcher terminó con error posterior a las inferencias: `score_and_compare` busca `seconds` y `meanSeconds` en el reporte candidato, pero `score_model` sólo escribe CER/recall; los tiempos viven en los recibos de workers. El scorer guardó las 12 métricas de calidad. Esto es un desacople del reporte, no un fallo de OCR, del guard ni de memoria.

La actividad habilitada por A19 es una reconciliación offline, sin cargar modelo, CUDA, servidor ni GPU. Un comparador independiente de stdlib consumirá el baseline fijado, el reporte de calidad A18, el recibo `guarded-inference-a18-xfund-screen.json`, los dos recibos worker señalados por `physicalGpuRuns`, el manifest congelado y los 12 textos locales. Verificará estado completo/códigos 0, igualdad de manifest hash, conjuntos de IDs exactos (12/12), reparto serial 6+6, unicidad, tiempos finitos positivos y coincidencia de cada `outputSha256` entre recibo worker, reporte del scorer y archivo `.txt`. Sólo entonces unirá `seconds` por ID, conservará sin recalcular CER/recall/parser, calculará media de tiempo, pares y el criterio original (reducción CER ≥15% y ≥8/12 victorias). Una regresión sintética cubre el join de tiempos y el rechazo de IDs o hashes inconsistentes. No se corregirá el parser a la vista de salidas ni se repetirá inferencia.

Fuentes fijadas para A19: baseline `/media/cristian/Disco local/LlamaCode-eval/source49-unlimited-ocr/real-holdout/xfund-es-val-v1/tesseract-baseline-q124.json` (SHA `241919a906d0111347e1f29f66098f00c5d3a1217460be3f44e41b715ea2f161`); reporte candidato `outputs/a18-xfund-screen/model-q124.json` (SHA `3ef47f4f8ff13e49368cec6bdf4dd0077648c0c3e2da4fb2704b308f80257b1e`); manifest SHA `ea86894d6bfec138b7f8ff4eaab258f33ac81a834ad22db462c8a6a018c38c03`. Antes de ejecutar regresiones o comparación, fijar hashes de nuevo script/fixtures/recibos en `receipts/amendment-19-offline-reconciliation-preregistration.json` y leer el preregistro actualizado de vuelta en Sheets. No se cambia producción.

2026-10-25T04:25:32Z: el primer pase de la regresión A19 produjo 5/6 PASS; el comparador pasó los casos negativos y la única falla fue una aserción de igualdad exacta (`0.19999999999999996` vs. `0.2`) en el test sintético. No se ejecutó el comparador sobre los resultados reales. A20 preregistra cambiar sólo esa aserción a comparación de punto flotante con tolerancia; la función A19 y las métricas/decisión permanecen idénticas. Hacer pin del test actualizado y Sheet readback antes de repetir.

## Resultado final Q124 · 2026-10-25

A18 completó 12/12 páginas XFUND en dos tandas seriales de 6 (GPU física 0 y después GPU física 1); ambos workers terminaron con código 0 y AMD05 no abortó. El launcher falló sólo en la comparación posterior con `KeyError('seconds')`: el reporte del scorer contiene CER/recall, y el tiempo por página está en los recibos worker. A20 corrigió una igualdad decimal del test sintético; el regresor A19 pasó 6/6. A19 unió, sin tocar parser ni recalcular CER, las 12 filas puntuadas con los tiempos y hashes de los recibos, y comprobó IDs/manifest/textos.

Veredicto según la regla congelada: **no integrar Unlimited-OCR Q49**. Tesseract mean CER 0,229119; Unlimited-OCR 0,339435 (CER 48,15% mayor); sólo 4/12 páginas ganadas. Unlimited-OCR sí obtiene recall de palabras mayor (0,9353 vs 0,8468), pero el gate requiere reducción CER ≥15% y ≥8/12 victorias; ambos requisitos fallaron. No se justifica ampliar el holdout de esta revisión. Los tiempos 1,041 s/página Tesseract CPU y 11,408 s/página Unlimited-OCR GPU son descriptivos y no una comparación normalizada.

La traza AMD05 A18 contiene 141 muestras: MemAvailable mínima 108,184 GiB, máximo cgroup del intento 1,789 GiB, PSI avg10 global y cgroup en 0%, swap/OOM del cgroup en 0 y `monitorAbortReason=null`. Confirma que esta corrida no produjo presión ni falso abort; no es una prueba de presión severa. Junto con ASTRA DEFAULT 1M real (RSS 51,306 GiB, MemAvailable mínima 58,698 GiB, sin stop/OOM/swap), Flash-Next 1M 3/3 (64,98–65,06 GiB disponibles) y SOL Q34 dual 3090 completado sin OOM, la evidencia sigue favoreciendo no usar RSS alto por sí solo como stop. SOL no guardó PSI continua; los cierres de Codex quedan sin atribución. No cambiar umbrales, modelos, perfiles, RAM ni swap.

Evidencia final en `RESULTS.md`, `receipts/attempt15-a19-synthetic-regression.json`, `receipts/attempt16-a19-offline-comparison.json` y `outputs/a18-xfund-screen/comparison-q124-offline.json`. Resultados y actionable sincronizados/readback en Sheets; el texto OCR crudo permaneció local. Producción sin cambios.
