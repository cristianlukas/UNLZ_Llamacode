# Plan — fuente 51: Swift 1.5 Qwen3.8-27B frente al ASTRA productivo

**Experiment ID:** VF-20261019-01-S51-SWIFT15-QWEN38-CODING-AB
**Estado:** preregistrado; no ejecutado. GPU1 sigue reservada al escritorio y el acceso de descarga al repositorio oficial debe confirmarse antes de transferir pesos.

## Pregunta de decisión

¿Swift 1.5 Qwen3.8-27B con quant GSQ-RCO IQ2_XS conserva o mejora la finalización de código y el uso de herramientas del perfil ASTRA actual, con menos tiempo/tokens por tarea, y justifica agregarlo como perfil local? El test compara dos perfiles desplegables; no atribuye una diferencia sólo al fine-tuning.

## Evidencia y aplicabilidad

El post de Reddit informa que un Qwen3.8-27B cuantizado superó a GPT-5.6 Luna en un ejercicio de predicción con ruido y quedó cerca de Astra, pero tardó 5–15 veces más; una actualización posterior afirma que Swift 1.5 mantuvo la varianza explicada y terminó alrededor de 4 veces más rápido en ese problema. El artículo Hashnode enlazado devuelve 403, así que no se verificaron su dataset ni sus comandos.

La ficha oficial de UkisAI aporta una razón independiente para evaluar el modelo en coding: en sus protocolos BF16 de cinco seeds, LiveCodeBench v6 reporta 76,76% para Qwen3.8-27B y 81,71% para Swift 1.5, mientras Terminal-Bench 2.1 reporta 69,21% y 72,13%. La ficha mantiene los resultados y configuraciones, y el repositorio oficial publica respuestas y logs crudos. Es evidencia del fabricante y no se transfiere a la cuantización, runtime ni HarnessSpec local.

La ficha oficial también ofrece Swift 1.5 GSQ-RCO IQ2_XS de 8,42 GB y un paquete con MTP de 8,77 GB. La receta declara que reutiliza la asignación por tensor ISTA, añade refinamiento específico para Swift y expone manifiesto/huellas. La evaluación KLD usa fragmentos de 512 tokens y no valida calidad agentiva a contexto largo. El informe local de ASTRA IQ2_XS ya tiene HE20 20/20 tras una reparación, BCB8 8/8 y Hard Mode 28×3 con media 77,98/100; TC-92 filtró datos entre tenants en las tres seeds. Este límite de seguridad sigue bloqueando el uso con permisos/datos sensibles.

El consejo en comentarios de bajar el contexto a 32K, usar KV q8_0 o cambiar MTP no tiene evidencia primaria controlada para este host. No modifica el contexto ni la receta productiva. La petición independiente de ampliar contexto ya está cubierta en la fuente #57 y sus resultados no se mezclarán con este experimento.

## Prerregistro

### Gates previos

1. No usar GPU ni iniciar inferencia hasta que se libere la reserva externa de GPU1. Con el lock de esta cola vigente, hacer un preflight fresco de ambas RTX 3090, memoria, procesos y puertos justo antes de la prueba; ejecutar los brazos en serie.
2. Revisar acceso autorizado al repo `ukisai/Swift-1.5-Qwen3.8-27B-GSQ-RCO-GGUF`, fijar revisión inmutable, leer `release-manifest.json` y verificar SHA-256 del archivo. No exponer tokens. Si el acceso no está concedido, dejar la prueba bloqueada, sin descargar ni intentar eludir el control de acceso.
3. Verificar que Strata 0.1.41 puede cargar el paquete Swift IQ2_XS con su MTP head y `MTP4`. El modelo publicado dice que el paquete MTP requiere soporte explícito del runtime y que la calidad/velocidad MTP no fue evaluada en esa publicación. Si el soporte exacto falla, abortar esta comparación preregistrada; no cambiar a otro backend o quant durante el experimento.
4. Descargar sólo el artefacto exacto `Swift-1.5-Qwen3.8-27B-GSQ-RCO-IQ2_XS-mtp.gguf` de 8,77 GB al volumen autorizado de modelos, después de confirmar al menos 20 GiB libres y el acceso. Guardar recibo de revisión, tamaño y hash. No instalar dependencias nuevas ni compilar un runtime para forzar compatibilidad.
5. Control ASTRA: ISTA-DASLab Qwen3.8-Flash-Next GSQ-RCO IQ2_XS, Strata 0.1.41, 2×RTX 3090, contexto 131.072, MTP4, contexto de harness y sampling efectivos fijados al recibo productivo. Reutilizar la línea base sólo si los fingerprints de runner, tareas, prompts, HarnessSpec y parámetros coinciden; si difieren, repetir el control antes del candidato con el mismo holdout.
6. Candidato: UkisAI Swift 1.5 Qwen3.8-27B GSQ-RCO IQ2_XS con MTP4, Strata 0.1.41 y el mismo límite de contexto, sampling, HarnessSpec, herramientas, límites de tokens/reparaciones y condiciones de evaluación del control. No cambiar sampling ni contexto para acomodar una respuesta del modelo.

### Secuencia de evaluación

- Screen de coding: HE20 y BCB8 congelados, primera pasada y resultado final por separado, sin cambios de fixture. Registrar tests independientes, errores de infraestructura, tokens de salida, reparaciones y tiempo total.
- Avanzar sólo si Swift termina ambas suites sin fallo de transporte, logra al menos 19/20 en HE20 y 7/8 en BCB8 en primera pasada, y no introduce errores de formato/salida que invaliden la evaluación. Los thresholds son gates de screen, no prueba de superioridad.
- Si pasa, ejecutar `tool-eval-bench` Hard Mode v2.8.0, commit `0a1ba68c7709f429298bc92417a9e003f61de4e3`, 28 tareas TC-70…TC-97, `variant_seed=20261010`, seeds 42/43/44. Comparar pareado por seed con el ASTRA IQ2_XS del mismo fingerprint. Mantener T=0.6, top-p 0.95, top-k 20, min-p 0, repetition penalty 1, presence penalty 0 y reasoning medium.
- Métricas: score y victorias/empates/derrotas por seed, primera pasada, éxito final, llamadas/errores de schema y transporte, reparaciones, tokens, latencia por tarea y tiempo agregado. Sin claims a partir de una seed o de la velocidad de generación aislada.

### Gates de decisión

- Para considerar Swift como perfil coding alternativo: superar el screen HE20/BCB8 y no quedar más de 3 puntos por debajo de ASTRA en el promedio Hard Mode, con cero errores de infraestructura y sin empeorar TC-74/TC-81/TC-92.
- Para sugerirlo como reemplazo general: al menos +3 puntos porcentuales de Hard Mode, victoria pareada en al menos 2 de 3 seeds, tiempo mediano de tarea no mayor a 2× el ASTRA local y TC-92 debe pasar las tres seeds. Si TC-92 vuelve a filtrar datos, no recomendarlo para sesiones con permisos/datos sensibles aunque mejore el promedio.
- No ampliar a contexto largo, visión ni `TaskFlow ULTRA` en este test; son decisiones aparte. Verificar por separado los términos de Swift Open License v1.0 antes de una adopción comercial; la ficha limita el uso comercial libre para organizaciones por encima de US$1M de ingresos anuales y requiere licencia empresarial.

## Resultado y reanudación

No se descargó el modelo, no se hizo build, no se ejecutó inferencia, no se usó GPU y no se cambió ningún perfil. Próximo paso: en una activación posterior, volver a leer `AGENTS.md`, `README.md`, `WORK_QUEUE.md` y `WORK_QUEUE.lock`; confirmar que el lock sigue siendo de esta cola y que la reserva de GPU1 terminó. Si la reserva sigue activa, mantener este experimento pendiente y continuar con la siguiente fuente del lote. Si se libera, completar gates técnicos/acceso antes de cualquier descarga.

## Enmienda 2026-10-20 — política de GPU y compatibilidad MTP

La instrucción posterior del usuario reemplaza la reserva de escritorio como bloqueo: la GUI puede permanecer abierta y antes de una prueba se busca específicamente un servidor/proceso de inferencia. El preflight del 2026-10-20T20:22:52Z encontró ambas RTX 3090 disponibles para cómputo, ningún proceso de inferencia ni compute app, y ningún listener en los puertos de evaluación. Esto habilita el recurso, pero no supera el gate técnico de este candidato.

La revisión del modelo oficial y el runtime local cerró el gate MTP: la ficha de Swift describe el archivo `...IQ2_XS-mtp.gguf` como los pesos cuantizados completos más la cabeza MTP, con 851 tensores del modelo y 15 de la cabeza; además exige un runtime compatible con esa implementación. Strata 0.1.41 consume un paquete `rt/` producido por `tools/mtp_rt.py` desde un GGUF de cabeza MTP; el conversor espera formas Qwen/Strata fijas y produce `experts.bin`, `dense.bin` y `dense.txt`. No hay ruta verificada que ingiera el GGUF completo de Swift en ese formato. El manifiesto fija el artefacto en 8.771.311.616 bytes, SHA-256 `4414bc39d93272af91ff311e837941434aec983d5633958c08acfe48b61cab85`, revisión `d74895bbe5db4bec1e0024e7cc87d59c02d7631a`.

Decisión: bloquear esta comparación preregistrada antes de descargar los pesos. No se cambia a otro backend, quant o modo sin MTP. Reabrir sólo si se verifica compatibilidad de Strata con este formato exacto, o si se registra por separado una comparación pareada sin MTP para ambos brazos. Recibo: `receipts/source-51-runtime-compatibility-block.json`.

## Enmienda 2026-10-21 — GGUF estándar y licencia Swift

Una nueva revisión del manifiesto oficial fijó también la variante estándar, sin MTP: `Swift-1.5-Qwen3.8-27B-GSQ-RCO-IQ2_XS.gguf`, 8.422.841.632 bytes, SHA-256 `714c509c3fc496ea4abc409097658df7cd218bc966f78e1459fc1649758a9de8`. El archivo MTP original se mantiene separado y sigue bloqueado por incompatibilidad de ingestión con Strata 0.1.41.

La variante estándar no permite conservar el protocolo original MTP4. Cualquier A/B sin MTP debe ser un experimento nuevo: mismo runtime/model harness y modo sin MTP para Swift y para un control ASTRA IQ2_XS con MTP desactivado; mismo corpus, prompts, contexto, sampling, herramientas y límites. Primero debe verificarse que ambas rutas cargan sin riesgo de presión sostenida de memoria. No comparar Swift sin MTP contra el ASTRA productivo MTP4 como si el cambio fuera sólo el checkpoint.

La licencia oficial `Swift Open License v1.0` define el umbral como ingresos brutos consolidados de US$1M o más durante el último ejercicio fiscal completo, sumando entidades bajo control común; el uso comercial por encima del umbral no queda licenciado salvo licencia empresarial escrita. El manifiesto y HEAD del GGUF estándar devolvieron HTTP 200, pero eso no establece acceso autorizado ni resuelve elegibilidad comercial. No descargar pesos ni comenzar inferencia hasta confirmar esos hechos. Resultado y hashes de esta revisión: `Q-20261021-VF-ITERATION-4/receipts/iteration4-revalidation-20261021T0432Z.json`.
