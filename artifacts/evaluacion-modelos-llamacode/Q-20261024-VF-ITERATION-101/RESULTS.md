# Q101 · Resultados

**Estado:** intento 10 cerrado; canario de herramientas fallido antes de `write_file`. HyperQwen queda bloqueado para la campaña de agentes hasta un cambio material del parser/runtime y un prerregistro nuevo.

## Resultado del canario

El servidor HyperQwen/Qwen3.8-27B llegó a `healthy` con TP=2 en las dos RTX 3090. La única llamada del canario produjo `read_file`, pero el argumento `path` no coincidió con el contrato de la fixture. La respuesta terminó en `stop` con 489 tokens de prompt, 507 de completion y 14.246 s. No se invocó `write_file`, no se leyó/escribió la fixture y no se ejecutaron Tool-Eval ni A/B.

La variable preregistrada era aumentar únicamente `write_file.max_tokens` de 512 a 1024. Al fallar la etapa anterior de `read_file`, ese cambio no llegó a evaluarse: resultado **inconcluso para la hipótesis de truncación de escritura**. El recibo no conserva el valor exacto de la ruta inválida, por lo que no puede atribuirse a una forma específica de path.

## Revisión del detector de memoria

Durante 96 muestras de un segundo, `MemAvailable` tuvo un mínimo de 102.201 GiB y un máximo de 109.948 GiB; PSI de memoria some/full alcanzó 1.08%; no hubo avisos del guard, racha severa ni OOM. La PSI de I/O llegó a 21.37% full, registrada por separado y sin umbral de aborto. El guard no detuvo el canario. Al finalizar, el servidor y su contenedor desaparecieron, el puerto 18142 quedó libre y no quedó directorio temporal de fixture.

La calibración conserva como evidencia el uso exitoso de ASTRA DEFAULT/Flash-Next a 1,048,576 tokens: 10/10 datos exactos, RSS máximo del árbol de procesos de 51.14 GiB, `MemAvailable` mínimo de 55.73 GiB, sin PSI ni swap-out y sin aborto. El umbral task-local de 32 GiB deja 23.73 GiB de margen frente al mínimo observado. Ni este umbral ni la unidad transient imponían límites de RAM o swap; las tres propiedades cgroup de memoria/swap estuvieron en `infinity`.

**Conclusión:** los datos disponibles no muestran que el detector haya abortado una ejecución sana por consumo alto. Presión moderada genera avisos; las condiciones de aborto permanecen reservadas a menos de 32 GiB disponibles, OOM nuevo o presión severa sostenida. El fallo de Q101 fue contractual en la ruta `read_file`, no de memoria.

## Alcance y siguiente condición

- No adoptar HyperQwen ni cambiar los perfiles productivos con este resultado; no hay comparación de calidad o velocidad.
- Mantener ASTRA DEFAULT 1M, SOL, Flash-Next productivo y PeritoSoft intactos.
- No continuar Tool-Eval ni A/B de HyperQwen hasta un cambio material de parser/runtime y un nuevo preregistro que capture de forma segura el argumento de path.

Recibos: `receipts/q101-tool-canary-20261024T222317Z.json`, `receipts/q101-cleanup-postflight.json`, `receipts/q101-final-result.json`, `runs/host-samples.jsonl`.
