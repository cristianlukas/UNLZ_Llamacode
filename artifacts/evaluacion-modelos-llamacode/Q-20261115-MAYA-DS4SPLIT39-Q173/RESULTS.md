# Resultados Q209 · Maya-XS Q173 DS4_SPLIT=39,1

## Estado

Ladder Q173 completo hasta el límite aprobado de 261888, en ambas RTX 3090 (ASUS GPU0 + PNY GPU1). El punto 523904 no se ejecutó, conforme al límite indicado por el usuario.

| Contexto | n | Prefill efectivo E2E (tok/s) | Decode `tg_throughput` (tok/s) | TTFT |
|---:|---:|---:|---:|---:|
| 8192 | 3 | 393.593 ± 0.895 | 31.023 ± 1.878 | 20.890 s |
| 32768 | 1 | 540.474 | 26.058 | 60.684 s |
| 65536 | 1 | 443.236 | 4.801 | 147.926 s |
| 131072 | 1 | 603.845 | 18.513 | 217.112 s |
| 261888 | 1 | 593.171 | 17.471 | 441.555 s |

El promedio descriptivo equiponderado entre las medias de los cinco contextos es P=514.864 y D=19.573 tok/s. Es provisional: 8K tiene n=3 y cada contexto restante n=1; el decode de 64K fue marcadamente más lento. No tratarlo como velocidad global estable. La corrida previa de 64K sin solicitud ni eventos sigue `NO RESULT` y está excluida. El punto final tuvo 261,918 tokens de prompt reales, 128 de salida, readiness 20.335 s (no clasificado cold/hot).

Q172 y LHA-1 permanecen separados de Q173: Q172 88/89/91, media 89.33/100 (n=3), con fallo TC-92 en las tres semillas; LHA-1 76/100 en otra suite. No usar como validación de aislamiento multi-tenant.

## Independencia y cierre del proceso

La primera corrida 64K perdió el controlador en primer plano mientras Maya siguió vivo sin recibir solicitud. No hay evidencia que pruebe que Maya causara el cierre de Codex. Los puntos válidos de 64K, 128K y 261K se ejecutaron bajo unidades transitorias de usuario `systemd`, separadas del lanzador y de esta conversación; el worker y Maya tienen límites de tiempo y memoria, Maya sin swap. La prueba final también terminó con ambos servicios exit0. El worker continuó después de que el lanzador salió; el modelo finalizó con exit 0. El cgroup reportó OOM=0/OOMKill=0. Postflight confirmó puerto libre, ningún servidor de inferencia ni proceso compute de GPU.

El `ExecStopPost` de a02 rechazó identidad porque Maya ya se había detenido normalmente y systemd devolvió la descripción predeterminada del nombre de unidad. No quedó ningún proceso; el runner hizo su limpieza y el postflight lo confirmó. Se corrigió el hook para que unidades ausentes/inactivas/fallidas sean un no-op sin señal; para una unidad activa sigue exigiendo la descripción Q209 exacta. La prueba CPU-only `Q209-CONTROLLER-DETACHED-CPU-02` pasó: el worker sobrevivió al lanzador, alcanzó su límite, detuvo sólo el hijo ficticio exacto y una segunda limpieza con descripción no coincidente sobre el hijo ya ausente no envió señal. No usó modelo ni GPU.

La causa exacta de los cierres de la app Codex no está demostrada. No se debe volver al controlador foreground para estos benchmarks. El diseño detached evita que una terminación de esta conversación deje la inferencia corriendo sin límites; no demuestra por sí solo la causa de los cierres anteriores.

## Estado y siguiente paso

Q173 quedó completo hasta 261888; el resultado y las notas se sincronizaron y leyeron de vuelta en Google Sheets. No ejecutar 523904. El objetivo padre Q202 sigue activo: continuar la reconciliación de las pestañas de IA y elegir el siguiente accionable pendiente según sus gates. Toda inferencia prolongada debe ejecutarse como worker `systemd` detached y acotado, cuyo ciclo de vida no dependa de Codex; registrar resultado y limpiar/verificar servicios al volver a consultar estado.

## Recibos principales

- 64K a02: `profiles/maya-xs-iq1s-pny-ds4split39-q173/receipts/q209-q173-65536-a02-result.json` SHA-256 `f4792c8140e0393951f369f9ad77e892c0019e1fc7c93aab87c47c422eb9b687`.
- Preflight cacheado previo a 64K: `profiles/maya-xs-iq1s-pny-ds4split39-q173/receipts/preflight-cached-refresh.json` SHA-256 `4a9c769a8b9c46f5dc66069cb701b584a7f7e878628a7ec3abdd5682196d96f5`.
- CPU repair prereg: `profiles/maya-xs-iq1s-pny-ds4split39-q173/receipts/detached-worker-cleanup-idempotency-amendment02.json` SHA-256 `81cd21858c5fda155914a2643bc73e9b0fbe47bda7ad223e255e237180bbe1d4`.
- CPU repair result: `profiles/maya-xs-iq1s-pny-ds4split39-q173/receipts/detached-worker-cleanup-idempotency-result-amend02.json` SHA-256 `f118cf8061cee5a9067363b545820eac1fd9b5911665513cfd0510d82f3b8471`.
- Sheet result readback after cleanup amendment02: `profiles/maya-xs-iq1s-pny-ds4split39-q173/receipts/sheet-q209-cleanup-amend02-result-readback.json` SHA-256 `64a8b4d0a06214c04fdd969de28f6071afc22432e7a11acee1f25a05e98e2c99`.
- Q173 full-ladder completion amendment: `profiles/maya-xs-iq1s-pny-ds4split39-q173/receipts/q173-context-261888-completion-amendment.json` SHA-256 `f8ad77402c965d89f52a96dbed3732ea6c8e0fa9b980d5031d2253f982f1e730`.
- Q173 261888 final Sheet readback: `profiles/maya-xs-iq1s-pny-ds4split39-q173/receipts/sheet-q173-261888-complete-readback.json` SHA-256 `5939f91eb8a5ea5dc7e0ed670b3d42fbbee22a34b4adf477fbbc62d374070cb2`.

## Registro de lanzamiento Q173 131072×1 a01 (histórico)

Lanzado 2026-11-15T15:44:24+00:00 como worker user-systemd desacoplado (q209-maya-q173-pp131072-worker-a01) y servicio Maya hijo (q209-maya-q173-pp131072-a01). El lanzador terminó tras aceptar el trabajo; ambos servicios estaban activos en la instantánea. Límites: worker 3900 s/8 GiB; motor 3600 s/96 GiB, swap 0, limpieza con identidad exacta. La hoja se actualizó y leyó de vuelta antes de esperar el resultado. Estado local: receipts/worker-status-pp131072-a01-active.json SHA-256 21bb314b8eb9759d64bd9b810a8428779fa02eaa261d418a4c9fab9fd5e7a3fe.

## Q173 131072×1 a01 — PASS

Prefill efectivo E2E 603.845 tok/s; decode `tg_throughput` 18.513 tok/s; TTFT 217.112 s; salida 128 tokens; readiness 30.391 s (no cold/hot). Ambos PIDs físicos PNY+ASUS verificados. Worker y engine terminaron exit 0; postflight con puerto libre, cero servidores de inferencia/compute, MemAvailable 123142356992 B y OOMKill 0. La lectura de vuelta corregida de Sheets pasó. Promedio descriptivo, igual peso por los cuatro puntos 8K/32K/64K/128K: P495.287/D20.099; 8K n=3 y los demás n=1. 261888 se completó después; ver la sección de cierre final.

Recibos: resultado local SHA-256 82a2dbb452ed3cfbb7a5ea7ac0b41507b19953d1b199a0fc0dece79fb2dfddf1; postflight SHA-256 33cefab9443bc42a1a69068d867bb6a28223e8c12d4d146572f0062979c6bd93; Sheet corrected readback SHA-256 66dba9ab4380c6232edc535d82f1156fd8c54674c1b43f4cacfe16cef1c3a425.

## Q173 261888×1 a01 — PASS y ladder cerrado

Prefill efectivo E2E 593.171 tok/s; decode 17.471 tok/s; TTFT 441.555 s; prompt real 261,918 tokens y salida128. Readiness20.335 s no es cold/hot. Worker y engine detached terminaron exit0. Postflight: puerto libre, ningún inference server ni proceso compute GPU, OOMKill0; MemAvailable mínimo116,190,371,840 B y posterior123,915,268,096 B. Picos ASUS7,439MiB, PNY23,770MiB, temperatura máxima74°C. Resultado y métricas sincronizados/leídos de vuelta en Sheets. Recibo de completion amendment SHA-256 `f8ad77402c965d89f52a96dbed3732ea6c8e0fa9b980d5031d2253f982f1e730`; resultado SHA-256 `f5b21d5cc463e61443c3606e79747c823895581e8d48e42028506a31bbe890d1`; postflight SHA-256 `301c1572646cf5672a4f88628271074008aebf9414925bee99733ab9c09bc9e7`; cleanup SHA-256 `ccf8a55a68077e6632b8744986c51b2706c49b10ec1bf7da392fad826f7d483b`; Sheet readback SHA-256 `5939f91eb8a5ea5dc7e0ed670b3d42fbbee22a34b4adf477fbbc62d374070cb2`.

El ladder no genera un score Q172: se mantiene separado el Q172 previo de 89.33/100, que falló TC-92 en las tres semillas. La causa exacta de los cierres de Codex sigue sin demostrar; el worker detached impide que una pérdida del lanzador deje el benchmark sin límites, pero no diagnostica el cierre de la app.
