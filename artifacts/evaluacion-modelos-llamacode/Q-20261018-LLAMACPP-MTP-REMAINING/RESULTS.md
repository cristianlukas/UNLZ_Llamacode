# Resultados — Q-20261018-LLAMACPP-MTP-REMAINING

**Estado:** bloqueada antes de inferencia. No se inició ningún benchmark ni se
cargó un modelo. No hubo cambios de producción, harness, perfiles, swap o GPU.

## Estado de las pruebas previas

- Q-20261010: Hard Mode 28×3 y probe corto de velocidad completados; HE0/HE20
  válidos en ambos brazos; BCB8 MTP-on 3/8 final; BCB8 MTP-off se canceló a
  2/8 y quedó incompleto; TaskFlow no se ejecutó.
- Q-20261017 FOLLOWUP: BCB8 MTP-off se canceló por la guarda de swap antes de
  puntuar; TaskFlow no se inició.
- Q-20261017 RESUME: BCB8 MTP-off quedó incompleto en 4/8; TaskFlow MTP-off
  quedó incompleto en 3/10; TaskFlow MTP-on finalizó 0/13 tras tres
  reparaciones. No hay comparación completa por brazos.

Por lo tanto, **no se habían completado todas las pruebas de coding/agentes**.
Los intentos sí se ejecutaron; los casos parciales no son scores finales y el
0/13 de TaskFlow MTP-on sí es un fallo válido de calidad. No se deben repetir
las huellas anteriores sin corregir primero el flujo de escritura al workspace
y la deriva de búsquedas externas.

## Por qué las tareas no arrancan

`WORK_QUEUE.md` describe una cola de coordinación manual, no un despachador. Al
preflight había 102 filas históricas: 97 `Completa`, 5 `Bloqueada`, y ninguna
`Pendiente` o `Activa`. Por tanto, no hay una tarea de repo pendiente que el
sistema vaya a iniciar automáticamente.

El runner LlamaCode de los benchmarks también usa un único slot (`parallel=1`)
y avanza al siguiente prompt sólo después de `turnFinished` y el cooldown. Una
generación larga o una reparación que no termina ocupa ese slot. Véase el
análisis de las corridas en
[`Q-20261017-LLAMACPP-MTP-CODING-RESUME`](../Q-20261017-LLAMACPP-MTP-CODING-RESUME/RESULTS.md)
y `src/AppController.cpp` alrededor de las líneas 21724, 22813 y 22929.

## Preflight de esta continuación

El host tenía 116 GiB disponibles, swap sin uso y PSI de memoria en 0; `oom_kill`
era 0. Sin embargo, las dos RTX 3090 tenían procesos `llama-server` activos del
servicio PeritoSoft: PID 8459 en `127.0.0.1:8033` y PID 15451 en
`127.0.0.1:8081`. `nvidia-smi` informó 6413/7148 MiB ocupados y 0/20% de
utilización. Son procesos ajenos a esta tarea; no se detuvieron ni se envió
ninguna solicitud a sus APIs. El preflight y los procesos observados están en
[preflight.json](receipts/preflight.json).

No se corrieron tests de C++/QML: esta continuación no cambió código. Tampoco
se repitieron inferencias con las huellas históricas.

## Reanudación

Reanudar cuando ambas GPUs estén libres y se haya fijado una estrategia de
workspace que no permita búsquedas fuera del directorio de tarea. Si se requiere
detener los dos servidores PeritoSoft antes de que terminen, esperar
autorización explícita del usuario. No promover MTP: los resultados históricos
siguen fuera del límite de duración definido por el usuario y falta una
comparación completa de coding/agentes.
