# Iteración 2 — VF-20261019-01

**Estado: bloqueada por condiciones externas; no quedan pruebas de modelo justificadas habilitadas en este chequeo.** No significa que todo el lote esté terminado: permanecen pruebas definidas con condiciones de reapertura.

## Revalidación

- Se releyeron `AGENTS.md`, `README.md`, `WORK_QUEUE.md` y el lock; el lock de esta iteración siguió siendo propio.
- Preflight del host a las 03:54:44 UTC: no se detectó `llama-server`, Strata, vLLM, SGLang ni listener en los puertos de evaluación. El proceso gráfico ArtCraft seguía abierto y usaba 207 MiB de VRAM; se dejó intacto. No se lanzó una inferencia ni se reservó GPU.
- MemAvailable 115.801.088 kB; PSI de memoria `some/full avg10=0.00`; OOM no fue necesario para la decisión. Aun con memoria hoy disponible, S23 sigue sin `io`/`io.max` delegado y sus intentos recientes con el mismo loader llegaron a presión de memoria sostenida antes de READY; no se repitió esa carga.
- Los artefactos UD-IQ4_XS no aportan respuestas completas reutilizables para cerrar BCB8: los timeouts no dejaron un EVAL final; el caso conocido 1019 sólo validó el grader con respuesta de referencia (5/5), no el modelo. No se reejecutó una campaña con la misma huella.
- Harness² ya pasó los canarios de egress/namespace y endpoint local, la suite determinista 5/5 y el demo 2/2. Eso valida aislamiento y transporte, no utilidad/calidad. El bloqueo actualizado es únicamente definir un workflow/componente LlamaCode y un holdout sintético fijo.

## Pruebas todavía pendientes

| Prueba | Estado | Condición concreta para reanudar |
|---|---|---|
| S36 Instagram, pedido ambiguo de empanadas | Bloqueada | Caption, transcripción, captura legible o mirror atribuible; luego fijar el fixture.
| S23 PLE FP8 | Pausada por seguridad de memoria | Un camino de carga/I/O materialmente distinto y validado en seco; alternativamente, delegación real de `io` al cgroup de usuario. Después, preregistro y preflight nuevos.
| UD-IQ4_XS BCB8/ADV/TaskFlow | Sin score final | Runner/grader reproducibles con dependencias fijadas, fallback MagicMock corregido y nueva huella del screen; no reutilizar timeouts como fallos del modelo.
| OpenJet/Qwen3.8-27B | Incompatible | Soporte del kernel para 64 bloques o un Q4_K_M compatible local; además, decisión explícita de evaluar ese perfil single-GPU.
| Harness² calidad | Transporte y mecánica completados | Definir un workflow de LlamaCode y holdout sintético no público; usar el aislamiento ya verificado.
| Swift 1.5 | Screen preregistrado, no ejecutado | Confirmar acceso permitido al artefacto y que la licencia habilita la evaluación comercial de la empresa; después verificar hash y espacio antes de descarga.

Los demás screens del lote ya tienen resultados o no aportan una prueba aplicable; no se crearon tests nuevos para llenar la cola. Se corrigió el estado obsoleto del actionable de Harness² y se agregó el screen Swift 1.5 ya preregistrado como un actionable separado, bloqueado por acceso/licencia. Se sincronizó la pestaña `Evaluaciones LlamaCode`; recibo: `receipts/google-sheet-iteration2-update-20261021T0355Z.json`.
