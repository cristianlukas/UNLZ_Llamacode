# Q110 · Revalidación del detector de presión de memoria

**Estado:** Activa bajo lock exclusivo.  
**Lock:** `Q-20261024-VF-ITERATION-110`, token `549f3a3b-673a-4d3a-9046-1122a67c04a2`.  
**Preregistro:** 2026-10-25 00:04:21 UTC.

## Pregunta

¿El guard candidato interpreta correctamente la evidencia que señaló el usuario: ASTRA DEFAULT/Flash-Next a 1M y SOL TP=2 finalizaron con mucha memoria de proceso/host sin crash? ¿Separa RSS alto y PSI moderada de las condiciones reales de corte?

## Pruebas preregistradas

1. Verificar con una regresión CPU-only focal de Q110 sobre el core Q108 inmutable: ASTRA 1M con 51,14 GiB RSS y 55,728 GiB disponibles → continuar; SOL Q34 TP=2 completo y sin OOM, sin inferir PSI no medida; Q100/Q97 PSI moderada → avisar/continuar; MemAvailable <32 GiB, aumento OOM y PSI severa sostenida 15 muestras → detener; telemetría ausente/malformada → fail-closed y sólo PID candidato.
2. Leer una muestra real de `/proc` con el core Q108 y guardar MemAvailable, PSI some/full, OOM, decisión y hora. No lanzar candidato ni señalizar procesos.
3. Detectar servidores de inferencia y compute apps con lectura de `/proc`, sockets y `nvidia-smi`; no detener procesos. La GUI/ArtCraft no cuenta como servidor de inferencia.

## Límites

CPU/read-only únicamente: sin modelo, servidor, benchmark de inferencia, asignación artificial de RAM, build, GPU, límite de memoria/swap, sysctl, cgroup o cambio de perfil. Repetir los 56 GiB de Q103 no es necesario: no cambia el umbral y el recibo existente ya cubre ese control.

El helper Q108 es candidato para lanzadores de evaluaciones; no está integrado como monitor general de Codex/GUI/driver ni como límite de ASTRA/SOL. Mantener ASTRA Flash-Next, SOL, los pesos productivos y PeritoSoft intactos.

## Ajuste de ejecución documentado

Al inspeccionar `test_q108_guard_audit.py` antes de ejecutarlo, encontré que su test final exige que el lock siga perteneciendo a Q108 y que otra comprobación lee un accionable externo. No corresponde ejecutar esa suite completa bajo Q110 ni eludir su ownership. Se preparó el runner focal `runner/q110_detector_recheck.py` sobre el mismo core sin modificar, con nueve comprobaciones relevantes. La descripción de la fila Sheet inicialmente decía “15 regresiones Q108”; esa descripción se corrige para reflejar el runner Q110 real. La corrección documental se registra después de la ejecución, sin alterar el resultado ya obtenido.

## Enmienda 01 · cadencia del aviso moderado

La comparación estática encontró una diferencia de política: Q97 exigía 30 muestras consecutivas de un segundo para emitir el aviso moderado; `q108_guard_core.evaluate_sample` devuelve `warning=True` desde la primera muestra que cruza el umbral. Esto no modifica sus hard stops, pero no reproduce la cadencia calibrada y podría generar avisos prematuros/repetidos. Antes de otro test, se preregistra un wrapper candidato Q110 separado que conserva el core de hard stops y aplica la persistencia de 30 muestras.

Prueba CPU-only nueva: validar warning ausente en muestras 1–29, presente en la 30, reset tras recuperación, hard stop severo aún a la muestra 15, y control ASTRA alto-RSS sin PSI sin aviso. No tocar Q108, no integrar el wrapper a producción, no iniciar inferencia/GPU ni alocar RAM. El objetivo es cerrar el contrato del próximo launcher, no cambiar umbrales ni limitar modelos.

## Elegibilidad para continuar la cola de modelos

No lanzar un benchmark de modelo salvo que cambie un gate registrado. En este executor Linux, C39-02/Job Objects siguen requiriendo Windows nativo; otros candidatos esperan runtime/fixture/artefacto primario concreto. Registrar esos bloqueos; no sustituirlos por una prueba incompatible.
