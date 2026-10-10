# Plan de evaluación — Q-20261009-FLASHNEXT-IQ3XXS-AB

Fecha de actualización: 2026-10-10 UTC  
Fuente objetivo: r/Qwen_AI, “Strata is the best Magic! Qwen3.8 FN IQ3_XXS on a 8GB Laptop”, usuario Ingroove.  
Lock de la cola: `e0dc3c20-28f5-4522-8897-b124577450d6`.

## Hipótesis y usos

El post ofrece una pista de viabilidad para ejecutar Qwen3.8-Flash-Next IQ3_XXS
con 8 GB de VRAM, CPU para visión y contexto configurado en 131.072; sus cifras
son autorreportadas, de otra máquina y no demuestran calidad para nuestros usos.
Se compara el perfil completo ISTA IQ3_XXS/Strata con el control ASTRA IQ3_S/
Strata en coding y rendimiento. No se cambia ningún perfil productivo.

## Evidencia ya disponible; no repetir

- LC-H1: HE0 → HE20 → BCB8, una corrida por perfil; ASTRA e IQ3_XXS usaron
  Strata v0.1.41, agente `agent-maximo`, thinking, seed 4242 y el mismo
  HarnessSpec `sha256:cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`.
- TaskFlow ULTRA: una corrida por perfil, misma suite/HarnessSpec/seed,
  presupuesto 8192, hasta tres reparaciones.
- Server Speed v1: dos pasadas por perfil, 32/32 muestras válidas por pasada;
  corpus `4bad8a5d24ce11096eb9634f7d03f24b83734c3f454031efb28d5fa259c996e9`.
- Sampling: probe exploratorio de cuatro celdas por perfil sobre HumanEval/0.

Los resultados crudos permanecen en
[`artifacts/qwen38-flashnext-iq3xxs-strata-20261009`](../../qwen38-flashnext-iq3xxs-strata-20261009/).

## ADV v1 — comparación complementaria

- Candidato: perfil aislado `iq3xxs-lch1-20261009`, modelo ISTA-DASLab
  Qwen3.8-Flash-Next GSQ-RCO IQ3_XXS, Strata v0.1.41 commit
  `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`.
- Control: perfil aislado `iq3s-lch1-20261009`, ASTRA calibrado IQ3_S con el
  mismo engine, host y parámetros de servicio.
- Suite `intelligence_adversarial_v1`, 10 tareas; SHA-256
  `2f0f30c863606fd443a161ac6946658129b31d874229a61ffd719f75df36ee87`.
- Harness engine `legacy` v1, HarnessSpec SHA-256
  `cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`.
- `agent-maximo`, thinking activado, misma semilla 4242, temperatura efectiva
  0,1, razonamiento medio, presupuesto 4096, timeout 1800 s, máximo 3
  reparaciones, una corrida inicial por perfil. Flags del perfil temporal:
  temp 0,60 / top-p 0,95 / top-k 20 / min-p 0 / repeat-penalty 1 /
  presence-penalty 0 / parallel 1. Sin concurrencia; ejecutar perfiles en serie.
- Criterio de validez: las diez tareas concluyen con transporte normal y sin
  timeout/caída. Score parcial válido cuenta como calidad; fallo funcional no
  se transforma en fallo de infraestructura.
- Criterio de decisión: screening descriptivo. No se declarará mejora estable ni
  se promoverá un perfil con una corrida por perfil; se requieren al menos tres
  pares válidos con semillas/tareas emparejadas y ausencia de regresión relevante.

**Incidencia de preregistro:** al reanudar el trabajo, el endpoint ya tenía en
curso el control ASTRA en ADV v1 (5/10 tareas visibles; proceso iniciado cerca
de 00:04:44 UTC del 10-oct-2026), antes de encontrar este archivo. No se
cancelará una prueba activa. Se registra este control como corrida heredada del
estado de la campaña, con desviación de preregistro; antes de iniciar IQ3_XXS
se conserva este plan. La pareja resultante será screening provisional y no
habilitará promoción.

## Solicitud añadida: post r/LocalLLM de Q4/4×P100/262K

El material adicional afirma Flash-Next Q4, KV q8, contexto 262K, 4×P100
PCIe 3 x8 y aproximadamente 2× frente a Qwen 27B/5× frente a un llama.cpp
modificado. No es el post original de IQ3_XXS en una laptop de 8 GB ni una
configuración que coincida con el A/B ya ejecutado. La evaluación y el estado
son independientes en el informe; no se reinterpretan los resultados IQ3_XXS
como réplica del caso P100.

El retrieval sintético 115K se intentó con IQ3_XXS y el transporte se cortó al
procesar 65.536/115.015 tokens, sin respuesta ni `usage` válido; no da score.
El smoke de 262K con config aislada se bloqueó antes de cargar el engine por la
guarda de swap (>2 GiB); no se generó ni envió prompt de 262K. Ambos estados se
registran como límite de infraestructura/transporte, no como fallo de calidad.

## Dimensiones fuera del scope ejecutable de este corte

- Computer Usage: no se ejecuta una interfaz real ni se infiere desde tool calls
  textuales; se conserva la auditoría previa de 216 prompts, que no fue E2E GUI.
- Ingi-Charla: no se evalúa audio; Flash-Next no incluye el pipeline STT/TTS
  integrado. Se conserva la recomendación anterior de Qwen3.5-9B.
- Visión: el post indica visión por CPU (`gpu: false`), pero no aporta corpus,
  errores ni métricas. Esta campaña tiene backend de texto y no medirá imágenes.
- Contexto: el perfil de esta campaña fue fijado en 131.072, pero el mayor
  prompt medido por Server Speed fue 38.804 tokens. La configuración no prueba
  uso efectivo ni calidad de recuperación cerca de 131K; se clasifica como no
  evaluado para contexto largo hasta contar con una prueba de retrieval fijada.

## Prueba diagnóstica de contexto prevista

Tras completar ADV v1 y con el endpoint libre, se hará una prueba por perfil
ASTRA IQ3_S e ISTA IQ3_XXS, una petición cada vez y con el mismo prompt
determinista, con objetivo aproximado de 115K tokens efectivos bajo
`max-context=131072`. El prompt incluirá registros variados y diez respuestas
exactas con valores señuelo, sembradas en posiciones aproximadas 5%, 15%, 25%,
35%, 45%, 55%, 65%, 75%, 85% y 95%; las diez preguntas se entregarán al final.
El perfil de serving será el de cada Strata config base (`iq3_s-main.json` y
`iq3_xxs-main.json`), imagen desactivada y máximo de contexto 131072. Una sola
petición por perfil, secuencial, sin tools; `temperature=0`, `top_p=1`,
`seed=4242`, `max_tokens=512`, `reasoning_effort=none`. La suite auxiliar se
llama `context-retrieval-v1`, sin HarnessSpec de agente: son diez búsquedas
exactas de campos distintos con datos señuelo. El fixture quedó generado con el
tokenizer del pack Qwen de Strata: 115.003 tokens de texto, 308.055 bytes,
prompt SHA-256 `ea4cd4a48080b0191273c4dfe4df54d69535a131d1e0117a31a3c75377d8ec84`,
expected JSON SHA-256 `89cd8df5fcf636c53436db4f4fdc9e8e2166a98e1c9c5d284428da4d23362d25`.
Los hechos están en offsets 5.758 (5,01%), 17.238 (14,99%), 28.729 (24,98%),
40.204 (34,96%), 51.667 (44,93%), 63.127 (54,89%), 74.602 (64,87%), 86.101
(74,87%), 97.567 (84,84%) y 109.050 (94,82%). Generador, prompt, expected y
metadatos están guardados en `context/`.

Se guardarán generador, prompt/hash, longitud real reportada por el servidor,
respuesta completa, uso de tokens, duración y RAM/VRAM/swap antes/después.
El servidor Strata puede estar descargado tras el benchmark anterior; el
endpoint autoinicia el engine en el siguiente request. Si comienza descargado,
el tiempo total incluirá esa carga en frío y se separará del prefill informado
en el log del engine.

Umbral de validez: respuesta normal sin truncamiento, timeout, OOM ni error de
transporte y `usage.prompt_tokens < 131072`. Se informará acierto exacto por
pregunta, prefill/latencia y estabilidad. Es una sonda sintética de capacidad y
recuperación, no una prueba integral de razonamiento largo ni una mejora
estable. No cambia producción; no se ampliará a 262K dentro de este test.

## Resultado de ejecución y cierre

- ADV v1 cerró para IQ3_XXS en 7/10 al primer intento y 10/10 tras dos
  reparaciones, 977,519 s y 105 tool calls, sin timeout ni caída. ASTRA cerró
  8/10 → 10/10 tras dos reparaciones, 773,404 s y 63 tool calls, sin timeout
  ni caída. La corrida ASTRA conserva la desviación de preregistro anotada
  arriba. Screening de una pareja; no prueba mejora estable.
- Context Retrieval IQ3_XXS se intentó una vez después de cargar Strata. Health
  previo: modelo cargado, contexto máximo 131072, imágenes desactivadas. El
  prefill alcanzó 65.536 de 115.015 tokens y después el cliente registró
  `RemoteDisconnected` a los 22,725 s, sin respuesta ni `usage`. El intento es
  inválido para score/calidad, no un 0/10. La causa raíz no se determinó; el
  control ASTRA no se inició. Se guarda el recibo en `context/iq3xxs.json` y la
  nota diagnóstica en `context/iq3xxs-infra-note.md`.
- Cierre del corte: no promover IQ3_XXS. Los perfiles productivos y el harness
  no cambiaron. Un eventual reintento de la sonda requiere primero aislar el
  cierre del endpoint; después ejecutar IQ3_XXS y ASTRA en serie con el mismo
  fixture.
