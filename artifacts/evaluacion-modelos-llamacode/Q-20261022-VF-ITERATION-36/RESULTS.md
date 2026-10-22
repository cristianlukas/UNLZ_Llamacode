# Q36 — contención de OOM del worker · 2026-10-22

## Conclusión

Se corrigió el aislamiento incompleto detectado después de Q35. La prueba sintética en un servicio efímero confirmó que un worker con `MemoryMax=128 MiB`, `OOMPolicy=kill` y `KillMode=control-group` recibe el OOM dentro de su unidad, termina también al hijo y conserva vivos el proceso que ejecuta el test, ChatGPT y Codex app-server. No se redujeron los pesos, el contexto, la cuantización ni el perfil. No se usó GPU ni se lanzó un inference server.

Esto prueba el comportamiento de la unidad bajo un OOM controlado; no garantiza inmunidad a OOM de otros cgroups o fallas del kernel/driver. El siguiente trabajo de seguridad es auditar otros runners que aún puedan iniciar modelos desde el scope del escritorio y migrarlos al mismo patrón. Q35 sigue bloqueada hasta que el guard PSI pase el preflight; no se reanudó inferencia.

## Evidencia de la prueba

- Regresión final: `receipts/systemd-oom-containment.json`, unidad `llamacode-q36-cgroup-oom-2862255-6ecdb1.service`, tiempo `2026-10-22T14:00:02.997Z`.
- El worker persistió antes de la asignación: `memory.high=125829120`, `memory.max=134217728`, `memory.swap.max=0`, `memory.oom.group=1`, `oom_score_adj=900`, bajo `background.slice`.
- systemd: `Result=oom-kill`, `MemoryMax=134217728`, `OOMPolicy=kill`, `OOMScoreAdjust=900`; journal: worker terminado por OOM y su hijo eliminado por `SIGKILL`.
- PID de ChatGPT `2778277` y Codex app-server `2829386` fueron iguales antes y después; el controlador siguió vivo.
- `MemoryPeak` se conserva como diagnóstico, pero no forma parte del criterio: una lectura intermedia devolvió un valor no compatible con el evento OOM después de que systemd retirara el cgroup. El resultado final sí reflejó el límite. Los recibos de las corridas intermedias documentan ese problema de instrumentación.

## Iteraciones y validación

1. Intento 1 con `MemoryHigh=64 MiB`: el límite ralentizó tanto la asignación que el controlador llegó al timeout. Se detuvo sólo esa unidad.
2. Intento 2 con `MemoryHigh=120 MiB`: systemd confirmó el OOM local y limpieza del grupo, pero el recolector falló al asumir que el cgroup seguía existiendo después de la salida. Ver `receipts/attempt-02-result.json`.
3. Intento 3 guardó la configuración efectiva antes de asignar memoria y leyó el journal/propiedades retenidas después de la salida. Pasaron las aserciones de seguridad; se retiró `MemoryPeak` del criterio por ser telemetría no fiable en este estado. Ver `receipts/attempt-03-result.json`.
4. Intento 4, preregistrado antes de correr, pasó todos los criterios de seguridad. Ver `receipts/attempt-04-preregistration.json` y `receipts/systemd-oom-containment.json`.

Validaciones estáticas: `py_compile` pasó para los scripts Q35/Q36; las regresiones del guard PSI pasaron 10/10; `bash -n` pasó para el supervisor. No se tocaron C++/QML, así que no correspondía build ni suite Windows.

## Acción siguiente

Antes de cualquier inferencia Q35: revisar el estado PSI y que el runner rechace el inicio si no puede aplicar límites cgroup finitos y `OOMPolicy=kill`. Si el PSI del user-manager sigue sobre 35% durante cinco muestras, dejar la corrida bloqueada. Extender este patrón a otros runners antes de decir que todas las evaluaciones están aisladas.

Fuentes técnicas primarias: [systemd.resource-control](https://freedesktop.org/software/systemd/man/latest/systemd.resource-control.html), [systemd.service](https://www.freedesktop.org/software/systemd/man/262/systemd.service.html) y [systemd-oomd](https://www.freedesktop.org/software/systemd/man/251/systemd-oomd.service.html).
