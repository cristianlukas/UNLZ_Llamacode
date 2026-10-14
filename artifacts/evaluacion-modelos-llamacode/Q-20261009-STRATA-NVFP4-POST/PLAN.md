# Plan — Q-20261009-STRATA-NVFP4-POST

- **Estado:** completa como auditoría documental bajo token
  `b960e546-450c-4418-b633-30f435bc8e86`, reclamada
  2026-10-12T18:41:07.889851Z y cerrada 2026-10-12.
- **Objetivo:** decidir si el post de r/LocalLLM sobre OrcaRouter Qwen3.8-
  Flash-Next ModelOpt NVFP4 y Strata aporta evidencia nueva a los perfiles o
  harness de LlamaCode, revisando claims contra fuentes primarias y el ensayo
  local exacto del 2026-10-05.

## Alcance preregistrado

- Candidato publicado: checkpoint **OrcaRouter Qwen3.8-Flash-Next Uncensored
  ModelOpt NVFP4**, revisión `f24d2b68ff2814f24455ae86717be276619b5664`, y el
  fork `sergqwer/strata-nvfp4` en la revisión que el post indique.
- Evidencia local de control: ensayo dual RTX 3090 del 2026-10-05, checkpoint
  exacto ya descargado/verificado y fork NVFP4 `992195498c16ea2b26c08bf1ba2402291553136f`
  / Strata `0.1.38-nvfp4.2`, con registros en
  `artifacts/strata-nvfp4-reddit-20261005/` y
  `docs/strata-nvfp4-reddit-20261005.md`. Reutilizar esos pesos/recibos; no
  volver a descargarlos ni repetir un fingerprint idéntico.
- Contexto comparativo: perfiles locales ASTRA/SOL y el A/B reciente de
  compactación, citados con sus propios límites. No mezclar puntajes de
  distintos hardware, runtime, cuantización o HarnessSpec como A/B directo.
- Usos a evaluar por evidencia: coding/agentes, Computer Usage E2E,
  Ingi-Charla, visión, contexto efectivo y rendimiento. Un claim de runtime o
  tokens/segundo no acredita calidad de modelo ni operación real de interfaz.
- Revisión primaria prevista: fuente del post/autores, README y commits/tags del
  fork, checkpoint/model card, issues/PRs vinculados y protocolo/recibos del
  ensayo previo. Registrar fechas y SHA/commit para separar novedades reales.
- Regla de ejecución: empezar por auditoría documental. Reservar GPU y correr
  una nueva prueba sólo si aparece un cambio de fork/modelo o una corrección
  concreta que invalide o amplíe el ensayo del 05-10; en ese caso preregistrar
  A/B, gate, métricas y recursos antes de lanzar. No modificar perfiles,
  HarnessSpec, defaults ni pesos originales.

## Hipótesis y criterio de decisión

El ensayo exacto del 05-10 ya verificó el checkpoint y una ruta de ejecución:
tool call directo correcto, pero LC-H1 sólo pudo superar HE0 con prefill fijo
2K tras una reparación y 355 s; `auto`/16K, 8K y 4K activaron el watchdog del
fork. El resultado fue insuficiente para promover y no midió el 256K del post.
Esta tarea buscará un cambio posterior que haya corregido ese bloqueo o nueva
evidencia primaria comparable. Sin ese cambio, la conclusión será documental,
sin inferencia/GPU.

Para promover se requerirían pruebas válidas de calidad y seguridad,
comparación emparejada con perfil/control local, al menos tres pares para una
mejora estable, y ausencia de regresiones importantes. Una corrida bloqueada
por watchdog, CUDA, timeout o transporte no cuenta como cero de calidad.

## Preflight al reclamar

- Lock exclusivo: `b960e546-450c-4418-b633-30f435bc8e86` en host 3090.
- La comparación de compactación anterior terminó: sus servidores devolvieron
  exit code 0, puerto 8352 cerrado y las dos GPU quedaron idle.
- Pesos NVFP4 y reportes históricos ya están locales; no se requiere descarga.
- Veredicto: se verificaron la URL/identidad del post y las releases posteriores;
  no hay razón operativa para otra corrida del checkpoint Orca retirado.

## Resultado

Se verificó el post y las releases posteriores con fuentes primarias. El post
comparó NVIDIA NVFP4 con una variante abliterated en un único test sintético de
256K; el modelo local fue OrcaRouter ModelOpt NVFP4, ya verificado y probado el
2026-10-05. La release 0.1.41-nvfp4.5 retiró Orca por resultados débiles del
mantenedor en una tarea Claude Code; 0.1.42 agrega cambios de runtime, incluido
dimensionamiento de buffers, sin evidencia de que resuelva el watchdog local.
El build actualizado no está instalado y el host sólo tiene CUDA 12.0 frente a
la ruta documentada Windows/CUDA 13. No se descargó nada, compiló, usó GPU ni
repitió inferencia. SOL ya estaba descargado en la campaña previa; no se volvió
a descargar. No se promueve ningún perfil ni cambia el harness. Informe:
[`RESULTS.md`](RESULTS.md).
