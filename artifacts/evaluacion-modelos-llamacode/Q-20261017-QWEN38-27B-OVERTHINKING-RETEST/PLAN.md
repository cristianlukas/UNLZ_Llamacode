# Plan — Q-20261017-QWEN38-27B-OVERTHINKING-RETEST

## Objetivo

A pedido explícito del usuario, retomar las pruebas que no se habían hecho en la
revisión del post “Qwen3.8-27b appreciation moment”. La tarea anterior fue una
auditoría documental, no una evaluación local. Cerrar el hueco agentivo que el
benchmark AP-Q3 del 26-09 dejó abierto (HE0 → HE20 → BCB8 y TaskFlow ULTRA) y
medir la terminación con límites reproducibles. No cambiar perfiles productivos.

## Alcance y límite de la afirmación

El GGUF exacto del post (Unsloth UD-Q3_K_XL y UD-Q2_K_XL) no está instalado. El
único Qwen3.8-27B Q3 disponible es Agention AP-Q3_K_XL, calibración distinta; el
control local disponible es ByteShape IQ4_XS. Cualquier score nuevo se atribuirá
sólo a AP-Q3/ByteShape y no será réplica del post ni comparación contra UD.

La campaña es un screen por perfil, no una promoción. Para hablar de mejora
estable harían falta tres corridas válidas emparejadas por perfil. Se reutilizan
los resultados ya existentes de PPL, velocidad, Computer Use, imagen y coding
smoke; no se repiten esas pruebas. Voz, visión E2E, contexto largo y rendimiento
no se infieren de esta escalera de coding.

## Perfiles y condiciones registradas antes de inferencia

- Candidato: `sys-eval-qwen38-agention-ap-q3kxl`, archivo
  `Qwen3.8-27B-AP-Q3_K_XL.gguf`, SHA-256 esperado
  `b5b35d550712f01fcaa0a982f281b7bcf47f6309c541450ca0e064c945c1c8fc`.
- Control: `sys-eval-qwen38-byteshape-iq4xs`, ByteShape IQ4_XS local, archivo
  `Qwen3.8-27B-IQ4_XS-3.84bpw.gguf`, SHA-256 esperado
  `89434f23dc89c5f990894e3fe9fdad19d88c370f0d3638a176f29933f218b78b`.
- Ambos: llama.cpp `llama.cpp-spark-native-20261003`, build 1 / commit `836d571`
  (0.5.0-dev; SHA-256 in preregistro),
  template `qwen38-tools-fixed.jinja`, contexto 32.768, KV Q8, una ranura,
  MTP apagado, reasoning/thinking en la misma configuración efectiva, y
  sampling del perfil servidor: T=0,6, top-p=0,95, top-k=20, min-p=0,
  repeat=1, presence=0. En benchmarks agentivos el harness limita la temperatura
  efectiva a `min(--temp, 0.1)` y fija seed 4242; ambos brazos usan T=0,1. Ejecución serial en GPU1 (`--device CUDA1`); GPU0 queda sin carga de modelo.
- App LlamaCode aislada, API/control en loopback, datos y recibos bajo este
  directorio. No se leen ni modifican perfiles/configuración de producción.

## Suites, orden y gates

1. Un pase de HE0, HE20 y BCB8 oficiales de LlamaCode por perfil, candidato y
   luego control. BCB8 sólo se inicia con HE20 válido y la misma huella
   efectiva. Transporte, timeout, truncamiento o error de runtime se clasifican
   como infraestructura/incompleto, no como error de calidad.
2. Un pase de TaskFlow ULTRA por perfil, HarnessSpec `LC-H1`, mismo prompt,
   suite, permisos y máximo de tres reparaciones; registrar primer intento,
   cada reparación, 13 criterios (10 archivos + py_compile/unittest/self-test),
   uso de tools y tiempo. No iniciar si las etapas anteriores revelan una
   falla de infraestructura sin resolver.
3. Sonda de razonamiento/terminación con `reasoning_budget_v2.json` (6 casos),
   presupuestos por solicitud `reasoning_budget_tokens=[0,512,2048]`,
   `chat_template_kwargs.enable_thinking=(budget>0)`, un pase, `max_tokens=512`,
   seed 4242 y el mismo sampler/template por perfil. El runtime local confirma
   estos campos en `tools/server/server-common.cpp` (líneas 1414–1424). Registrar validez de transporte, marcador
   de aceptación, finish reason, tokens de salida/razonamiento y latencia. Sólo
   puntuar si el runtime confirma que aplica el presupuesto por solicitud; si no,
   conservar el recibo como limitación de capacidad.

Tiempo máximo: 30 minutos acumulados por perfil para cada screen (escalera HE0→HE20→BCB, TaskFlow y sonda de presupuestos se registran por separado). Al alcanzar
el límite, se detiene ese perfil y el resultado queda parcial. No se cambia el
sampling para forzar aceptación y no se promueve con una corrida.

## Criterio de decisión

Completar los gates pendientes aporta evidencia de screening para coding/agente.
Una mejora requiere tres pares válidos y mejora repetida en aceptación y
terminación sin regresión importante de tiempo/estabilidad. Si ambos pasan o
los resultados son mixtos, no cambia el perfil vigente. La hipótesis del post
sobre UD-Q3/Q2 seguirá sin prueba local mientras esos pesos no estén instalados.

## Desviación registrada antes de la sonda de presupuestos

HE20 AP expiró con el timeout de 900 s que pasó el primer colector; la pantalla tenía un máximo de 1800 s. El recibo queda inválido/incompleto (5/20 tareas alcanzadas, 0/0 como marcador inválido), no habilita BCB y no se repetirá porque ya no cabe otro intento completo en el presupuesto acumulado de esa pantalla. La sonda directa usa `reasoning_budget_tokens` (no `reasoning_budget`), verificado en el parser del runtime antes de generar.

## Cierre de la campaña — 2026-10-17

ByteShape HE0 y HE20 fueron válidos; HE20 terminó 20/20 en primer intento en
1.530,9 s. La ventana acumulada de 30 min dejó sólo unos tres minutos, por lo
que BCB8 quedó pendiente y no se inició como parcial. Agention HE20 conserva el
recibo inválido por timeout del colector (900 s, 5/20); no es un resultado del
modelo. Las sondas de presupuesto se completaron en ambos perfiles, 18/18
respuestas HTTP por perfil; el caso safety truncó con thinking habilitado a
512 tokens. TaskFlow ULTRA no se ejecutó porque el screen comparable conserva
HE20 AP incompleto. No se cambió ningún perfil productivo.

El recibo ByteShape HE20 informó 52/53 llamadas exitosas, cinco redundantes y
un evento de estancamiento; el recibo AP parcial informó dos estancamientos,
tres llamadas redundantes y un `stream_repetition`. No se interpreta el parcial
AP como score.
