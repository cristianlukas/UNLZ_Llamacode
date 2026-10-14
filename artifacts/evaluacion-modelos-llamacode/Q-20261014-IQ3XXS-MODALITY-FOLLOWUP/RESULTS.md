# Resultados — Q-20261014-IQ3XXS-MODALITY-FOLLOWUP

**Fecha:** 2026-10-14
**Estado:** Screening incremental completado con abortos preregistrados por recursos e infraestructura.
**Decisión:** No promover IQ3_XXS ni cambiar perfiles/defaults de producción. Los nuevos resultados completan parte de las modalidades pendientes, pero 262K no pudo ejecutarse y la visión no tiene control A/B válido.

## Resumen

| Prueba | ISTA IQ3_XXS / Strata v0.1.41 | Control ASTRA IQ3_S / Strata |
|---|---:|---:|
| Retrieval, prompt de 115.015 tokens | 10/10 hechos exactos, 33,461 s | 10/10, 39,110 s |
| Contexto 262K | Bloqueado por guarda: swap 7,727 GiB >2 GiB; no se cargó el perfil ni se envió prompt | No aplica |
| Visión CPU, holdout sintético | Formas 4/4 categorías; conteos de color 5/7, exact match fallido; 4,459 s | Aborto durante carga antes de API ready por swap/pressure; sin imagen enviada |
| Computer Usage E2E | Calculadora 3/3; edición exacta 1/2 réplicas completas; multiapp 2/2. Una réplica parcial abortó por AT-SPI | No evaluado |
| Audio / Ingi-Charla | Auditoría de compatibilidad solamente; GET a endpoint de transcripción devolvió 404; sin payload ni WER/CER | No evaluado |

Los endpoints, configuraciones y fixtures están aislados en esta tarea. Coding/agentes, TaskFlow y Server Speed no se repitieron; siguen siendo válidos los resultados y límites de la campaña original [Q-20261009-FLASHNEXT-IQ3XXS-AB](../Q-20261009-FLASHNEXT-IQ3XXS-AB/RESULTS.md).

## Recuperación de contexto

Se reutilizó sin cambios el fixture de 10 hechos y 115.015 tokens reportados por la API, con JSON, seed 4242 y sampling preregistrado. Tanto IQ3_XXS como ASTRA terminaron HTTP/JSON sin truncamiento y recuperaron los diez valores exactos. El corte de transporte visto en la campaña original no se reprodujo en este reintento; su causa no queda identificada. La latencia de una sola pasada no es un benchmark comparativo estable.

Recibos: [IQ3_XXS](receipts/context/iq3xxs-retry.json), [ASTRA](receipts/context/astra-control.json), [nota del intento previo](receipts/context/prior-infra-note.md).

## Contexto 262K y presión de memoria

El gate preregistrado exigía MemAvailable ≥32 GiB y swap usado <2 GiB. Tras las cargas secuenciales para retrieval y visión, el uso de swap llegó a 7,727/8 GiB; el guard falló antes de cargar el perfil 262K. No se generó ni envió el prompt. No se hizo swapoff, limpieza manual de caché ni se detuvo ningún proceso ajeno. La carga de control ASTRA para visión alcanzó swap prácticamente lleno y presión de memoria elevada; se detuvo antes de que el API estuviera listo.

Recibos: [aborto 262K](receipts/context/262k-followup-guard-abort.json), [aborto del control visual](receipts/vision/astra-control-abort.json) y logs preservados en receipts/logs/.

## Visión

El fixture holdout contiene figuras y colores sintéticos. IQ3_XXS procesó la imagen con Strata CPU vision y devolvió JSON válido en 4,459 s. Contó correctamente círculo 2, triángulo 2, rectángulo 2 y estrella 1; confundió amarillo/naranja, respondiendo amarillo 0 y naranja 2 en vez de 1 y 1. No cumple exact match. ASTRA no llegó a servir solicitudes, por lo que no hay A/B de calidad.

Recibo: [IQ3_XXS](receipts/vision/iq3xxs.json); imagen y expected están en fixtures/vision-holdout-v1/.

## Computer Usage E2E

Se usó LlamaCode daemon aislado en Xvfb :98, sólo herramientas desktop_*, dos aplicaciones genéricas (Calculator y Text Editor), API de texto y sin MCP. Se variaron resolución, locale y tema en tres réplicas. Cada escenario verificó el estado mediante controles UI, OCR y capturas por ventana. Se revisaron manualmente las capturas porque Tesseract tuvo falsos negativos con tema oscuro/contraste y en el texto del editor.

| Réplica | Entorno | Calculadora 73×19 | Editor línea exacta | Multiapp 47×29 + reemplazo |
|---|---|---|---|---|
| r1, intento 2 | 1440×900, es_AR, claro | Pasa: 1387 visible | Falla: la línea fue escrita dos veces | Pasa: 1363 en Calculator y línea de reemplazo visible |
| r2 | 1280×800, C.UTF-8, Adwaita oscuro | Pasa: 1387 visible | Abortada: cinco recuperaciones de snapshots AT-SPI obsoletos | No ejecutada |
| r3 | 1024×768, es_AR, claro | Pasa: 1387 visible | Pasa por revisión visual: la línea exacta aparece una vez | Pasa: 1363 verificado por controles y texto de reemplazo visible |

La aplicación cumplió parte del flujo entre apps, pero la inserción exacta fue inconsistente y una réplica se bloqueó en AT-SPI. Esto no justifica promover el perfil. El OCR crudo sigue conservado en cada run.json; el dictamen visual está en [assessment-summary.json](receipts/cu/assessment-summary.json). El primer intento r1 quedó invalidado antes del score porque faltaba el window manager; se preservó como [infraestructura inválida](receipts/runs/iq3xxs-base-r1/assessment.json).

## Audio e Ingi-Charla

El model card del candidato declara Image-Text-to-Text. El GET local a /v1/audio/transcriptions devolvió HTTP 404. No se envió audio, ni se midió WER/CER o respuesta acústica. Ingi-Charla sigue usando componentes separados de STT/TTS; esta corrida no evalúa su calidad.

Recibo: [auditoría de compatibilidad](receipts/audio-capability-audit.json).

## Fuente del post Strata y límites de comparación

Se fijó Strata v0.1.41 para mantener el mismo fingerprint del benchmark local previo. Sus notas oficiales indican mejoras para prompts cortos de una GPU y cargas multi-cliente; no demuestran por sí solas >200 tok/s de decode en una secuencia larga sobre dos RTX 3090. Las PR #711 y #749 se refieren, respectivamente, al streaming de KV híbrida K8V4 con --kv-resident y a capacidad de commit de Windows; esta corrida Linux usó KV int8. Upstream ya publicó 0.1.44/0.1.44.1 al momento de la auditoría, pero no se mezcló una actualización de runtime con este A/B.

Fuentes: [Strata v0.1.41](https://github.com/Niko1221/Strata/releases/tag/v0.1.41), [PR #711](https://github.com/Niko1221/Strata/pull/711), [PR #749](https://github.com/Niko1221/Strata/pull/749), [v0.1.44](https://github.com/Niko1221/Strata/releases/tag/v0.1.44). El post citado carece de hash, prompt, seed y mediciones completas y usa 2×RTX 5090/256 GB; no es una comparación directa con este host 2×RTX 3090.

## Cierre

No se tocaron C++, QML, core, perfiles ni defaults productivos. No correspondían build ni tests del producto. Se conservaron modelos, logs, requests, capturas, OCR y manifiesto de hashes. La réplica Xvfb/daemon se limpió al concluir cada corrida; el API Strata quedó apagado y se verificaron cerrados los puertos 8350, 8351 y 8898. La RAM disponible volvió a ~109 GiB y PSI a ~0; el swap quedó en ~7,7/8 GiB. No se hizo swapoff ni se detuvieron procesos ajenos. Recibo: [limpieza](receipts/session-cleanup.json).
