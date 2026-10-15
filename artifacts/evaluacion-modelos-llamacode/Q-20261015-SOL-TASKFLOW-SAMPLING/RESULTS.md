# Resultados — Q-20261015-SOL-TASKFLOW-SAMPLING

**Estado: screening de SOL bloqueado por un fallo CUDA de vLLM; no hay score
válido de calidad.**

## Ejecución

Se cargó el perfil Ubuntu 177_SOL · Qwen3.8 27B · vLLM TP2 P2P MTP4 · 262K:
Qwen3.8-27B Frozenlock AutoRound INT4, vLLM 0.27.1, dos RTX 3090, W4A8,
MTP4 y contexto máximo 262144. El endpoint devolvió /v1/models con el modelo
qwen3.8-27b. Los pesos y la imagen ya estaban en disco; no hubo descargas.
La referencia de modelProfile guardada en el launch aún se llama Q4_K_M +
MTP3, pero la selección Linux del backend y el log de vLLM confirman que la
carga efectiva de SOL fue AutoRound INT4; el detalle queda separado en
receipts/sol-profile.json.

Se inició TaskFlow ULTRA con temperatura efectiva 0,1 y seed 4242. LlamaCode
guardó 0/13, dos reparaciones y 10,757 s, con mensaje de conexión cerrada y
cero tool calls. Ese registro **no es un resultado de calidad**: durante la
interacción CUDA levantó scatter gather kernel index out of bounds en vLLM y
un worker TP murió. El proceso API perdió el grupo NCCL y el endpoint empezó a
resetear las conexiones. La aplicación clasificó el 0/13 como quality; los
logs del servidor demuestran que fue infraestructura y el score se invalida.

La siguiente seed, 4243, no llegó a inferir: el benchmark quedó esperando la
carga/conexión del modelo mientras el API no respondía. Se detuvo a los 50 s
tras confirmar la caída del worker. No se corrieron las otras siete corridas
TaskFlow ni los tres coding smoke. Las temperaturas 0,6 y 1,0 quedan sin
probar.

El mismo assert CUDA ya aparece en la comparación local de SOL de
Q-20261009-STRATA-QWEN38-27B-AB con vLLM, tanto con MTP4 como sin MTP. El
perfil SOL actual no permite comparar la calidad con IQ2_XS hasta corregir o
reemplazar el runtime. La prueba sólo confirma que este stack no logra sostener
la inferencia del TaskFlow.

## Comparabilidad y recursos

La suite y los prompts son los mismos que en el screen IQ2_XS. SOL conserva su
techo de contexto de 262K; IQ2_XS se probó a 1M. Como SOL falló en el runtime,
no hay score comparable ni conclusión de que SOL sea mejor o peor que IQ2_XS.

El preflight encontró 114,58 GB de RAM disponibles, PSI en cero, GPUs y
endpoint libres. Durante el inicio, el monitor registró un mínimo de 103,32 GB
disponibles, PSI en cero y ningún OOM. En la instantánea previa a apagar el
contenedor había 108,97 GB disponibles; tras quitarlo quedaron 114,55 GB,
PSI cero, OOM cero y puertos 8113/8898 libres. La salida de emergencia no se
activó. La última muestra continua del monitor fue 14:28:33Z, antes de la
primera petición TaskFlow; durante la petición no hubo muestreo continuo. La
instantánea de 14:31:40Z y el postflight registraron PSI y OOM en cero.

No se modificaron perfiles productivos ni código de producto. Se usaron una
copia aislada del perfil, un contenedor con nombre/proyecto únicos y el binario
de evaluación ya preparado para permitir seed/temperatura. Validaciones
realizadas: readiness de SOL, launchMenu.ready, sintaxis Python/Bash y
git diff --check; no aplican builds ni tests del producto.

## Evidencia

- receipts/assessment.json: clasificación del intento y de las corridas no
  ejecutadas.
- receipts/taskflow-T0.1-seed4242.json y
  receipts/taskflow-T0.1-seed4242.launcher.json: respuesta cruda de la app,
  temperatura y seed efectivos.
- receipts/taskflow-T0.1-seed4243.launcher.json: intento sin score.
- receipts/sol-vllm-runtime-crash.log: assert CUDA, muerte del worker y
  errores NCCL.
- receipts/sol-profile.json, receipts/runtime-fingerprints.sha256 y
  receipts/sol-model-sha256.tsv: perfil, runtime y verificación local de los
  shards.
- receipts/preflight-20261015.json,
  receipts/pre-stop-runtime.json y receipts/postflight-20261015.json:
  recursos y cierre limpio.
