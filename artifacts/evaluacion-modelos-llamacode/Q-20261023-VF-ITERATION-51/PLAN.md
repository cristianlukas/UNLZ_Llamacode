# Iteración 51 — revalidación de RCO Coder y apertura de candidato Swift Flash-Next

Inicio UTC: 2026-10-23T01:52:13.514561Z  
Token de `WORK_QUEUE.lock`: `07c11d5b-bb8f-45c1-826f-1a4807e801ef`

## Objetivo

Revisar si el cambio anunciado por ISTA para RCO Coder es posterior al artefacto local probado y detectar una comparación Swift/Flash-Next técnicamente soportada que pueda cambiar el setup productivo. Esta iteración no descarga pesos, no inicia inference, no compila y no usa GPU.

## RCO Coder IQ1_M — revalidación del artefacto

La revisión probada por Q27 es `bba88856f8c3c0c9e40e45f82d05e228b814ac43`. Q27 dio BCB-Hard-8 0/8 contra ASTRA 1/8, ambos 8/8 en transporte, y no pasó el gate preregistrado ≥3/8. La tarjeta oficial informa una mejora de codificación publicada el 17 de octubre.

Consulté el árbol oficial de Hugging Face para la revisión probada y `main`: ambos contienen los mismos 13 archivos con tamaño, LFS SHA y OID idénticos. En particular, IQ1_M shard 1 es 29.608.446.496 bytes / SHA-256 `bfa3644db4adfff072fc946c20994f2909d2cf89879d83f80a4c811d4016c211`; shard 2 es 28.800.138.432 bytes / SHA-256 `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`. La revisión probada ya resolvía ambos shards a los commits actuales `d1d94679ac2fecd5ebe7af7c32e532bf3ca9c469` y `b803bd5abe65d7198c4deac8d6aaa6f2606d5334`. Por ello el anuncio ya estaba incluido en el benchmark local. No se repite ni se redescarga el Coder.

## Swift 1.5 Qwen3.8-Flash-Next IQ2_XS — nueva prueba candidata

La ficha primaria de UkisAI publica Swift 1.5 para Qwen3.8-Flash-Next en GSQ-RCO IQ2_XS: 68.152.166.976 bytes, dos shards y SHA-256 recuperado de uncompressed GGUF `eb0dcf3c752d4b282eacc902e09200c1ac1fd974b4466e43f8a07699311f6580`. SHA de shard 1 `ca3b302d3d1eb6eddce3ea4acc79854e6cc5fdc0583e374a6a8b6bb67327743b`; shard 2 `e4996a6de18fd49c58d9a0040fcfd73787db6407c51973f29884bee7b14c9dbb`.

La ficha reporta, para su evaluación BF16 del modelo, 63,4% menos tokens de pensamiento y 1,8× velocidad con pérdida de precisión <1%; su evaluación de quant usa KLD en ventanas/contexto 512, no tareas locales de coding o agente. Para IQ2_XS reporta KLD 0,341275 y mejor KLD que ISTA IQ2_XS en siete de ocho conjuntos. Son afirmaciones del publicador, no evidencia local de capacidad ni calidad agentiva.

La documentación oficial de Strata 0.2.2 (engine 0.1.47) lista Swift 1.5 IQ2_XS como modelo soportado y expone `--family swift --model IQ2_XS`; el runtime también ofrece draft/MTP para su familia. Esto supera el bloqueo anterior de Strata 0.1.41 para la familia integrada, pero no autoriza cambiar el modelo productivo. El A/B debe usar un Strata 0.2.2 aislado en ambos brazos (Swift IQ2_XS y ASTRA IQ2_XS), mismos HarnessSpec, contexto, sampling, seeds y herramientas, para comparar perfiles deployables sin mezclar versiones de runtime.

### Screen preregistrable cuando se confirme licencia

1. Descargar sólo desde la revisión oficial fijada y verificar manifest, tamaño y SHA-256; guardar el artefacto en una carpeta aislada con ≥20 GiB libres después de la descarga. No tocar ASTRA, SOL, modelos protegidos ni ningún archivo de PeritoSoft.
2. Confirmar al menos 20 GiB libres antes de la descarga y suficiencia de RAM/VRAM; revisar procesos/puertos de inference inmediatamente antes de la GPU. Ejecutar los perfiles estrictamente en serie.
3. Control y candidato en Strata 0.2.2 / engine 0.1.47, contexto 131.072, MTP configurado igual en ambos si las dos rutas pasan el loader, sampling productivo y el mismo BCB-Hard-8 congelado. Si MTP no está disponible idénticamente, detener y crear un prereg separado no-MTP para ambos brazos.
4. Screen: 8 tareas congeladas; separar transporte, primera pasada/corrección, tokens y tiempo por caso. Gate para avanzar: ambos brazos con 8/8 transporte y Swift con ≥3/8 soluciones, sin resultados inválidos. Este screen no es claim de superioridad.
5. Si pasa, preregistrar antes de correr Hard Mode v2.8.0, 28 tareas, seeds 42/43/44, pareado con ASTRA. Medir victorias/empates/derrotas, score, éxito primera pasada/final, herramientas, tokens y tiempo por tarea. No promover si TC-92 filtra información o si la calidad no pasa los gates de adopción de la campaña.
6. No iniciar descarga/inferencia hasta que Vector Fields confirme la elegibilidad de uso bajo Swift Open License v1.0 (ingresos consolidados del último ejercicio fiscal < US$1M o licencia empresarial escrita). La pregunta quedó pendiente al usuario.

## Bloqueos / siguientes pasos

- El usuario reportó que arregló Windows, pero esta ejecución de Codex sigue siendo Linux (`uname -a` indica Ubuntu); no hay `pwsh`, `cmd.exe` ni `/mnt/c`. No se puede ejecutar aquí el runner Windows nativo. Retomar P1 Windows sólo en una sesión Windows realmente disponible.
- Swift: esperar respuesta concreta sobre la licencia; luego confirmar revisión/hash actuales y elegir la ruta aislada con espacio suficiente. Sin esa respuesta, no bajar pesos.
- No se ejecutó ninguna prueba local de modelo en esta iteración.
