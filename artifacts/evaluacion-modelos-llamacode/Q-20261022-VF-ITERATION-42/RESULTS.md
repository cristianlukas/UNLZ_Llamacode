# Q42 · Resultados

## Resultado

`scripts/run-astra-strata.sh` ahora delega el proceso Linux al helper de scope
Q41. El proceso falso quedó bajo `background.slice`, con `OOMPolicy=kill`,
`KillMode=control-group`, `ManagedOOMMemoryPressure=kill`,
`ManagedOOMSwap=kill`, `oom_score_adj=900` heredado y
`MemoryHigh/MemoryMax/MemorySwapMax=infinity`. No se limitaron recursos del
modelo. SIGINT/SIGTERM se registra en el handler y la parada del scope ocurre en
el loop principal, fuera del handler; esta forma pasó el canario SIGTERM.

No se ejecutó Strata real, inferencia, benchmark ni GPU. Windows permanece fuera
del cambio.

## Canarios

- Intento 01: rechazado antes de iniciar el falso servidor porque el checkout
  NTFS está montado `noexec`; receipt `receipts/c42-linux-launcher-scope-probe.json`.
- Intento 02: caso de salida natural pasó (rc 23, argv/cwd, scope y cleanup),
  pero SIGTERM agotó 15 s; sin procesos propios al postflight.
- Intento 03: mismo problema SIGTERM; el probe terminó su propio launcher por
  timeout y detuvo sólo el scope exacto; sin procesos propios al postflight.
- Intento 04: salida rc 23 y SIGTERM rc 143 pasaron; proceso hijo ausente y scope
  inactivo; propiedades OOM y límites infinitos leídos de vuelta.
- Intento 05: ambos casos volvieron a pasar, incluyendo
  `Q42_CANARY_ENV=q42-preserved`; stdout, argv, cwd, rc 23/143, cgroup y score
  confirmados. Receipt `receipts/c42-linux-launcher-scope-probe-attempt-05.json`.

## Validación

- `PYTHONPATH=. python3 tests/test_linux_eval_scope.py`: 4/4.
- Cross-regression rerun: `tests/test_kv_cache_ab.py` 11/11 and Q41 scope parser
  3/3; 18/18 across the three Python regression suites.
- `python3 -m py_compile` para helper, regresiones y probe: pasó.
- `bash -n scripts/run-astra-strata.sh`: pasó.
- Postflight: `systemd-oomd.service` activo; ningún scope `llamacode-eval-*`,
  fake server o listener en 18342/18343. ArtCraft y el resto de procesos de GUI
  quedaron intactos.

## Alcance pendiente

Q42 cubre el launcher Linux manual de ASTRA/Strata. No cierra el P0 global:
faltan los launchers PowerShell con Job Objects y su validación Windows nativa.
Q39 C39-02 Flash-Next sigue pendiente en Windows; este commit no contiene TPS ni
resultados de calidad de modelo.
