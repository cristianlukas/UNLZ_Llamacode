# Qwen3.8-Flash-Next GSQ-RCO Coder — revisión del post

## Resultado

**Auditoría documental completada; no se descargó ni se ejecutó un benchmark nuevo.** El post de r/Qwen_AI informa Strata, contexto configurado en 262K, “Q3_XSS”, cerca de 130 tok/s decode y otra cifra de 4.000 tok/s sin aclarar su métrica. No publica revisión de pesos, prompts, suite, longitud efectiva, logs o recibos por seed.

La etiqueta del quant no coincide con las fuentes del publicador/runtime que se pudieron verificar: la tarjeta de ISTA-DASLab presenta el Coder podado como IQ1_M; retiene 256 de 512 expertos y enumera 58,4 GB de archivos, con 29,6 GB de pesos residentes. Strata también lo describe como IQ1_M. Por eso no atribuyo al post el resultado del IQ1_M local histórico ni lo renombro como Q3_XSS.

## Evidencia local previa reutilizada

El checkout ya conserva la auditoría del **ISTA Coder IQ1_M**, revisión `5348543e0147355ac9cbcb031184a3546350988e`, con dos hashes de shards y sus resultados en `docs/qwen38-flash-next-gsq-rco-coder-audit-20260930.md` y `artifacts/qwen38-gsq-rco-coder-eval-20260930/`:

- BigCodeBench-Hard-8 directo: 2/8, con transporte válido en 8/8; el control Genesis obtuvo 1/8. Es un fixture pequeño, no LC-H1 ni Hard Mode de 28 tareas.
- Contrato básico de herramientas: 5/5.
- Decode corto: mediana 62,39 tok/s en cinco pasadas; control Genesis 56,35 tok/s. El registro del candidato lleva `mtpDraftMax=4` como metadata, pero el servidor no tenía speculative decoding habilitado; no equivale a una comparación MTP.
- Computer Use textual: exactitud 100% en dos órdenes y 97,92% en el tercero con thinking apagado; el gate completo perdió por latencia (+33% en sandwich). Un smoke de visión funcionó 3/3.
- LlamaCode LC-H1 quedó bloqueado por el binario ausente en el daemon de test. El máximo de contexto del ensayo fue 65.536; no se validó 262K.

Estos resultados son de un perfil anterior y no comparten la suite Hard Mode 2.8.0 de 28 tareas. No tienen el tiempo total de tres seeds, así que **no pasan ni fallan** el corte de 30 minutos por perfil. No los incorporo como celda comparable en la tabla 28×3.

## Preflight y decisión

La búsqueda local halló el puntero de revisión en la caché de Hugging Face, pero no un snapshot ni los shards del Coder. Sí están instalados los modelos ISTA IQ3_XXS e IQ2_XS regulares; no son el Coder podado. La GPU0 está ocupada por ArtCraft y la GPU1 presentó utilización variable; no reservé ninguna. No descargué el artefacto oficial de 58,4 GB ni ejecuté otra prueba. El detalle está en `receipts/local-preflight.json`.

El post sirve como pista, no como evidencia de una mejora. Para admitir el perfil en la comparación de interés habría que fijar qué variante se pretende probar, y medir la misma suite con tres seeds y un tiempo total por perfil de como máximo 30 minutos. La corrida de contexto 262K queda **no evaluada**: la ficha de Qwen permite configurar esa longitud, pero la evaluación previa llegó sólo a 65K.

**No se promueve perfil ni se modifica HarnessSpec o configuración productiva.** Sin cambio en los resultados anteriores.
