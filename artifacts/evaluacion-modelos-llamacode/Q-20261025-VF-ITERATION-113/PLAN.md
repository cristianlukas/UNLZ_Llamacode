# Q113 · Replay de los gates completos del detector activo

## Pregunta

¿La ruta que de verdad supervisó ASTRA/SOL detiene por RSS alto, o sólo por señales de presión registradas? ¿Los gates MemAvailable, PSI global y contadores OOM tienen los límites esperados?

## Preregistro Q113-A1

- CPU-only; invoca `check_gates`/`record_sample` reales de Q97 mediante fixtures de señales. Se mockea `gpu_snapshot` para que el test no consulte GPU.
- Reproducir el control ASTRA 1M con RSS histórico como metadato y MemAvailable 55,728 GiB; la política no debe usar RSS como entrada.
- Reproducir Q100 PSI full moderada 46,52% / MemAvailable 69,386 GiB: warning sostenido y continúa.
- Verificar frontera estricta de MemAvailable (32 GiB continúa; 31,99 detiene); OOM global y cgroup; PSI severa full 60%/some 80% a 15 muestras; recovery resetea.
- SOL TP=2 queda sólo como control histórico de no-OOM, ya que no tiene serie PSI continua.
- Sin servidor/modelo/inferencia/GPU/red/build, sin señales a procesos, sin asignación grande de RAM y sin cambios de thresholds/perfiles.
- Parar ante hashes de fuentes cambiados o mismatch de lock.
