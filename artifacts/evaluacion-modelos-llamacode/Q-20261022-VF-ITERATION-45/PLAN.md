# Q45 — AgentToolRunner E2E de EmbeddingGemma 2

## Pregunta de decisión

¿El `hybrid_search` real de LlamaCode, ejecutado sobre el snapshot completo y limpio del repo, conserva una ganancia útil de recuperación frente a su fallback BM25 cuando se conecta el sidecar EmbeddingGemma 2? ¿El caché evita reembeber documentos en una segunda pasada y el modo sin endpoint mantiene el baseline?

Esta prueba valida sólo búsqueda de código. No evalúa calidad generativa, Flash-Next, Qwen27, RCO, Swift, Strata, ni propone cambiar el modelo productivo.

## Prerregistro y condiciones

- Lock exclusivo Q45: `947e1662-be31-451b-a4a4-f00d9f8af0ea`.
- Fixture y 21 queries/qrels: Q44 `corpus.jsonl`, `queries.jsonl`, `qrels.jsonl`; el fixture fue congelado desde `HEAD=51acfeb1299231b6678bc2e9a56ba6f07254165e` antes de embeddings. Se reutiliza como holdout sin editar sus etiquetas.
- Corpus de ejecución: snapshot de todos los archivos rastreados en ese mismo HEAD, creado con `git archive` en `/tmp`, de modo que la evaluación no lea cambios ajenos del working tree. Se usará la ruta real de `AgentToolRunner::hybrid_search` y su límite actual de 800 chunks; los elementos no encontrados dentro de ese límite cuentan como fallos, no se descartan.
- Control A: `AgentToolRunner::hybrid_search` con endpoint auxiliar vacío (BM25 fallback). Controla la misma consulta y el mismo snapshot.
- Candidato B: la misma tool y snapshot, endpoint local `llama.cpp b11554` con EmbeddingGemma 2 Q8_0, strings planas, RRF actual y sin reranker configurado. No se envían prefijos porque no son el protocolo actual de LlamaCode.
- Repetición C: segunda pasada B en el mismo proceso y caché, para comprobar rankings idénticos y ausencia de nuevas entradas-documento en el tráfico de embeddings; la query se puede volver a embeber.
- Métricas: nDCG@5 y MRR@5 calculadas sobre las 21 qrels, incluidas consultas no recuperadas. Gate de candidato: B debe mejorar nDCG@5 al menos 5 puntos porcentuales sobre A y no bajar MRR@5; C debe coincidir exactamente con B. El gate no basta para activar defaults: cualquier cambio productivo requiere revisión posterior de latencia, caché/fallback y regresiones.
- La interfaz GUI puede permanecer abierta. Antes de iniciar, comprobar procesos/puertos de servidores de inferencia y el puerto fijo; no matar procesos ajenos. Usar sólo GPU física 1 y exigir al menos 4 GiB libres en preflight. Si el server, hash, runner, snapshot o gate de fixture falla, guardar recibo y detenerse antes de cargar el modelo.
- El modelo y `llama-server` se fijan por SHA-256 a los artefactos validados en Q44: modelo `2188ac1deca4b77dffefd603c2776a9d76d9d74ec01841392982ebb840b09135`; server `fe8a7d6073d3e3a276193fcaec162cbf280d2572ad2016c9100fd924be19c6ed`.
- Servidor y prueba correrán como un árbol de procesos dentro de `background.slice` mediante `tools/linux_eval_scope.py`, con systemd-oomd activo, sin límite finito de RAM/swap y con timeout de seguridad. Nada del test comparte cache de embeddings o configuración con la aplicación del usuario.

## Implementación de evaluación

Añadir únicamente un slot QtTest opt-in a `tests/test_agent_tools.cpp`, ejecutable por nombre y saltado si faltan variables `LC_Q45_*`. El slot llamará `AgentToolRunner::executeTool("hybrid_search", ...)` en el snapshot, recopilará el `contextReceipt.returned` real para los tres brazos y escribirá un recibo externo al directorio de resultados. No modifica el código de producto. Correr primero el target `test_agent_tools`; después el gate Linux Release `scripts/tests-linux.sh Release` bajo el mismo scope.

Un proxy loopback de auditoría entre el runner y llama-server registrará sólo ruta, número de entradas, longitudes, modelo, código HTTP, demora y hash del body; no persistirá texto del repo. El resultado debe demostrar qué pasó por el caché. El endpoint del proxy y la base XDG del test estarán aislados.

## Cierre

Guardar protocolo/hash de runner, snapshot manifest, control de GPU y procesos, log del servidor/proxy, resultados por query, auditoría independiente de métricas, tests, cleanup de scope/listeners y reconciliación de `WORK_QUEUE.md`, informe canónico, actionable local y Sheets. Si el gate pasa, recomendar sólo mantener EG2 como candidato para una fase de adopción; si no pasa, no integrar y documentar la causa. No tocar perfiles productivos, inventario de modelos ni archivos de usuarios.

## Enmienda de ejecución · 2026-10-22T18:19Z

- El gate Linux Release terminó con **90/90 pruebas aprobadas** (CTest, 159.93 s).
- Un primer arranque quedó registrado en `receipts/attempt-01/preflight-or-controller-failure.json`: `linux_eval_scope.py` no transportó `LC_Q45_TEST_EXE` al proceso dentro del scope (`AgentToolRunner QtTest executable missing: .`). Se detuvo antes del chequeo de servidores/GPU y no inició ni detuvo procesos.
- Para el siguiente intento, la ruta del test se pasa como `--test-exe` y los recibos se aíslan en `attempt-02`. Los queries, fixture, modelo, parámetros, métricas y gates no cambian.
- `run_agent_tool_e2e.py` y `audit_q45.py` se compilaron con `py_compile`; el ejecutable `test_agent_tools` existe y es ejecutable en `/home/cristian/.cache/llamacode/build_tests_linux/`.

## Segunda enmienda · 2026-10-22T18:20Z

- `attempt-02` también se detuvo antes del preflight de GPU/model server: el commit contiene cuatro symlinks de modelos hacia volúmenes externos. No se siguieron ni leyeron esos destinos.
- El snapshot ahora omite todos los symlink entries de `git archive`, registra sus rutas/destinos en el manifiesto y extrae únicamente archivos/directorios rastreados; los hardlinks siguen rechazándose. Esta omisión aísla artefactos GGUF externos al corpus fuente, sin cambiar el commit, queries ni test. El reintento queda separado en `attempt-03`.
- `attempt-03` pasó los preflight: cero servidores de inferencia, puertos 8397/8398 libres, RTX 3090 GPU 1 con 24.016 MiB libres. No llegó a cargar el modelo porque el orden de opciones de `timeout` era inválido (`--signal` se interpretó como ejecutable). El recibo confirma cero procesos residuales y VRAM sin cambio. Se corrigió el orden; nuevo recibo en `attempt-04`.
- `attempt-04` ejecutó las 21 consultas y escribió sus rankings, pero el server rechazó los lotes de 64 documentos: 42 respuestas HTTP 500 informaron que 7.620 tokens excedían el `ubatch-size` 2.048. El fallback BM25 dejó ambas métricas candidatas en cero y el gate falló; esos resultados no son una comparación válida de EG2. Durante el cierre, enviar SIGTERM a todo el process group dio dos señales a llama.cpp y el controlador acabó con `-11`; el recibo confirma que no quedaron servidores ni uso de VRAM.
- Siguiente intento preregistrado: elevar sólo los tamaños de batch/ubatch del servidor de evaluación a 8.192 (el lote medido fue 7.620 tokens), y que el controlador envíe primero SIGTERM a `timeout` para que éste reenvíe una sola señal al server. El auditor ahora exige HTTP 2xx en todas las llamadas de embeddings. Sin cambios a la app, queries, fixture ni gates; recibos en `attempt-05`.
- `attempt-05` reprodujo el rechazo: 16.212 y 13.909 tokens no cabían en 8.192, por lo que el candidato volvió a fallback y el gate no es evidencia de EG2. El cambio de cierre aún dejó doble señal con `timeout`; el recibo conserva cero procesos residuales y VRAM liberada.
- `attempt-06` sube batch/ubatch de evaluación a 32.768 para cubrir el máximo observado de 16.212 con margen, y elimina el wrapper `timeout`: el QtTest tiene un límite de 720 s, la espera de health 90 s, y el scope systemd controla el árbol completo. El cleanup enviará primero una señal directa al proceso de `llama-server`. El auditor requiere que todas las peticiones de embeddings sean 2xx. No cambian la app, queries, fixture, modelo ni gates.
- `attempt-06` procesó los lotes de 16.212 tokens dentro del batch físico, pero llama.cpp rechazó 42 solicitudes con HTTP 400 porque cada lote excedía el contexto 8.192; el test volvió al fallback y el gate no mide EG2. El cierre directo devolvió exit 0, sin doble señal, proceso residual ni VRAM ocupada.
- En `attempt-07` se elevará también el contexto del server de evaluación a 32.768, igualando el máximo de batch/ubatch. Es un parámetro exclusivo de este harness, no una afirmación sobre el contexto entrenado ni una configuración productiva. Auditoría requiere que todos los embeddings devuelvan HTTP 2xx. El resto permanece idéntico.
- `attempt-07` verificó que llama.cpp pidió 26.880,75 MiB de buffers CUDA con contexto/ubatch 32.768 y no pudo arrancar con 24.016 MiB libres; el server salió antes de aceptar tráfico y liberó todo. Las tandas de entrada observadas llegan a 16.212 tokens. Para `attempt-08`, usar contexto/batch/ubatch 16.384, el mínimo que cubre esos lotes, y exigir 16 GiB libres antes de iniciar para conservar margen. Sin cambios a modelo, app, datos, ni gate.
