# Q35 · Holdout de contexto largo Flash-Next · 2026-10-22

**Prioridad:** P1 · Qwen3.8-Flash-Next ASTRA IQ2_XS
**Pregunta:** ¿la recuperación selectiva sigue siendo fiable con consultas reformuladas, registros distractores y valores contradictorios al 95,5% de 131K, 262K, 512K y 1M tokens?
**Lock de cola:** `Q-20261022-VF-PENDING-AUDIT`, token `20f0de1a-7953-4c05-95f8-f6a5b73fac26`.
**Estado:** holdout preregistrado; los intentos 04–06 del fixture `131072:2026101` son inválidos de infraestructura; el intento 06 inició carga de Strata pero no envió solicitud ni produjo score. La causa de su aborto (contador global de swap no atribuible) quedó diagnosticada y corregida en Q37. Se aisló el supervisor y cada inferencia en servicios systemd transitorios fuera del cgroup de Codex.

## Razón para ejecutar

El screen existente `Q-20261014-ISTA-NEEDLE-HAYSTACK` obtuvo 10/10 una vez por tamaño a 131K/262K/512K/1M con una sola plantilla de diez hechos, claves/etiquetas explícitas y sin holdout. Eso permite afirmar que ese fixture se recuperó, pero no respalda la misma recomendación para datos contradictorios o consultas paraphraseadas. Este holdout puede cambiar el límite recomendado por perfil; no cambiará modelos ni el default global.

## Diseño fijo

- Perfil exacto: ASTRA DEFAULT, ISTA-DASLab Qwen3.8-Flash-Next GSQ-RCO IQ2_XS, Strata 0.1.41, runtime/GGUF/MTP y bundle fijados en `Q-20261014-ISTA-NEEDLE-HAYSTACK/receipts/effective-profile-manifest.json`.
- Contextos seriales: 131.072 nativo, 262.144 nativo, 524.288 YaRN ×2 desde 262.144 y 1.048.576 YaRN ×4 desde 262.144.
- Tres holdouts deterministas independientes por contexto, seeds de fixture `2026101`, `2026102`, `2026103`; ocho casos por holdout. Cada caso tiene registro `FINAL_APPROVED` y registro contradictorio `REVOKED` (incluidos registros revocados posteriores al aprobado), además de distractores con campos/códigos similares. Las preguntas reformulan campo y selección de estado, y piden un único objeto JSON con ocho valores exactos.
- Total objetivo de prompt: 95,5% del límite, calculado con el tokenizer de la revisión local. Una solicitud por servidor; servidores y GPU en serie. Temperature 0, top-p 1, top-k 20, thinking desactivado, caché de prompt desactivada; `max_tokens=768`; timeout duro 1.200 s por intento.
- No se modifica ningún perfil o archivo de modelo productivo; no se descarga ni compila software. La app y los perfiles ASTRA/SOL/Flash-Next, PeritoSoft y sus pesos quedan intactos.

## Umbrales y detención

- Antes de cada solicitud: comprobar lock propio, ausencia de procesos/listeners de servidores de inferencia, puertos del runner libres, MemAvailable ≥80 GiB, SwapFree ≥1 GiB, PSI de memoria no sostenida, ≥5 GiB libres en el volumen de resultados y que los hashes de pesos/runtime/config coincidan con el manifiesto anterior. La GUI no es un bloqueo; no se mata ningún proceso ajeno.
- Antes de iniciar cada modelo, el supervisor verifica contra `fixtures-manifest.json` el SHA-256 en bytes del prompt y el SHA-256 del JSON esperado con serialización canónica ordenada; la reanudación se bloquea si alguno no coincide.
- El supervisor persistente y cada corrida se lanzan como servicios transitorios separados en `background.slice`. Strata no debe heredar el cgroup `app-org.chromium...scope` de ChatGPT/Codex. Si systemd-oomd vuelve a detectar presión, la unidad de inferencia queda como víctima aislada; los resultados parciales y el progreso sobreviven en archivos y journal. El monitor revisa PSI del cgroup de inferencia y de `user@UID.service`; a 50% sostenido en el user-manager detiene el worker tras cinco muestras (el sistema configura >20 s), y mantiene el gate general del runner a 80/60%. No se cambia el contexto, cuantización, perfil, archivos del modelo ni reparto de GPU.
- Una corrida es válida sólo si el servidor acepta ≥95% del contexto, responde HTTP 200, termina con `stop`, retorna JSON con exactamente las ocho claves esperadas y no se activa la guarda de recursos. Infraestructura incompleta no cuenta como score de calidad. Un fallo de infraestructura sólo puede volver a intentarse después de registrar una causa concreta, corregirla y preregistrar un nuevo preflight; no se repite una respuesta válida. Q35-06 fue el intento tras el aislamiento Q37 y falló por un guard global no atribuible; Q35-07 es la única reanudación preregistrada tras diagnosticar y corregir ese guard. Si vuelve a fallar por infraestructura, detener y diagnosticar, no repetir automáticamente.
- Un tamaño pasa el holdout sólo si sus tres corridas son válidas, cada una obtiene 8/8 y ninguna selecciona un valor `REVOKED`. Un tamaño con corrida de infraestructura inválida queda inconcluso; no se imputa cero.
- Si 1M falla la calidad en una respuesta válida, continuar con tamaños menores para hallar el límite respaldado. Si hay abortos de memoria/PSI/swap o falta de servidores/recursos, detener y conservar el siguiente punto de reanudación.
- Aun pasando, el resultado sólo valida este holdout sintético y el perfil/runtime indicado; no demuestra calidad general, tareas coding/agente, ni superioridad frente a SOL. La promoción o el aumento del default global queda fuera de Q35.

## Diagnóstico de cierre de Codex y recuperación

- A las `2026-10-22T13:17:27Z`, `systemd-oomd` terminó `app-org.chromium.Chromium-833601.scope` bajo presión sostenida del cgroup de usuario: uso máximo 112,9 GB, PSI local `some.avg10=90,01%` y presión del user manager 63,31% frente al umbral 50% durante más de 20 s. El cgroup tuvo ~101,8 GiB en páginas de archivos y ~3,2 GiB anónimos. En ese mismo scope corría el proceso de Codex y el servidor Strata porque el harness los lanzó como hijos del turno; el app-server anterior dejó de registrar y al reabrir Codex el turno reportó una llamada de herramienta sin salida. No hubo request Q35 ni error de GPU.
- La prueba de aislamiento confirmó que `systemd-run --user --slice=background.slice` asigna el proceso a un cgroup distinto del scope del escritorio. El supervisor registra `active_run` antes de cada inicio; cada corrida obtiene su propia unidad, cgroup, `preflight.json`, journal y logs. El cambio desacopla el ciclo de vida de las pruebas de la app y conserva intacta la configuración/modelo de 131K a 1M.
- Se congela esta recuperación como nuevo intento de infraestructura antes de otra inferencia. Ante presión sostenida, se detiene una sola corrida y se conserva su estado como inválido; no se reduce el modelo/contexto ni se reporta score.
- Intento 4 (13:35:58–13:36:33 UTC): preflight pasó con 114,234 GiB disponibles y PSI inicial 0%; Strata seguía cargando expertos a los 23 s y el worker aislado alcanzó 3,9 GiB. La corrida no llegó a crear `request.json` ni a enviar solicitud. El runner terminó con `AttributeError` al calcular `sum(None.values())`, antes de escribir recibo; el escritorio permaneció vivo en su cgroup. Se añadió `score_response()` para mantener nulos los métricos sin respuesta y dos regresiones. Intento 5 está documentado; el guard detuvo el worker y no se habilitan más reintentos mientras persista esa presión.
- Intento 5 (13:38:52–13:39:27 UTC): mismo modelo y fixture, en la misma unidad aislada. El PSI del user-manager alcanzó el guard alineado con systemd-oomd; el runner detuvo únicamente el worker después de 35 muestras, con pico de memoria del servicio de 5,1 GiB. La corrección produjo un recibo completo con calidad nula y request=false; ChatGPT/Codex siguieron vivos y no quedó servidor. No volver a intentar bajo esta condición repetida; el resto del barrido queda bloqueado hasta que cambie la presión externa del user-manager.

## Enmienda Q37 · alcance real del aislamiento y reanudación

El aislamiento original usaba `systemd-run --user --slice=background.slice`; aunque el cgroup del worker era distinto del scope de la GUI, seguía siendo descendiente de `user@1000.service`. Por eso un OOMD kill de ese servicio padre podía cancelar supervisor y prueba. A partir de Q37, el supervisor y los workers se crean con `sudo systemd-run --system`, User/Group 1000, en el `background.slice` del gestor **del sistema**, fuera de `user.slice`. El monitor registra el PSI del user-manager, pero no lo aborta por PSI intermedio aislado. Siguen activos el piso de memoria, swap-out, PSI severo global/run-cgroup y límites MemoryHigh/MemoryMax/MemorySwapMax por servicio.

La regresión CPU-only ahora pasa 15/15. Un test sintético system-manager con MemoryMax=128 MiB terminó sólo su cgroup y dejó vivos controlador, ChatGPT y Codex app-server; Q35 detectó desde esa ruta tanto el cgroup del worker como el PSI de user@1000. Q37 también elevó el límite del servicio de usuario a 70% sin desactivar OOMD. No se ejecutó inferencia en esta enmienda; los intentos 4–5 siguen siendo inválidos. Ver `../Q-20261022-VF-ITERATION-37/RESULTS.md` y `../Q-20261022-VF-ITERATION-37/receipts/system-service-oom-containment.json`.

Una vez confirmado el lock propio y el preflight completo, reanudar exactamente `131072/2026101` como una unidad system-manager. No usar workers antiguos iniciados con `systemd-run --user`; no contar infraestructura fallida como score ni alterar el perfil.

## Orden de la cola tras Q35

P1 Flash-Next (holdout de contexto y gates de runtime) → P2 Qwen3.8-27B (calidad/seguridad ya medida; OpenJet bloqueado por compatibilidad) → P3 RCO (gate cerrado para la misma revisión) → P4 Swift (acceso/licencia/runtime bloqueados) → P5 Strata/claims nuevos comparables. No repetir screens finalizados salvo cambio material que pueda alterar la decisión.

## Artefactos

- Fixtures/receipts/scripts de Q35, en este directorio.
- Diagnóstico y política de aislamiento del proceso en `receipts/codex-crash-diagnosis.json` y `scripts/start_context_holdout_supervisor.sh`.
- Informes y recibos históricos inmutables de Q29–Q34 y del screen Q14.
- Reconciliación de Accionables local y Google Sheets, con readback, al cerrar Q35.
