# Q115 · Límites exactos de aviso PSI moderada

## Pregunta

¿Los dos caminos de warning global activos en Q97 usan límites inclusivos exactos y esperan 30 muestras consecutivas?

## Preregistro Q115-A1

- CPU-only replay de `check_gates` real; `gpu_snapshot` fixture de dos RTX 3090, sin NVML.
- Probar `full=20.00%` y `some=70.00%` durante 30 samples: warning en 30, nunca antes.
- Probar justo por debajo (`full=19.99%`, `some=69.99%`) durante 30 samples: sin warning.
- Asegurar que no se active stop severo en ninguna condición.
- Sin modelo/servidor/inferencia/GPU/red/build/RAM artificial ni cambios a policy.
- Detener ante hash/lock distinto.
