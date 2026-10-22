# Q35 — diagnóstico y prevención del cierre de Codex

## Hallazgo

El cierre del 2026-10-22 fue causado por `systemd-oomd`: el harness lanzó Strata como hijo de la herramienta de Codex dentro del mismo scope `app-org.chromium.Chromium-833601.scope`. Bajo presión sostenida, systemd-oomd terminó el scope completo. El pico registrado fue 112,9 GiB; PSI del scope 90,01% y del `user@1000.service` 63,31% frente al umbral 50% durante más de 20 s. No hubo OOM del kernel ni Xid de NVIDIA. Strata todavía cargaba pesos/expertos; no se envió un request válido.

## Cambio preventivo

El supervisor y cada inferencia corren en servicios transitorios separados bajo `background.slice`, cada uno con su cgroup, journal y estado persistente. La corrida vigila PSI y se detiene dentro de su unidad antes de que systemd-oomd pueda cerrar el escritorio. El runner rechaza iniciar si no está en el cgroup esperado. No se redujeron pesos, contexto, cuantización, perfil ni memoria lógica, ni se cambió el reparto de GPU.

## Verificación

- Intentos 4–5 cargaron el mismo artefacto y contexto 131K en cgroups aislados. La carga llegó a 3,9 GiB y 5,1 GiB de pico de unidad respectivamente; el escritorio siguió vivo en su cgroup.
- El intento 4 mostró un error de manejo de ausencia de respuesta (`None.values()`). Se corrigió con `score_response()`: si no hubo respuesta, todos los campos de calidad quedan nulos; la fixture no se marca completa. Las regresiones y el guard pasaron 7/7; `py_compile` pasó.
- El intento 5 superó el guard PSI 50% y terminó sólo el worker. Codex siguió vivo, no hubo request ni score y no quedó ningún inference server. El recibo y el progreso permanecieron legibles.

## Estado

La prevención del cierre por este harness quedó verificada. Q35 no tiene aún un resultado de calidad: el barrido restante está bloqueado hasta que cambie la fuente externa de presión del user-manager y un nuevo preflight/startup permanezca bajo el guard. Siguiente paso: revisar la fuente de presión en `user@1000.service`, luego reanudar exactamente desde `131072/2026101`, con la misma configuración. No repetir mientras se reproduzca el guard; no reducir el modelo o el contexto.

Evidencia: `receipts/codex-crash-diagnosis.json`, `receipts/attempt-02-memory-pressure.json`, `receipts/attempt-04-runner-nullscore.json`, `receipts/attempt-05-pressure-guard.json`, `receipts/progress.json`.

## Registro compartido

La fila Q35 se agregó a `Evaluaciones LlamaCode` (`A266:J266`) y la recomendación P0 de aislamiento quedó primera en `Accionables` (`A2:N2`). El readback verificó los valores y el formato WRAP/TOP. El recibo de sincronización está en `receipts/google-sheet-sync.json`.

La recomendación P0 también se añadió al JSON de accionables de la app, como primer elemento; se dejó backup previo y se validó mediante el mismo `read_json()` del servidor, sin iniciar el servicio. El recibo está en `receipts/app-actionable-sync.json`.

## Corrección de diagnóstico y alcance · Q36 · 2026-10-22

La frase anterior «la prevención del cierre por este harness quedó verificada» era demasiado amplia. La lectura posterior del journal mostró que, 16 segundos después del abort controlado Q35-05, systemd registró otro proceso terminado por OOM bajo `app.slice`; el registro no nombra al PID. ChatGPT/Codex siguieron vivos y no hubo request, score ni servidor residual. Por tanto, Q35 por sí sola sólo probó aislamiento/guard para sus intentos, no contención completa frente a OOM.

Q36 corrigió este hueco para el runner Q35: `MemoryMax` dinámico a partir de la RAM disponible, `MemorySwapMax`, `OOMPolicy=kill`, `KillMode=control-group`, `OOMScoreAdjust=900` y verificación de los límites efectivos antes de aceptar un request. Una regresión CPU-only en servicio efímero confirmó que `MemoryMax=128 MiB` mata la unidad completa y no el proceso padre/Codex. La verificación fue una inyección sintética pequeña; el barrido Flash-Next sigue bloqueado por PSI y no se reanudó.

El cambio limita los recursos que puede consumir el proceso de evaluación; no reduce el modelo, el contexto, la cuantización ni el uso de memoria lógica solicitado. Esto contiene el OOM del worker, no demuestra inmunidad a fallos independientes del kernel, systemd-oomd, driver o presión generada fuera del cgroup. Q36 y sus recibos están en `../Q-20261022-VF-ITERATION-36/RESULTS.md`.
