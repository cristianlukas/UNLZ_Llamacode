# Q194 — reanudación de Q193

## Estado: pausado por pedido del usuario (2026-11-02T12:18:08Z)

No quedan pruebas ejecutándose. El servidor del smoke Q194 está detenido; puerto 18503 libre; no hay procesos CUDA compute. La GUI de LlamaCode quedó intacta. El lock Q194 se liberará al terminar de escribir este punto de pausa.

## Qué se hizo

- Preflight fresco aprobó: sin servidores de inferencia ni CUDA compute, puerto 18503 libre, cuarentena de memoria ASUS 1636/1636, P2P bidireccional, `gpu_unlock` activo en ambas RTX 3090 y cero fallos nuevos de kernel durante Q194.
- Dos intentos del wrapper se frenaron antes de arrancar por errores del parser P2P; no enviaron requests. Se corrigió el parser y el preflight volvió a pasar.
- NInfer-3090 v0.17.1 Linux cargó los pesos existentes Q190 (SHA `3e33297645dc33557751be1c407a74ed7c00f34909b5d4e8cfdce91b3dbe84`) con `--devices 0,1`. PID 545712 apareció en GPU0 (11,756 MiB) y GPU1 (10,258 MiB); el engine indicó dos devices y `engine ready` en 21.7 s.
- El único request smoke devolvió HTTP 200 en 108 ms, pero el texto visible quedó vacío: `max_tokens=16` se consumieron por completo en reasoning, `finish_reason=length`. El gate de respuesta válida falló. Los 375.8/355.6 tok/s son únicamente diagnóstico de ese request y no benchmark.
- Se detuvo solo el servidor propio. Postflight limpio: sin proceso/listener/compute, VRAM 938/111 MiB y cero faults nuevos.
- Las hojas Google `Modelos locales por peso` (fila 33) y `Accionables` (fila 60) documentan el smoke fallido, el punto de pausa y el reintento condicionado. Ambos readbacks confirmaron Arial 10 y WRAP. Las métricas D:F/Z siguen siendo únicamente Q190; no se atribuyeron resultados Q194.

## Trabajo pendiente

Q173 y Q172 no empezaron. Sigue preregistrado un único reintento del smoke 8K con `max_tokens=128`, mismas opciones, prompt y temperatura; debe producir `PONG` visible, HTTP 200, `finish_reason=stop` y evidencia de uso de ambas GPUs. Si pasa, el siguiente plan es Q173 a 261888 (sin 523K) y luego Q172 Tool-Eval 2.8.0 con seeds 42/43/44, en serie. No heredar Q190 como resultado de este runtime.

Al reanudar: reclamar lock exclusivo; releer AGENTS/README/WORK_QUEUE; verificar hash de modelo/runtime, servidores, P2P, unlock, helper/quarantine, faults de kernel, memoria y discos (raíz >= 2 GB); mantener temporales y logs en D; actualizar ambas pestañas del Sheet después de cada prueba.

Los archivos de pesos y los resultados históricos Q190/Q193 permanecen intactos. Detalle reproducible: `receipts/pause-point-20261102.json` y `receipts/sheet-sync-actionable-pause-20261102.json`.
