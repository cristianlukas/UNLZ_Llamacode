# Plan de mejora para Ingi-Charla: OpenJarvis, Dodaios y Google Workspace

**Fecha:** 2026-11-18
**Estado:** integración de origin/main y cambios locales completada; free/busy, cancelación, retry acotado, revocación OAuth y fixtures de prompt injection implementados; gate final en curso
**Tarea:** `Q-20261117-INGI-CHARLA-PLAN`

## Objetivo

Mejorar Ingi-Charla como interfaz de voz del agente de LlamaCode y sumar acceso seguro a Gmail, Google Calendar y Google Tasks. La integración debe reutilizar el pipeline de voz, el enrutador de herramientas, las aprobaciones y las primitivas de persistencia existentes. OpenJarvis y Dodaios sirven como fuentes de patrones y criterios de evaluación; no se propone desplegar otro runtime o scheduler junto a LlamaCode.

## Avance de implementación

La primera entrega conecta OAuth de escritorio con PKCE/state y callback loopback, refresh de tokens, scopes read-only para Gmail/Calendar/Tasks, cliente REST con límites y tools del agente. La segunda suma consulta de disponibilidad por separado con el scope calendar.events.freebusy, sin leer títulos ni detalles de eventos; cancela requests cuando se detiene o redirige el turno, y reintenta una sola vez respuestas 429/5xx con demora acotada. Si Google pide esperar más de 1 s en `Retry-After`, no acorta esa espera: devuelve el error para un reintento posterior. Desconectar limpia credenciales locales de inmediato y solicita revocación remota. Settings permite configurar el Client ID, conectar y desconectar; el refresh token se persiste sólo con keyring del SO o Credential Store/DPAPI, y queda en memoria durante la sesión cuando esos backends no están disponibles. Las tools respetan Modo privacidad y marcan los datos remotos como no confiables.

La versión integrada de origin/main más los cambios locales pasó el gate serial Ubuntu Release completo (105/105) después de incluir free/busy, cancelación, retry/backoff y revocación. Todavía no se validó el consentimiento real, una cuenta Google de ensayo, la ruta de voz completa ni el rendimiento acústico en la PC del usuario. Las escrituras y recordatorios siguen pendientes.

## Evidencia revisada y decisión

El enlace compartido abre la pestaña **Modelos locales por peso**. La propuesta está registrada en otras pestañas del mismo libro: **IA local** filas 153–154, **Recursos** filas 172–173, **Enlaces revisados** IDs L998–L1002 y **Accionables** fila 141 (`INGI-OPENJARVIS-DODAIOS-GOOGLE-20261117`). La fila 141 está pendiente y declara que aún no hubo OAuth real, prueba con cuenta personal ni prueba sobre el hardware del usuario.

OpenJarvis aporta ejemplos de adaptadores y una disciplina de evaluación que mira energía, latencia, FLOPs y costo junto con calidad. Su código Google debe tratarse como referencia: la revisión anotada en el libro encontró scopes compartidos y más amplios que los requeridos por un flujo inicial de lectura; Tasks de Google era sólo lectura en ese conector. Para Ingi conviene elegir permisos según cada capacidad y aplicar los gates del agente a cada llamada. Fuentes: [repositorio OpenJarvis](https://github.com/open-jarvis/OpenJarvis), [changelog de evaluación y telemetría](https://github.com/open-jarvis/OpenJarvis/blob/main/CHANGELOG.md), [OAuth de sus conectores](https://github.com/open-jarvis/OpenJarvis/blob/main/src/openjarvis/connectors/oauth.py).

Dodaios aporta una UX de voz para operaciones largas y aprobaciones con una acción y argumentos concretos. Sus propios documentos advierten que *Bypass* puede saltar aprobaciones de correo, pagos y borrado, y que algunos inicios de sesión de plugins contactan el servicio OAuth del proyecto. El plan adopta el patrón de revisar la acción exacta y descarta permisos permanentes amplios para Ingi. Hay además deriva entre sus descripciones de voz local y el changelog actual, que registra la retirada de Faster-Whisper local como proveedor seleccionable; volver a fijar versión y documentación antes de usarla como referencia de motores. Fuentes: [aprobaciones](https://github.com/Dodaios/Dodaios/blob/main/docs/product/privacy-safety-and-support/safety-and-approvals.md), [privacidad](https://github.com/Dodaios/Dodaios/blob/main/docs/product/privacy-safety-and-support/privacy-and-local-data.md), [changelog](https://github.com/Dodaios/Dodaios/blob/main/CHANGELOG.md).

La arquitectura actual ya incluye STT local Whisper/Parakeet y streaming, VAD, barge-in, TTS multimotor y percentiles de latencia. El correo existente usa SMTP/IMAP/POP3; no se encontró un adaptador directo de Google API/OAuth en los módulos revisados. Ya existen `SecretStore`, `TaskScheduler`, `TriggerManager`, tools `email_*` y tarjetas de aprobación. Referencias: [modo Ingi Charla en README](../README.md#modo-ingi-charla-voz-a-voz--agente), [auditoría de voz local](ingicharla-local-voice-audit-20260918.md), [protocolo STT streaming](voice-streaming.md), [pruebas de voz](../tests/test_voice.cpp), [pruebas de correo](../tests/test_mail.cpp).

### Mediciones de voz disponibles

La evidencia local más útil antes de proponer defaults nuevos está en [comparación de voz y multitarea](charla-multitarea-computer-use-20261105.md) y [normalización STT/TTS](charla-tts-normalizacion-20261105.md):

| Área | Comparación medida | Decisión actual y límite |
|---|---|---|
| Charla con agentes simultáneos | Primera oración: 46,9 s con 1 slot durante 3 agentes frente a 1,09 s con 4 slots y prompts precalentados; perfil sin MTP: 1,25 s peor 1,5 s y 20,5 GB VRAM | Mantener perfil multitarea sin MTP; las pruebas son de ese runtime/GPU, no una promesa universal |
| STT, 20 clips FLEURS es_419 | Whisper small: WER 6,37%, p95 1,19 s; Whisper large-v3-turbo q8: WER 3,39%, p95 2,69 s; Parakeet TDT v3 q4: WER 4,18%, p95 0,30 s | No cambiar el default: el ensayo fue CPU, una pasada y carga por clip; el perfil JARVIS usa Whisper CUDA |
| Texto hacia TTS, 20 frases | Normalizador integrado redujo WER proxy de 26,8% (48/179) a 7,3% (13/179) con Piper y Parakeet como evaluador | Conservar la normalización común a motores; es inteligibilidad estimada por ASR, no MOS ni evaluación humana |
| TTS | Kokoro: primer audio 0,33–0,35 s, similar en inteligibilidad a Piper (0,42 s); Ming: 0,97 s, sin streaming y ~2,9 GB VRAM | No cambiar el default por ahora; medir con la misma ruta acústica antes de una promoción |

Estos ensayos usan corpus/proxies y un hardware concreto. No cubren todavía micrófono→LLM→parlante en vivo, MOS, ruido doméstico ni cancelación acústica completa. La siguiente comparación debe reutilizar corpus y config congelados, sumar holdout rioplatense con nombres/fechas/negaciones y registrar p50/p95, carga fría/caliente y recursos.

Las APIs de Google fijan dos límites que deben reflejarse en producto: hay que pedir scopes estrechos; y `Google Tasks.due` conserva la fecha, pero descarta la hora. Gmail `gmail.compose` permite administrar borradores y enviar, por lo que OAuth por sí solo no separa esas dos acciones; el gate de LlamaCode debe hacerlo. Fuentes: [scopes de Gmail](https://developers.google.com/workspace/gmail/api/auth/scopes), [scopes de Calendar](https://developers.google.com/workspace/calendar/api/auth), [OAuth para apps de escritorio](https://developers.google.com/identity/protocols/oauth2/native-app), [recurso Task](https://developers.google.com/workspace/tasks/reference/rest/v1/tasks).

## Alcance funcional propuesto

1. **Lectura inicial:** buscar y resumir correos; listar eventos y disponibilidad; consultar listas y tareas de Google Tasks.
2. **Escritura gradual:** crear borradores, crear o actualizar eventos y crear, actualizar o completar tareas. Envíos, invitaciones, cambios externos y borrados siempre pasan por confirmación explícita.
3. **Recordatorios locales:** registrar hora y zona horaria en LlamaCode. La primera versión debe declarar si notifica sólo mientras la app está abierta; el `TaskScheduler` actual vive dentro de la app. Avisos con la app cerrada requieren un alcance separado de ejecución en segundo plano por plataforma.
4. **Evaluación de voz:** medir calidad acústica y latencia con corpus controlado; no inferir calidad de voz desde benchmarks de texto ni activar un motor nuevo por afirmaciones del README de un proyecto externo.

Fuera de la primera versión: un segundo agente supervisor, un segundo scheduler, autonomía sin límites, borrado permanente de correo y envío sin aprobación.

## Arquitectura y límites de seguridad

- Implementado: `src/core/google/` contiene OAuth de escritorio PKCE y el cliente REST de lectura; usa Qt Network y no añade runtime aparte.
- Implementado: navegador del sistema, `state`, callback loopback IPv4 en puerto efímero, timeout, refresh, validación de scopes y revocación remota asíncrona al desconectar. La limpieza local es inmediata aunque falle la llamada a Google; el estado informa cuando Google no confirma.
- Política de secretos implementada: `SecretStore` sólo persiste el refresh token con keyring del SO o Credential Store/DPAPI. Sin backend seguro, queda en memoria hasta cerrar la app; nunca se escribe en configuración ni logs.
- Scopes de lectura: Gmail lectura, Calendar eventos lectura, Calendar disponibilidad y Tasks lectura. El endpoint free/busy usa calendar.events.freebusy; no se solicitan scopes mutadores.
- Cinco tools de lectura Google reutilizan `AgentToolRunner` y el gate del agente. Envío, borradores y cambios de Calendar/Tasks siguen fuera de esta entrega; cada escritura futura necesita capability, preview y aprobación ligada al payload exacto.
- El contenido del correo, título de evento y descripción de tareas son entrada no confiable. Las instrucciones incrustadas no pueden otorgar permisos ni autorizar escrituras. Si un perfil cloud procesa contenido sensible, advertir qué texto/audio sale del dispositivo y exigir opt-in explícito.
- Registrar estado técnico y resultado, no cuerpos de mensajes, tokens ni audio. Una respuesta ambigua tras timeout deja el efecto como `uncertain`; consultar Google antes de reintentar para evitar duplicados.
- Para fechas/horarios, guardar zona IANA explícita y probar `America/Argentina/Buenos_Aires`, cambios de día, recurrencia y reinicio. Google Tasks es una lista con vencimiento por día; la hora exacta pertenece al recordatorio local.

## Mapa de archivos implementados y siguientes

| Área | Código actual / candidato |
|---|---|
| Voz y confirmación hablada | `src/core/voice/VoiceController.*`, `VoiceAssistant.*`, `SttEngine.*`, `TtsEngine.*` |
| Tools y política | `src/core/agent/AgentToolRunner.*`, `LlamaAgentBackend.*`; seis tools Google de lectura conectadas, clasificadas como read y bloqueadas en Modo privacidad |
| Correo y cuentas | `src/AppController.*`, `qml/components/SettingsMailSection.qml`; Client ID, estado OAuth, conectar/desconectar y scopes read-only |
| Secretos | `src/core/SecretStore.*`; persistencia sólo con keyring/DPAPI, sesión efímera si no está disponible |
| Aprobación visual | `qml/pages/AgentPage.qml` (tarjetas existentes); extender el preview para mostrar datos de Gmail/Calendar/Tasks completos |
| Agenda local | `src/core/tasks/TaskScheduler.*`, `AutomationStore.*`, `src/core/agents/TriggerManager.*`; confirmar si alcanzan para recordatorios individuales |
| Pruebas | OAuth/API mock y fail-closed del agente en `tests/test_google_workspace_*.cpp`, `test_agent_tools.cpp`, `test_agent_wire.cpp` y `test_appcontroller.cpp`; falta E2E hablado y cuenta de ensayo |
| Build/dependencias | `CMakeLists.txt` registra los módulos Google; Qt Network está disponible y Qt NetworkAuth no se necesita |

## Fases de implementación y gates

### Fase 0 — contrato y línea base

- Confirmar requisitos por acción, cuentas múltiples o única, lectura de cuerpo, retención, política cloud/local y comportamiento de recordatorios con la app cerrada.
- Congelar hashes, perfiles, contextos, sampling, micrófono, motores, drivers y corpus. Usar como controles los perfiles Charla existentes documentados en `docs/charla-balance-2x3090-20261101.md`; no cambiar defaults aquí.
- Congelar una tabla de scopes y permisos en la UI, threat model y manifiesto de datos. Definir objetivos de latencia/calidad antes de comparar cambios.

**Gate:** todas las escrituras tienen dueño, scope, preview, confirmación y resultado verificable; ninguna promesa de voz o reminder contradice la capacidad real actual.

### Fase 1 — suite de evaluación de voz

- Ampliar `tests/test_voice.cpp` sólo donde falten invariantes unitarias: estados de cancelación, fin de turno, texto parcial, interrupción TTS y fallback.
- Crear fixtures acústicos versionados para español rioplatense con ruido, pausas, nombres propios, números, fechas, correo y frases de negación. Separar corpus de desarrollo y holdout; guardar licencia/origen y hashes.
- Medir Whisper y Parakeet con WER/CER y exactitud de intención por caso; medir TTS con tiempo a primer audio reproducido, RTF, fallos y escucha humana ciega. Reportar p50/p90/p95, frío/caliente y CPU/RAM/VRAM.
- Usar el harness sintético que ya existe para pruebas rápidas; no presentarlo como evidencia acústica de micrófono/parlantes reales.

**Gate:** repetir los resultados con la misma configuración; cero ejecución de órdenes en ejemplos negativos/ambiguos; aceptar cambios de latencia sólo contra una línea base preregistrada. Objetivo provisional: p95 caliente de respuesta no regresa más de 10% sin aprobación explícita de la regresión.

### Fase 2 — OAuth y clientes API (lectura implementada)

Implementado: PKCE S256, state, callback loopback, timeout del intento, refresh y cliente REST read-only para Gmail/Calendar/Tasks, incluido el endpoint Calendar free/busy. También se implementaron cancelación del request, un retry como máximo para 429/5xx, y revocación remota asíncrona al desconectar. El cliente sólo reintenta después de 250–1000 ms; si `Retry-After` excede 1 s, devuelve el error sin hacer un retry temprano. El guardado del refresh token depende de keyring/DPAPI. Las pruebas cubren callbacks inválidos, scopes, paginación, errores HTTP, cancelación, retry y endpoints simulados.

Pendiente: build/pruebas Windows y validación con cuenta Google de ensayo. No habilitar scopes de escritura todavía.

- Implementado y probado con mocks: PKCE/`state`, callback loopback, timeout, refresh, scopes concedidos, revocación y estado de conexión.
- Implementado: cliente con timeout, límite de respuesta, paginación y errores sanitizados; cancela requests y backoff ante stop/steer; permite un retry como máximo sólo para 429/5xx dado que las llamadas actuales son de lectura. Un `Retry-After` superior a 1 s suprime el retry automático para respetar la espera del servidor.
- Implementado: persistencia segura condicionada a keyring/DPAPI; sin backend seguro no hay persistencia del refresh token.
- Implementadas pruebas simuladas de Gmail, Calendar y Tasks; se está ampliando el gate para incluir POST free/busy y sus límites. No se usó cuenta personal ni se ejecutó OAuth real.

**Gate:** scopes efectivos se validan al iniciar cada operación; el token nunca aparece en config/log/recibo; desconectar cuenta elimina su secreto y detiene refreshes pendientes.

### Fase 3 — lectura por voz (integración inicial)

Implementado: Settings ofrece conexión/desconexión OAuth; el agente expone seis tools de lectura Google, las ejecuta en AgentToolRunner y bloquea su uso en Modo privacidad. La consulta free/busy devuelve sólo intervalos ocupados y no interpreta respuestas incompletas como disponibilidad. Las tools etiquetan el contenido remoto como no confiable, y hay fixtures de prompt injection para verificar que el texto hostil llega como dato y no autoriza otras tools.

Pendiente: selector de cuenta cuando se admitan varias, identidad/correo de la cuenta origen en Settings, recorrido E2E hablado y repetición del fixture con una cuenta de ensayo.

- La búsqueda y lectura de Gmail, eventos, disponibilidad y Tasks están conectadas; validar en la siguiente corrida la nueva llamada POST de free/busy.
- Verificar con cuenta de ensayo la cancelación del request de API y transición Thinking/Ready al detener una lectura desde voz.
- Mostrar cuenta origen y fecha de los resultados; Settings ya ofrece Client ID, scopes read-only, conexión y desconexión.
- Ampliar fixture actual de correo a descripciones de evento/tarea y repetir el flujo de extremo a extremo con cuenta descartable.

**Gate:** las consultas de lectura funcionan con mocks y cuenta de ensayo; la app identifica claramente contenido remoto, errores de autorización y datos que no pudo leer.

### Fase 4 — escrituras y recordatorios

- Incorporar primero `gmail_draft`, `calendar_create/update` y `tasks_create/update/complete`. Definir validaciones y dry-run para cada tool.
- Antes de cada operación mutadora, presentar tarjeta con valores completos y reproducir una confirmación breve. Si el transcript no es claro, mantener la acción pendiente o cancelarla; no ejecutar por aproximación.
- Enviar correo sólo desde una aprobación que revele destinatarios, asunto y cuerpo; cambios de agenda deben mostrar fecha, hora, zona horaria, asistentes y efecto de notificación. Borrado permanente queda fuera del primer rollout.
- Crear recordatorios locales con ID estable, deduplicación y recuperación al reiniciar. Reutilizar `TaskScheduler`/`TriggerManager` si cubren el contrato; si no, sumar un store acotado. No afirmar entrega con app cerrada hasta implementar y probar un ejecutor de fondo para cada plataforma.

**Gate:** cero side effects en denegación, ambigüedad, acción vencida o argumentos alterados; cero duplicados en retries; toda escritura queda confirmada por lectura de vuelta o estado explícito `uncertain`.

### Fase 5 — E2E, revisión y rollout

- Probar con un usuario Google de ensayo y datos descartables. Enviar sólo a una casilla controlada; eventos/tareas creados deben llevar marcador de prueba y limpiarse al cerrar.
- Ejecutar flujos de voz completos: abrir inbox, resumir evento, crear borrador, proponer evento, confirmar/denegar, cancelar, desconectar y recuperarse de pérdida de red. No ejecutar envíos a destinatarios reales durante la validación.
- Revisar primero lectura, después escrituras internas y por último cualquier efecto que notifique a terceros. Rollout por capability flag y con apagado inmediato de la integración Google.
- Hacer revisión de arquitectura, seguridad/privacidad, UX de voz y accesibilidad, APIs/scope, persistencia/idempotencia y compatibilidad Windows/Linux.

## Matriz de pruebas

| Capa | Cobertura mínima |
|---|---|
| Unitarias | PKCE/state; serialización de cuenta; scopes; parser y paginación; errores; policy read/write; fingerprints; expiración; cancelación; fechas y DST; deduplicación de reminders. |
| Secretos | Keyring disponible/no disponible, falla al guardar, reinicio, revocación y desconexión; búsqueda de tokens en logs y archivos de configuración de prueba. |
| API simulada | 200/204, datos vacíos, página siguiente, 400, 401, 403, 404, 409, 429, 5xx, respuesta lenta, timeout y resultado de escritura incierto. |
| Herramientas/agente | Tool allowlist, autorización exacta, mismatch de payload, modo de aprobación, `mailAutoSend`, tool desconocida, reintento y contenido malicioso dentro de email. |
| Voz | Confirmaciones “sí/no/no sé”, voz cortada, ruido, eco/TTS, barge-in, cambio de idioma, alias/nombre propio, diarización inexistente y transcripción que cambia luego de aprobar. |
| Integración local | Cuenta de ensayo; no credenciales personales; estados de UI; latencias de turno y audio; cancelación cuando backend o endpoint caen. |
| Plataforma | Windows: build Debug y `tests.bat Debug`; Ubuntu: `./scripts/build-linux.sh Debug` y `./scripts/tests-linux.sh Release`. X11/AT-SPI para pruebas foreground Linux. |

## Revisiones requeridas antes de habilitar escrituras

1. **Seguridad:** scopes efectivos, PKCE/state, keyring, revocación, prompt injection, redacción, autorización no eludible por modos automáticos.
2. **UX:** preview legible/escuchable, destinatarios inequívocos, confirmación simple, cancelación disponible, accesibilidad y fallback cuando no hay voz.
3. **Datos:** qué texto/audio ve cada modelo; retención de summaries y recibos; configuración cloud/local; cuenta y scope visibles.
4. **Confiabilidad:** idempotencia, paginación, backoff, estados inciertos, cambios de zona horaria, reinicio y token revocado.
5. **Release:** flag inicialmente apagado, migración de config no destructiva, telemetry local sin contenido sensible, plan de rollback y evidencia de Windows/Linux.

## Criterios de aceptación global

- La lectura y cada escritura tienen pruebas automatizadas y recorrido E2E de ensayo; los casos de rechazo no producen efectos.
- El preview que el usuario aprueba coincide con los argumentos ejecutados.
- No hay tokens, cuerpos de correo ni audio crudo en logs/recibos del feature.
- Las decisiones de voz se basan en corpus y comparaciones reproducibles; no se cambia el motor por popularidad o métricas textuales ajenas a la ruta acústica.
- La integración permanece apagable por capability flag y su desconexión revoca o elimina el token local.

## Restricciones de ejecución

Gate Linux Release: 105/105 targets aprobados en la corrida serial final de esta iteración. Una corrida paralela previa tuvo una falla transitoria de puerto ocupado en `test_system_profiles`, que pasó aislado y en suite serial. No se inició OAuth real, no se usó una cuenta personal, no se hicieron benchmarks nuevos ni pruebas acústicas; el gate con cuenta Google de ensayo y la validación Windows siguen pendientes.
