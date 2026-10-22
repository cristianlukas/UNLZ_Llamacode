# Q41 · Contención de launchers de evaluación Linux · resultados

Fecha: 2026-10-22. Lock: `Q-20261022-VF-ITERATION-41` (token `a5758823-c599-48e3-afe5-d34381057eed`).

## Decisión

El camino Linux nativo de `tools/kv_cache_ab.py` lanza ahora servidores dentro de un scope del system manager bajo `background.slice`. `tools/long_context_matrix.py` y `tools/context_tps_matrix.py` reutilizan `start_server`, por lo que también quedan cubiertos. El scope tiene `OOMPolicy=kill`, `KillMode=control-group`, `ManagedOOMMemoryPressure=kill` y `ManagedOOMSwap=kill`; el wrapper ejecuta el árbol con `oom_score_adj=900`, heredado por los hijos. No se fija `MemoryHigh`, `MemoryMax` ni `MemorySwapMax`: el servidor conserva la memoria y swap que necesite. El cierre detiene el scope completo y luego recoge el proceso cliente.

La protección aborda el modo de cierre por presión/OOM que motivó Q37. Es evidencia de contención del runner en Linux; no demuestra que la app sea inmune a fallos no relacionados con OOM. El P0 global sigue abierto: `scripts/run-astra-strata.sh` y los lanzadores PowerShell aún no están integrados ni validados desde esta sesión Linux. `tools/meter_system_profiles.py` contiene rutas `D:/` y `.exe` y no se modificó.

## Evidencia y pruebas

- C41-01: los dos intentos iniciales de scope (`--pipe` y `Type=exec`) fueron rechazados antes de ejecutar hijos; el servicio transitorio de system-manager conservó stdout y exit code. Recibos `c41-01-attempt-01-rejection.json`, `c41-01-attempt-02-rejection.json`, `c41-01-canary-result.json`.
- C41-02: OOM sintético de servicio 512/128 MiB contenido; descendientes terminados y controlador vivo. `c41-02-oom-containment.json`.
- C41-03: scope corto preservó stdout, código 23, entorno, cwd, UID/GID y límites bajo `background.slice`. `c41-03-scope-semantics.json`.
- C41-04: attempt 04 confirmó `memory.events` mientras el cgroup existía (`oom=1`, `oom_kill=3`, `oom_group_kill=1`), `Result=oom-kill`, journal por unidad, descendientes muertos y controlador vivo. Attempts anteriores/con error están preservados; attempt 03 no se usa para atribuir el contador porque su recibo no etiquetaba si la lectura ocurrió antes o después del cierre del cgroup. `c41-04-attempt-04-scope-oom-containment.json`.
- C41-05 lifecycle: proceso corto preservó stdout y exit 23; largo verificó score 900 en padre/hijo, mismo cgroup de `background.slice`, política OOM, candidaturas de oomd, ausencia de caps de memoria/swap y stop del árbol. `c41-05-scope-lifecycle.json`.
- Integración `start_server`: canario CPU-only verificó log, marcador, score, `ManagedOOM*=kill`, caps en `infinity`, stop del árbol y unidad inactiva. `c41-05-kv-cache-integration.json`.
- `long_context_matrix.py --dry-run`: generó comandos para 8K/16K con modelo de ruta ficticia; no inició servidor. `c41-05-long-context-dry-run.json`.
- Regresiones Python finales: `PYTHONPATH=. python3 tests/test_kv_cache_ab.py` 11/11 y `python3 .../test_scope_oom_probe.py` 3/3; `py_compile` pasó en los módulos modificados. El lifecycle final pasó sus 13 checks y la integración `start_server` sus 10 checks. `long_context_matrix.py --dry-run` imprimió los comandos de 8K/16K sin iniciar servidor. Recibo agregado `receipts/c41-05-validation-summary.json`.

Los controladores de canary tuvieron fallos de harness durante el desarrollo (imports, formato bytes/texto y una firma no expuesta); quedaron registrados por intento. Se corrigieron y las ejecuciones finales pasaron. No se cargó modelo, no se ejecutó benchmark de inferencia, no se usó GPU y no se mató ningún proceso ajeno. `systemd-oomd` estaba activo; no se provocó presión global artificial.

## Alcance y seguimiento

Esta integración requiere systemd, `systemd-oomd.service` activo y `sudo -n` configurado para `systemd-run`/`systemctl`; el helper comprueba el servicio antes de lanzar y falla cerrado si no está disponible. La marca de oomd vuelve al árbol candidato ante presión, pero no se ha forzado una acción de oomd para probarla. `oom_score_adj` sólo influye en la selección del OOM del kernel y no es una garantía absoluta.

Siguiente: cubrir `run-astra-strata.sh` si se decide mantenerlo como launcher de evaluación, y añadir Job Objects en Windows para los scripts `Start-Process`; después reabrir pruebas model-backed sólo en el runner/plataforma compatible. Q39 C39-02 Flash-Next sigue pendiente de Windows nativo; esta sesión sigue en Ubuntu.


## Cierre operativo

En el postflight no quedaron procesos de inferencia ni scopes `llamacode-eval-*` activos. El OOMD recibió scopes transitorios sólo durante las canarias y todos terminaron limpios. No se tocó la configuración global del host ni la memoria de los perfiles.
