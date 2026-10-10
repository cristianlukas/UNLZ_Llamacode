# Prueba local de Flash-Next Q4 y el reclamo de 4×P100

- **ID:** `Q-20261010-FLASHNEXT-Q4-P100-POST`
- **Estado:** Completada bajo el token
  `6be4e333-caa3-4c31-ab4f-8f4a1df19fcb`. Se priorizó por pedido explícito
  mientras las tareas anteriores seguían en cola. La corrida válida usó las dos
  RTX 3090; el smoke preliminar de una GPU se conserva aparte y no se puntúa.
  Resultado dual: LC-H1 29/29 final (25/29 primera pasada) y ADV v1 10/10 final
  (7/10 primera pasada). Informe: [`RESULTS.md`](RESULTS.md).
- **Objetivo:** probar un checkpoint Q4 de Qwen3.8-Flash-Next en una tarea de
  coding/agentes de LlamaCode y medir rendimiento local; delimitar qué parte del
  reclamo del post se puede trasladar a esta máquina.
- **Post de referencia:** [Strata takes the promise of “MoE models just need a
  total amount of VRAM+RAM” and makes it a reality](https://www.reddit.com/r/LocalLLM/comments/1wx3g89/strata_takes_the_promise_of_moe_models_just_need/).

## Por qué no hubo prueba Q4 antes

La campaña anterior se enfocó en ISTA IQ3_XXS frente a ASTRA IQ3_S. El post
posterior reporta “Flash-Next Q4”, Q8 KV, 262K y cuatro P100, pero no identifica
el formato concreto del GGUF en el texto recibido. El smoke 262K ejecutado
entonces era sólo una comprobación de recursos para IQ3_XXS: se abortó antes de
cargar el modelo porque había 3,253 GiB de swap usado y la guarda preregistrada
exigía menos de 2 GiB. No es un fallo del modelo ni un resultado Q4.

## Dependencias y condiciones

La tarea se priorizó por solicitud del usuario; las evaluaciones previas siguen
Pendientes y no se declaran completas. Si `Q-20261010-STRATA-UDIQ4XS-POST`
identifica el mismo repositorio, revisión y SHA-256, reutilizar sus recibos y no
repetir la misma huella. El host tiene 2×RTX 3090 y 132,6 GB RAM. Aunque la receta de setup para precargar el Q4 completo estima ~135 GB, existe un precedente válido en este equipo con el mismo checkpoint y ambas 3090: `Q-20261005-DUALVRAM`, LC-H1 39/39 con Strata 0.1.39. Esta corrida usa Strata 0.1.41 en dual GPU, split 18/30, `--resident-experts` y reserva VRAM de 2048 MiB; no usa `--resident-budget-gib`, que no es compatible con `--layer-split`. No reproduce 4×P100 ni el post completo.

Antes de cargar o descargar:

1. El post sólo dice “Flash-Next Q4”. Elegir un artefacto identificado y etiquetar
   el resultado como prueba representativa, no réplica del post. Hecho: Unsloth
   UD-Q4_K_XL, revisión `38bb39e`; los cuatro hashes de shard fueron verificados.
2. Preflight: 113 GiB RAM disponible, 460 MiB swap, ~197 GiB libres en el disco
   del modelo. Se usaron GPU 0 y 1 por indicación expresa; carga y evaluación
   terminaron sin CUDA/OOM. El swap observado permaneció debajo de 2 GiB. No se
   forzó un intento de 262K.
3. Registrar perfil/fingerprint efectivo, Strata/runtime, flags, contexto, KV,
   MTP, caché de expertos, sampling, seed, HarnessSpec y hashes de las suites.
4. Usar ASTRA IQ3_S como control de familia donde sea comparable; reutilizar
   IQ3_XXS de la campaña anterior como referencia histórica, sin repetir sus
   fingerprints salvo que exista una hipótesis explícita de variabilidad.

## Pruebas previstas

- Screening de coding/agentes: HE0 → HE20 → BCB8 y ADV v1 complementaria,
  ejecutados con `agent-maximo`, thinking, seed 4242 y el mismo HarnessSpec de
  la campaña Strata. TaskFlow ULTRA quedó fuera de esta corrida.
- Rendimiento: no se ejecutó Server Speed v1 independiente. Se conservaron
  `avgTps` de las suites y telemetría de prefill/decode de Strata; no comparar
  las cifras del post directamente con 2×3090 ni con runtimes distintos.
- Contexto: 262K sólo con el preflight aprobado y un prompt con posiciones de
  recuperación verificables. Ventana configurada no equivale a tokens
  procesados ni retrieval correcto. Si no pasa la guarda, registrar bloqueo y
  no score.
- Computer Usage E2E, visión e Ingi-Charla permanecen sin evaluar mientras no
  haya fixtures, controles y verificadores adecuados.

Para una mejora estable hacen falta al menos tres corridas válidas emparejadas
por perfil; con menos, el resultado será screening provisional. No cambiar
perfiles productivos ni HarnessSpec por una sola corrida.

## Cierre

Resultados válidos: HE0 1/1; HE20 20/20; BCB8 4/8 → 8/8; ADV v1 7/10 → 10/10.
El conjunto suma 32/39 al primer intento y 39/39 final tras reparación, sin
timeouts. La evaluación se mantuvo en el contexto máximo de 131072 tokens.
No se probó TaskFlow ULTRA, Server Speed independiente, Computer Usage GUI,
visión, audio ni retrieval 262K. No se modificaron perfiles ni HarnessSpec.

El daemon de LlamaCode y Strata fueron detenidos al cerrar; los puertos 8898 y
8350 quedaron cerrados y la GPU regresó a uso de escritorio. La evidencia
detallada está en [`RESULTS.md`](RESULTS.md) y `receipts/`.
