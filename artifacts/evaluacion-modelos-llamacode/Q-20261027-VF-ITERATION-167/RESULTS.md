# Q167 · Resultados HyperQwen frente a SOL

**Decisión:** no-go para el perfil HyperQwen probado; no ejecutar más semillas en Q167.

## Resultado del screen

| Perfil | Transporte | Aprobadas | Sin respuesta final | Fallos de sandbox | Mediana E2E total | Prefill proxy | Decode proxy |
|---|---:|---:|---:|---:|---:|---:|---:|
| HyperQwen Qwen3.8-27B W4A16 + DFlash2, TP=2 | 8/8 | 0/8 | 7/8 | 0 | 155.52 s | 1273.33 tok/s | 39.55 tok/s |
| SOL Qwen3.8-27B AutoRound INT4/W4A8 + MTP4, TP=2 | 8/8 | 0/8 | 0/8 | 0 | 11.32 s | 1316.11 tok/s | 113.50 tok/s |

Los valores prefill/decode son proxies medidos por el cliente, no velocidad nativa de kernel. El gate preregistrado exigía cero respuestas finales vacías y al menos seis tareas aprobadas por ambos perfiles. HyperQwen incumplió ambos: en siete tareas terminó al alcanzar los 6.144 tokens, todos o casi todos contabilizados como razonamiento, con cero caracteres de respuesta final; la octava produjo respuesta final, pero falló el test. SOL entregó respuesta final para las ocho, aunque ninguna pasó.

El runner marcó `SCREEN_INVALID` y salió con código 2 por el gate preregistrado de respuestas vacías. Salud HTTP, transporte, grader/sandbox y limpieza pasaron. El rótulo describe el incumplimiento del gate de evaluación; no indica un crash del servidor ni presión de memoria.

## Interpretación de velocidad

No hay seis tareas emparejadas aprobadas —hay cero—, por lo que la comparación E2E de tareas resueltas no se puede calcular. Las medianas de la tabla son descriptivas del lote completo y no prueban superioridad de velocidad ni calidad/velocidad. Los perfiles también difieren en engine, cuantización y especulación. En esta configuración HyperQwen no entregó código final útil en siete casos, así que no es candidato a reemplazar SOL.

## Memoria y limpieza

- Memoria disponible mínima: 102.10 GiB; PSI some/full máximos: 0.00% / 0.00%.
- Swap del cgroup: 0.0 MiB; delta OOM: 0; avisos del monitor: 0.
- Pico de VRAM: GPU0 14055 MiB, GPU1 13112 MiB; temperatura máxima 71 °C.
- `compose down` terminó con código 0; no quedaron contenedores Q167 ni listeners del puerto. Después del no-go se eliminó solo la copia Q167 de pesos (18.045.887.466 B) y sus cachés/temporales propios (553.956.325 B); el HDD recuperó 571.244.544 B medidos en el segundo paso, además de ~18,05 GB al borrar los pesos. La fuente de modelos Q85 también se retiró tras confirmar que no tenía consumidores activos: 24.412.685.738 B; sus artefactos, recibos y hashes quedan. SOL, ASTRA y PeritoSoft no se tocaron. HDD liberado en total: 43.029.970.944 B medidos. No se cerró la GUI ni ningún proceso ajeno. El escaneo autorizado de PeritoSoft no encontró su app ni servidores que terminar.

## Límite del resultado

Es un screen de un seed, ocho tareas, sin tools. No mide calidad general, seguridad, agentes, contexto largo ni otros modos de razonamiento. El preregistro ordena cerrar el screen con 0/8 o 1/8 y no gastar más semillas; cualquier perfil nuevo necesita pregunta y preregistro propios.

Evidencia completa: [`receipts/q167-final-decision.json`](receipts/q167-final-decision.json), `receipts/hyperqwen/final-summary.json`, `receipts/sol/final-summary.json`, y `runs/*/bcb8-result.json`.
