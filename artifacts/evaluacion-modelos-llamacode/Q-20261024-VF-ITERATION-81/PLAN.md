# Q81 — Corrección del timeout de reparación y reanudación TaskFlow

## Objetivo

Corregir el timeout duro de `runBenchmarkAgentPass` para que un único límite de pared desde el inicio incluya todos los turnos de reparación. Cubrir en CPU la decisión de mantenerlo armado durante un retry y de detenerlo en la salida terminal. Corregir el runner aislado para que alcance `cancelBenchmark` al vencer max-wait y confirme limpieza con una gracia limitada. Luego repetir únicamente TaskFlow ULTRA MTP-off y MTP-on, en ese orden y con el mismo setup fijado en Q79, si todos los gates locales y externos pasan.

## Evidencia de partida

Q80 localizó la causa en `src/AppController.cpp`: `finalize()` detenía y eliminaba `hardTimeoutWatchdog` antes de decidir si iniciar otra reparación; la rama de repair reiniciaba `finished` pero no rearmaba ese timer. En los registros Q79 no aparece `benchmark_timeout`; el runner vencido anotaba max-wait pero salía sin cancelar automáticamente. Q79 canceló por API y se cerró su servicio aislado. Ver recibos fuente Q80 y logs Q79.

## Cambios previstos

1. Separar cleanup terminal de la rama que reencola una reparación; el watchdog conserva el inicio original y el tiempo restante durante retries, y no se extiende el plazo.
2. Añadir una función pura de política usada por producción y una regresión Qt/C++ que demuestre que un retry mantiene el deadline, pero una finalización terminal lo detiene.
3. Copiar el runner TaskFlow a este artefacto Q81; al alcanzar `max-wait=1860s`, enviar `cancelBenchmark`, comprobar `benchmarkRunning=false` durante una gracia finita y limpiar sólo procesos de la instancia Q81. Nunca terminar Codex, escritorio, GUI, ArtCraft, modelos ni perfiles compartidos.
4. Documentar la semántica del límite único en README/runbook.
5. Ejecutar `./scripts/build-linux.sh Debug` y `./scripts/tests-linux.sh Release`; guardar logs, códigos de salida y hash del binario Debug.
6. Sólo con build/tests aprobados, preregistro y Sheets sincronizados/readback, hacer preflight fresco y ejecutar los dos brazos TaskFlow uno por uno; detener/recolectar la instancia entre brazos. MTP-off precede MTP-on.

## Diseño de comparación

- Modelo: Qwen3.8-Flash-Next Q4 fijado en los artefactos Q79, nunca ASTRA/SOL productivo.
- Suite: TaskFlow ULTRA (`qwen38_taskflow_ultra_ast_vs_sol_20261006`), SHA-256 `f04febb440208d5bf74c01e84d78f5127e57c164fabece2acbfb346215dc0c17`.
- Perfil off: `q4-mtp-off-taskflow-20261013`; perfil on: `q4-mtp-on-taskflow-20261013`, verificando cada fingerprint contra el recibo Q79 antes de cargar.
- Orden: MTP-off → cleanup/readback → nuevo preflight → MTP-on.
- Timeout de inferencia por brazo: 1800 s; margen de finalización sin inferencia: 60 s; max-wait 1860 s; gracia limitada tras cancelación, con stop controlado sólo de la instancia Q81 si la app no finaliza.
- No correr BCB8 de nuevo en Q81. No cambiar perfiles, sampling, runtime, sidecar, suite, launcher, modelo, producción, defaults o memoria/swap.

## Gates y límites

- Lock Q81 debe seguir siendo el propietario.
- Antes de compilar: comprobar cambios preexistentes y editar sólo archivos del alcance, sin staging/reversión ajena.
- Antes de GPU: build Debug y suite Release terminan con exit 0; Sheet readback exacto; rehash de suite/perfiles/modelos/runtime; sin inference server externo ni PeritoSoft. Si se encuentra PeritoSoft, detener sólo su server/app conforme a autorización expresa. La GUI activa no bloquea.
- MemAvailable ≥ 40 GiB, SwapFree ≥ 1 GiB, OOM estable, puertos libres, temperaturas/telemetría de GPUs registradas. No exigir GPU o memoria libres por conteo de procesos compute; detectar inferencia por procesos/command line y listeners.
- Un timeout, cancelación, diferencia de fingerprint, OOM, server externo, service cleanup fallido o regresión incompleta deja ese brazo como incompleto sin score.
- Un único par no establece superioridad general ni adopción. Q79 y Q81 son evidencia candidate-only; preservamos ASTRA/SOL productivo.

## Criterios de éxito

- El watchdog de pared sigue activo durante reparaciones y vence una sola vez en el deadline original; la regresión CPU verifica retry/terminal.
- Runner emite cancelación en max-wait y termina con app/servidor Q81 apagados y puertos propios libres.
- Build Debug y tests Linux Release pasan.
- Si se ejecutan ambos brazos, cada uno tiene fingerprint, logs, coverage, score válido sólo con suite completa, timings y postflight; si no se cumplen gates, no se carga el modelo y se registra una condición concreta.
