# Q111 · Verificar guard activo y reconciliar cadencia PSI

## Objetivo

Comprobar la implementación que realmente usaron las corridas dual-3090 (Q97 y Q100): PSI moderada advierte sólo tras 30 muestras de 1 s, la recuperación reinicia el contador, y la parada severa conserva 15 muestras. Delimitar el core candidato Q108/Q110 frente a esos launchers. Esta prueba no inicia modelo, servidor, build ni GPU y no cambia umbrales/producto.

## Preregistro Q111-A1

- Lock: `Q-20261024-VF-ITERATION-111`, token verificado en `WORK_QUEUE.lock`.
- Ejecución: CPU-only; `runner/test_q111_memory_guard_integration.py`.
- Controles: PSI `full=20%` (warning sólo en muestra 30); recuperación (reset); PSI `full=60%` y `some=80%` (no-stop en 14, stop en 15); importación/delegación Q100→Q97; frontera candidate-only Q108/Q110.
- Criterio: todas las expectativas pasan y hashes de los launchers/core coinciden con este preregistro; de lo contrario detener y no iniciar inferencia.
- Prohibido en esta iteración: inferencia, descarga, build, GPU, RAM artificial, cambios a perfiles/pesos, señales a procesos.
- Próximo paso si pasa: reconciliar documentación/inbox/accionable y reanudar sólo la siguiente prueba con gate externo ya satisfecho.

## Cierre

Q111-A1 terminó 8/8 PASS a 2026-10-25T00:18:54Z; preflight sin servidor de inferencia. La cadencia observada es la del guard Q97/Q100; Q108/Q110 conserva estatus candidate-only. No quedan pruebas de modelo habilitadas por esta auditoría; los pendientes tienen gates externos o necesitan un fixture construido y validado en la próxima iteración.
