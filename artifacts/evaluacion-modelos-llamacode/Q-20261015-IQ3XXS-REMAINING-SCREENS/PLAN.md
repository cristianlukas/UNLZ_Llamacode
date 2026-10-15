# Plan — Q-20261015-IQ3XXS-REMAINING-SCREENS

**Fecha:** 2026-10-15
**Estado:** cerrado el 2026-10-15; resultados en `RESULTS.md`.
**Lock:** `611718ad-bc12-4a31-ac59-263ebbae5a53`

## Alcance

Completar sólo los screens del follow-up de IQ3_XXS que no produjeron resultado válido: (1) recuperación sintética en contexto nativo 262K; (2) el control visual ASTRA IQ3_S, que antes abortó antes de API-ready; y (3) un reintento de la réplica Computer Usage r2 abortada por AT-SPI. No repetir el retrieval 115K (10/10 en ambos perfiles), la visión IQ3_XXS ya completada, ni las réplicas CU que terminaron. Coding, TaskFlow, ADV y Server Speed ya tienen resultados válidos en la campaña original.

Audio/Charla no requiere una inferencia: el model card del candidato declara Image-Text-to-Text y el endpoint de transcripción probado devolvió 404. No se enviará audio ni se atribuirá STT/TTS al modelo.

No tocar código, perfiles productivos ni defaults; dejar logs y recibos bajo este directorio. GPU serial, un servidor por vez; no controlar `:0`, no detener procesos ajenos, no ejecutar `swapoff`.

## Guarda de recursos

El intento anterior usó una regla estática de swap ocupado <2 GiB y se bloqueó antes de cargar. El usuario ya autorizó continuar el barrido conservando swap y usando presión/actividad real. Guarda efectiva para los screens aún habilitados: antes de cargar, MemAvailable ≥32 GiB, swap libre ≥1 GiB, sin procesos CUDA de inferencia ajenos; durante la corrida, abortar si MemAvailable <20 GiB, swap libre <1 GiB, PSI some avg10 ≥80% o full avg10 ≥60% durante 15 muestras seguidas. Registrar `pswpin/pswpout`, pero no aplicar un delta global fijo: las tres cargas abortadas de 262K y la carga ASTRA elevaron `pswpout` entre 76 y 496 MiB mientras MemAvailable permaneció >75 GiB y PSI bajo 60%; el contador siguió avanzando después de detener el server. Swap ocupado por sí solo no bloquea y no se libera.

Cada screen tiene timeout de hasta 15 minutos. Un bloqueo del engine antes de API-ready cuenta como aborto de infraestructura, nunca como cero de calidad. Interrumpir y limpiar sólo procesos de esta tarea.

### Enmienda de guarda — 2026-10-15

El primer arranque de 262K fue abortado por 3.686 páginas de `pswpout` (~14,4 MiB), con MemAvailable ~81,6 GiB y PSI ~40,5%; no llegó a API-ready. El segundo llegó a 19.467 páginas (~76 MiB), MemAvailable ~75 GiB y PSI ~54%, también sin prompt. Tras detener el proceso propio, MemAvailable volvió a ~106 GiB y PSI avg10 a 3,5%; `pswpout` avanzó otras 2.124 páginas sin servidor. El techo temporal se amplió primero a 64 MiB y luego a 256 MiB. El tercer intento superó 256 MiB antes de API-ready. Se cierra 262K como bloqueado y no se vuelve a intentar.

### Enmienda de guarda para ASTRA/CU — 2026-10-15

La primera carga ASTRA superó 256 MiB de `pswpout` (~416 MiB observados) antes de API-ready; MemAvailable seguía en ~105 GiB y PSI avg10 ~34%. La segunda carga llegó al API, pero el runner recibió 404 porque envió el POST a la URL base en vez de `/v1/chat/completions`; el modelo no procesó la imagen. `pswpout` es global y no identifica qué proceso escribió páginas al swap. Para los screens restantes deja de ser un gate por delta: se registra como métrica, con piso de 1 GiB de swap libre y las guardas de RAM/PSI anteriores. No se libera swap. Se corrige el runner y se fija el endpoint antes de una única repetición ASTRA; después se intenta CU con el mismo preflight.

## Procedimiento

1. IQ3_XXS retrieval a 262.144 tokens: reutilizar el config aislado ya fijado salvo el log/output y el puerto 8351; un passkey sintético cerca del 95%, greedy/seed 4242. Acierto sólo si HTTP termina y devuelve literalmente la clave.
2. ASTRA visual: mismo holdout geométrico congelado, pregunta y parámetros que el brazo IQ3_XXS; encoder en CPU. Una pasada; comparar 11 checks exactos. Si el servidor no llega a API-ready, guardar el aborto y parar este brazo.
3. Computer Usage r2: un solo reintento (1280×800, C.UTF-8, tema oscuro) en Xvfb privado, mismo HarnessSpec y perfil IQ3_XXS; sólo reponer la réplica que abortó por snapshots AT-SPI. No acceder al escritorio `:0`.

## Criterio de cierre

Informar resultados y límites por screen, verificar puertos/procesos propios detenidos, correr `git diff --check` y liberar el lock sólo con token propio. No compilar ni correr tests de producto porque no se modifica C++/QML/core.

## Cierre

- 262K: tres arranques abortados por la guarda global de `pswpout`, ninguno
  alcanzó API-ready ni recibió el prompt. No hay score de capacidad; no volver
  a intentar este fingerprint dentro de esta tarea.
- ASTRA visual: una corrida válida con el holdout congelado, 9/11 campos
  exactos; persiste la confusión amarillo/naranja de IQ3_XXS.
- CU r2: el cálculo de Calculator pasó; Text Editor falló tras entradas
  repetidas y recuperación con snapshots AT-SPI obsoletos. El servidor estaba
  sano y el fallo cuenta como resultado operacional del perfil, no como caída
  de infraestructura.
- Audio: no aplicable; no se envió payload.
- Todos los servicios propios se detuvieron; puertos 8350, 8351 y 8898 cerrados.
  No hubo cambios de producto ni build/tests de producto.
