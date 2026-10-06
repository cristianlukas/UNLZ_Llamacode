# A/B complejo: SOL vs ASTRA IQ3_S calibrado — 2026-10-06

## Dictamen

En la única pareja que completó la tarea, ASTRA quedó ligeramente por delante en los criterios finales: **12/13 frente a 11/13 de SOL**. Ambos generaron el proyecto, compilaron el paquete y fallaron el mismo self-test funcional: deshacer una tarea completada. ASTRA pasó todos los tests unitarios que generó (43/43); SOL pasó 36/37 y falló `test_undo_reverts`. ASTRA completó esta corrida en **177,390 s**, SOL en **589,364 s**. La diferencia de tiempo es de extremo a extremo en dos runtimes distintos y una sola muestra: no es una comparación pura de velocidad de modelo.

Esto es evidencia favorable a ASTRA para esta tarea coding, **pero todavía no prueba que sea globalmente más inteligente que SOL**. Además, dos de tres intentos de ASTRA se abortaron antes de producir el proyecto al activar el guard de LlamaCode por más de 64.000 caracteres previos al primer uso de herramientas. Son fallos de ejecución/harness y se excluyen de la nota de calidad; sí muestran una posible fragilidad operacional del modelo bajo esta instrucción larga.

## Diseño

- Tarea: `TaskFlow ULTRA E2E`, creación desde cero de un gestor Python de proyecto/equipo con diez módulos, dependencias, recurrencia, historial/undo, concurrencia, persistencia JSON atómica, filtros, reportes, CLI y self-test.
- Aceptación: diez archivos requeridos, `py_compile`, tests `unittest` generados en el workspace y `--self-test`.
- La suite se convirtió a comandos válidos para Linux sin cambiar alcance funcional.
- Mismo prompt, workspace limpio por corrida, harness legacy v1, `agent-maximo`, seed 4242, temperatura 0,1, `maxTokens=32000`, timeout 1800 s; HarnessSpec `sha256:cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`.
- SOL usó el runtime vLLM Qwen3.8-27B AutoRound INT4; ASTRA, Strata 0.1.35 con IQ3_S calibrado, MTP y las dos RTX 3090. El perfil ASTRA tuvo contexto máximo 131.072, KV int8, `spec-min-p=.70` y `pcie-frac=.00`.

## Resultados

| Perfil | Corrida válida | Final | Compilación | Tests unitarios producidos | Self-test | Tiempo total | Archivos / líneas añadidas |
|---|---:|---:|---:|---:|---:|---:|---:|
| SOL AutoRound INT4 | 1/1 | 11/13 | pasa | 36/37; falla `test_undo_reverts` | falla al deshacer `complete` | 589,364 s | 20 / 1.760 |
| ASTRA IQ3_S calibrado | 1/1 | 12/13 | pasa | 43/43 | falla al deshacer `complete` | 177,390 s | 20 / 1.969 |

Las dos corridas adicionales de ASTRA se clasificaron como `infrastructure`, no como calidad: el modelo excedió el límite preventivo de 64.000 caracteres antes de usar herramientas. Duraron 62,931 s y 36,167 s; crearon sólo un archivo de borrador y no constituyen una prueba completada. El guard no se desactivó ni se relajó.

## Recomendación

- **Para seguir evaluando un Flash-Next que pueda superar SOL en coding, priorizaría ASTRA calibrado como candidato**: la única tarea compleja emparejada lo favorece por un punto y el tiempo observado fue menor. Mantener ese dictamen como provisional hasta completar al menos otra pareja válida con suite independiente o una repetición válida.
- **No borraría Swift IQ3_XXS aún**: no se probó inferior en esta comparación y su prueba previa de Computer Use textual tuvo la misma exactitud que ASTRA con menor latencia. Si la restricción de espacio obliga a elegir un único Flash-Next hoy, ASTRA es el candidato de calidad/coding y Swift el de menor espacio/latencia breve; la evidencia disponible no convierte a Swift en “claramente peor”.
- El resultado no justifica cambiar SOL del perfil diario ni modificar el harness. Ambos fallaron el mismo caso de undo/complete; eso marca un borde de calidad que conviene convertir en una comprobación independiente común antes de promover ASTRA.
- Los modelos UD-Q3 y UD-Q6 retirados del volumen D se quitaron por espacio/flujo de uso según la instrucción del usuario; no se afirma que sean universalmente inferiores. AP-Q3 válido permanece y tampoco tiene A/B LC-H1 concluyente frente a SOL.

## Trazabilidad

- Resultados crudos, config y hashes: `results.json`, `manifest.json` y `strata-iq3_s-calibrated-retest-20261006.json` en este directorio.
- El benchmark persistió sus workspaces en `/home/cristian/.qttest/share/LlamaCode/LlamaCode/benchmark-runs/`.
- Carpeta ASTRA descargada y preparada: `/media/cristian/Disco local/Models/ASTRA-IQ3_S-calibrated-20261006` (93.000.847.852 bytes, 56 archivos).
- El servidor Strata de prueba se detuvo al terminar; puerto 8350 cerrado. El daemon con estado aislado se cerró; puerto 8897 cerrado. SOL vLLM quedó detenido como estaba. GPUs tras limpieza: 986 MiB usados en GPU0 y 108 MiB en GPU1 al verificar.
- Limpieza de modelos D: `../qwen38-27b-storage-audit-20261006/decision.md` y `cleanup-receipt.json`.
