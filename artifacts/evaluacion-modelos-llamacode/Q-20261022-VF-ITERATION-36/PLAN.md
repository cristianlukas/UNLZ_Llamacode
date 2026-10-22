# Q36 — Contención dura de procesos de evaluación · 2026-10-22

**Estado:** preregistrado; sólo hardening del runner y una prueba de OOM controlada. Sin servidor de inferencia, pesos ni GPU.

## Hallazgo que motiva el cambio

Q35 probó que mover Strata a `background.slice` separa los cgroups, pero el worker quedó sin límite (`MemoryMax=infinity`) y con `OOMPolicy=stop`. El 22/10 a las 10:39:27 local el guard lo detuvo con PSI del user-manager de 54,52%; 16 segundos después, systemd registró un proceso eliminado por OOM dentro de `app.slice`. El PID principal de ChatGPT siguió vivo y el log no identifica al proceso hijo eliminado; por eso Q35 no demuestra que la mitigación fuera completa. La evidencia anterior del cierre de 10:17 sí confirma que un Strata lanzado dentro del turno compartía el scope de Codex y `systemd-oomd` terminó ese scope.

En el chequeo actual: RAM física 129.5 GB; `app.slice` informa 111.8 GB cargados, de ellos 105.3 GB en caché de archivos, con `MemoryMax=infinity`. MemAvailable 118.9 GB y PSI avg10 sin presión sostenida. La métrica cgroup contiene páginas de caché compartida y no equivale a RSS residente de una sola app.

## Cambio preregistrado

1. Calcular para cada worker un límite cgroup de memoria sin alterar modelo, cuantización, contexto, perfil, pesos ni asignación de GPU: máximo `min(104 GiB, MemTotal − 16 GiB, MemAvailable − 16 GiB)`. Si no quedan al menos 64 GiB, bloquear antes de cargar el modelo.
2. Configurar `MemoryHigh = MemoryMax − 8 GiB`, `MemoryMax` al presupuesto calculado, `MemorySwapMax = min(4 GiB, SwapFree − 1 GiB)`, `OOMScoreAdjust=900`, `OOMPolicy=kill` y `KillMode=control-group`. Hacer al worker candidato de `systemd-oomd` con un límite propio de PSI del 35%. Verificar los valores efectivos desde el cgroup del proceso antes de admitir una solicitud.
3. Detener el worker al 35% sostenido de PSI del user-manager (5 muestras de 1 s), bastante antes del umbral host configurado. Conservar recibos/progreso fuera de la unidad. Estos límites aíslan la consecuencia; no reducen la memoria solicitada por el modelo. Si el worker supera el presupuesto, la corrida se clasifica como infraestructura y no se repite automáticamente.
4. Regresión CPU-only: ejecutar un proceso desechable que intenta reservar/tocar 512 MiB dentro de una unidad transitoria con `MemoryMax=128M`, `MemoryHigh=64M`, `MemorySwapMax=0`, `OOMPolicy=kill`, `OOMScoreAdjust=900`. Aceptar sólo si el cgroup registra OOM local, toda la unidad se detiene, el proceso padre/Codex permanece vivo y el recibo/journal quedan disponibles.

## Límites y criterios

- No arrancar Flash-Next ni otro inference server en esta iteración; no hay inferencia ni resultados de calidad.
- Si systemd no aplica el límite, si el worker no queda en cgroup propio o si el test controlado no provoca un OOM local contenido, detener y no reanudar Q35.
- Un resultado satisfactorio prueba la contención del runner frente a un OOM cgroup inducido; no garantiza inmunidad ante una falla independiente del kernel, driver o sistema.
- Mantener los datos y pesos de Qwen Flash-Next ASTRA/SOL, perfiles productivos, PeritoSoft y resultados previos intactos.

## Enmiendas de ejecución y resultado

- El intento 1 con `MemoryHigh=64M` se atascó por throttling antes de forzar el OOM; se detuvo únicamente su propia unidad. Intento 2 preregistró `MemoryHigh=120M` para permitir llegar a `MemoryMax=128M`.
- Tras el intento 2, se corrigió el recolector: systemd puede retirar el directorio cgroup al cerrar la unidad. El worker ahora persiste los límites efectivos antes de asignar memoria y el recolector lee el resultado/journal retenidos.
- El intento 3 mostró que `MemoryPeak` puede ser inconsistente después de retirar el cgroup. Antes del intento 4 se quitó esa métrica del gate de seguridad; se conserva como dato diagnóstico.
- Intento 4 pasó el gate: OOM local, grupo entero eliminado y PID del controlador/ChatGPT/Codex app-server iguales antes y después. Ver `receipts/systemd-oom-containment.json` y `RESULTS.md`.
- La prueba verifica contención de este worker sintético; no habilita aún reanudar Q35 ni certifica otros runners.
