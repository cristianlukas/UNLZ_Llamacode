# Q114 · PSI del cgroup alta frente a PSI global moderada

## Pregunta

¿El guard activo Q97/Q100 trata la PSI alta del cgroup como señal diagnóstica y deja que las decisiones de aviso/parada dependan de MemAvailable, PSI global y OOM? Este borde importa porque Q97 registró pico cgroup 81.53% y pico PSI global 34.72% mientras ASTRA completó. Los picos históricos no se asumen simultáneos.

## Preregistro Q114-A1

- Replay CPU de `q97.check_gates`/`record_sample`, sin modificar el código activo; dos RTX 3090 representadas por `gpu_snapshot` fixture, sin consultar NVML.
- MemAvailable 71.864 GiB, OOM sin incremento, PSI global full/some moderada 34.72%; cgroup PSI full/some 81.53% sólo diagnóstica. Comprobar continúa y la fila conserva la lectura cgroup.
- Mantener las señales por 30 muestras: warning global moderado en sample 30 y no hard-stop; cgroup PSI no produce stop independiente.
- Sin modelo/servidor/inferencia/GPU/red/build/descarga, sin RAM artificial ni cambios de política.
- Lock y SHA del Q97/Q100/review deben coincidir con el manifiesto antes de invocar escenarios.

Enmienda 01: la primera corrida pasó 2/2, pero el caso cgroup-only sólo cubría una muestra. La cobertura se amplió a 30 muestras con PSI global=0 para discriminar de forma directa un posible warning cgroup a la cadencia real.
