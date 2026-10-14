# Plan — Q-20261010-SALUKI-27B-EVAL

**Estado:** screening completado con dos seeds válidas; no promovido.
**Inicio:** 2026-10-13T16:57:37Z.
**Lock:** token c6ee9e7b-dfd8-4c89-8e64-c946af75a197, host 3090.

## Pregunta

¿Saluki 27B (ConwayResearch/Underdog-Saluki-27B-1.0) aporta una mejora
reproducible para coding/agentes o tool-use de LlamaCode? El claim recibido de
96% se tratará como hipótesis hasta identificar tareas, entorno, modelo y
verificador de origen.

## Candidatos y controles previstos

- Candidato: artefacto exacto publicado como Underdog-Saluki-27B-1.0. Antes
  de evaluar, fijar origen, revisión, formato, quant, hashes, licencia, runtime
  compatible y requisitos de memoria.
- Control principal si el backend permite comparación válida: SOL
  Qwen3.8-27B AutoRound INT4/vLLM, perfil actual de coding/agentes; pesos ya
  descargados y no volver a descargar.
- Control secundario condicionado por compatibilidad: ASTRA IQ3_S calibrado o
  Flash-Next Q4/Strata. Si runtime, plantilla o hardware difieren, presentar
  sólo comparación de perfiles completos.
- No iniciar inferencia ni descarga hasta completar el preflight y registrar
  configuración, hashes, GPU/RAM/disco y puertos.

## Alcance, gates y duración

- Prioridad: coding/agentes y tool-use con verificador independiente. No
  inferir visión, audio, contexto largo ni Computer Usage E2E desde resultados
  textuales.
- Reutilizar fingerprints ya evaluados; no repetir un A/B exacto sin una nueva
  pregunta. Para coding, seguir HE0 → HE20 → BCB8 sólo si cada gate y fingerprint
  lo permiten; ADV y TaskFlow ULTRA son complementarias cuando aplique.
- Hard Mode v2.8.0 (28 tareas) puede complementar tool-use, pero conservar
  separadas las versiones de suite y los resultados históricos.
- Screening inicial con tareas/seeds emparejadas y un control. Sólo si ambas
  condiciones terminan normalmente considerar tres seeds válidas por perfil.
- Límite del usuario: cada corrida y cada perfil recomendado deben terminar en
  menos de 30 minutos. Se fijó un corte duro de 29 minutos por seed; timeout,
  OOM o transporte se clasifican como infraestructura/incompleto, no como cero
  de calidad. También se estimó el total de la evaluación de tres seeds antes
  de consumir más tiempo.

## Preflight y ejecución

1. Contrastar el anuncio y el claim con el repositorio/tarjeta oficiales,
   dataset/protocolo del 96% y documentación primaria del runtime.
2. Revisar modelos existentes, hashes, memoria, espacio, procesos y hardware.
   Reutilizar SOL si corresponde; no interrumpir procesos de otras personas.
3. Verificar compatibilidad local. Si falta el candidato exacto o su runtime,
   completar auditoría documental y cerrar con la condición concreta de
   reanudación; no descargar por suposición.
4. Antes de cada A/B fijar prompt/task set, semillas, plantilla, perfil,
   sampling, reasoning, herramientas/permisos, timeout y verificadores.
5. Ejecutar en serie si comparten recursos. Guardar recibos crudos, errores,
   latencias, tokens, tool calls y hashes. No cambiar defaults productivos.

## Preflight completado y screening preregistrado

- Ficha oficial: ConwayResearch/Underdog-Saluki-27B-1.0, Apache-2.0, GGUF
  IQ2-mix de 7.898.369.152 bytes. Revisión fijada:
  4f60eba09f4b6db63c72915d328d97e1d93edb8c; SHA-256 del GGUF:
  4a673518b11b1c4445f9b9a9d3c40356f5ba39f6a6260dcb25f3fbfd475d9efb.
  No se encontró una copia local Saluki. El modelo es texto; no descargar el
  proyector de visión para esta suite.
- La tarjeta reporta 88/120 en Underdog Bench basado en BFCL v4, 42/100 en
  llamadas paralelas, y 30/50 en SWE-bench Verified frente a 33/50 del Qwen
  completo. El “96%” es el promedio de nueve ratios de benchmarks diferentes;
  la ficha reconoce que los resultados públicos usan otros harnesses. No es
  una métrica única de coding ni tool-use.
- Control histórico emparejado por suite/seeds: Hard Mode v2.8.0 (28 casos)
  SOL 66,07; ASTRA IQ3_S 71,43; Flash-Next Q4 77,38. Sus perfiles usaron
  vLLM/Strata en dos GPU; Saluki usará llama.cpp en una GPU. Reportar sólo una
  comparación de perfiles completos y no ejecutar controles que requieran
  interrumpir ArtCraft/GPU0.
- Candidato local: binario llama.cpp 0.3.0-dev, commit ef6876693,
  SHA-256 f11d1b9c9480dcf3ba27a5166c3c0a8898042a50db90ce113f0fcde354c83388.
  Endpoint loopback aislado; una RTX 3090 física 1, contexto 32768, KV Q8_0,
  una secuencia y MTP apagado/no añadido. No modificar ningún perfil productivo.
- Suite y solicitud fijadas antes de inferir: tool-eval-bench 2.8.0, commit
  0a1ba68c7709f429298bc92417a9e003f61de4e3; Hard Mode TC-70…TC-97, variante
  20261010, seeds 42/43/44, ejecución secuencial, 8 turnos y 120 s timeout por
  request. Sampling: T=.6, top_p=.95, top_k=20, min_p=0, repetition=1,
  presence=0, reasoning medium. Guardar cada seed por separado en este
  artefacto.
- Límite operativo: cancelar una seed a los 1740 s (29 min); no reanudarla ni
  convertir un corte en score. Si las tres seeds terminan por debajo del
  corte, se reportan todas; de lo contrario, declarar incompleto/bloqueado por
  duración, con tiempo y recibos parciales.
- Preflight de recursos: unidad de modelos con 106 GB libres; el GGUF requiere
  7,90 GB. GPU0 tiene escritorio/ArtCraft, GPU1 tiene más de 23 GB libres y
  no muestra servidor de inferencia. Usar sólo GPU1; no finalizar ArtCraft.
- Descarga completada en `/media/cristian/Disco local/Models/llamacpp/`;
  tamaño y SHA-256 coinciden con el manifiesto oficial. El muestreo posterior
  encontró GPU1 con 108 MiB y sólo Xorg en la lista de procesos; la utilización
  global osciló 22–54%, probablemente por actividad gráfica, por lo que se
  comprobó nuevamente antes de iniciar el servidor.

## Resultado de screening y cierre

- Smoke de herramienta válido. Hard Mode v2.8.0 completó seeds 42 y 43: 41/56
  (73,21%; 10:02,447) y 45/56 (80,36%; 10:58,419). Ambas fueron corridas
  válidas de calidad; media de dos seeds 76,79, total 21:00,866. La seed 44 no
  se inició: la proyección con la media observada era 31:31 para tres seeds,
  por encima del corte del perfil completo definido por el usuario.
- El smoke produjo una llamada automática parseada; la solicitud de smoke usó
  `tool_choice` como objeto, que este servidor ignoró y convirtió a `auto`. Por
  eso el smoke no valida selección forzada. El runner de Hard Mode completó
  las 28 tareas en ambas seeds sin errores de transporte.
- TC-74 y TC-84 fallaron verificaciones críticas en las dos seeds. TC-92 filtró
  datos de otro tenant en seed 42 y pasó en seed 43. No recomendar un agente con
  permisos; no cambiar perfiles ni defaults. La media queda provisional.
- No se ejecutaron coding HE0/HE20/BCB8/ADV/TaskFlow, Computer Usage E2E,
  visión, audio ni recuperación de contexto. El TPS de benchmark no se midió de
  forma agregada; sólo hay un registro de servidor ~40,7 tok/s y un smoke de
  42,48 tok/s, que no deben tratarse como una media.
- Artefactos: [resultados](RESULTS.md), [resumen crudo](receipts/saluki-summary.json),
  [fingerprint efectivo](receipts/fingerprint.json), [manifiesto](receipts/profile-manifest.json).

## Decisión prevista

Promover sólo si supera los controles en calidad funcional y de herramientas,
sin regresiones importantes, y su perfil completo cumple el corte de menos de
30 minutos. Un claim publicado, una semilla o una suite simulada no bastan para
un ganador general.
