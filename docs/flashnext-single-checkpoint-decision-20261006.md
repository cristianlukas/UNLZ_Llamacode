# Decisión de conservar un solo Qwen3.8 Flash-Next — 6 oct. 2026

## Decisión

Se conserva **Swift 1.5 IQ3_XXS** como único checkpoint Flash-Next local. No lo elijo porque haya ganado coding en calidad: ASTRA IQ3_S calibrado y Swift terminaron las dos corridas LC-H1 con **38/38**. ASTRA fue más rápido en esa batería. Swift sí tuvo menor latencia en el A/B de decisiones breves de Computer Use, ocupaba menos, y sus pesos estaban en D, donde hay más margen que en C. La prioridad solicitada es reducir el conjunto pesado a una sola variante.

| Métrica | ASTRA IQ3_S calibrado | Swift IQ3_XXS | Lectura |
|---|---:|---:|---|
| LC-H1, dos corridas | 38/38 y 38/38; media 1.868,9 s | 38/38 y 38/38; media 2.109,7 s | Empate final. Swift tarda ~12,9% más; ASTRA es ~11,4% más rápido que Swift. |
| Primera pasada LC-H1 | 29/38 y 31/38 | 29/38 y 29/38 | ASTRA tuvo una ventaja de 2 tareas en la repetición; n=2 por perfil. |
| Computer Use textual breve | 100% exactitud/validez/seguridad; 0 errores HTTP | Lo mismo; mediana 22,8–23,9% menor | Swift gana latencia en esta tarea acotada, no en GUI de extremo a extremo. |
| Shards de pesos | 83.617.662.656 B (~83,62 GB decimales) | 75.966.073.120 B (~75,97 GB decimales) | Swift ahorra 7,65 GB en pesos. |
| Ubicación | C, poco espacio libre | D | Se deja el único checkpoint en D. |

La prueba de Computer Use usó el mismo corpus `computer_use_prompt_order_hard_v1`, 24 estados, tres órdenes y tres pasadas (216 respuestas por perfil). Ambos fueron 72/72 correctos y 63/63 seguros por orden; `sandwich` no cumplió el gate de latencia en ninguno. No fue una prueba de manejo real de la GUI. No se repitieron cargas: las corridas existentes cubren el mismo checkpoint/perfil y dan evidencia suficiente para esta elección de almacenamiento.

## Retirados

Los pesos y paquetes listados abajo se quitaron para cumplir la decisión de mantener una sola variante. **Retirado no significa peor demostrado en calidad.** En Orca, los gates incompletos no permiten clasificar calidad; Albucino tiene ventajas de contexto largo. Al borrar fuente y conversión NVFP4 se pierde la posibilidad de retestear Orca sin volver a descargar y convertir.

| Volumen | Ruta retirada | Bytes inventariados | Motivo y límite de evidencia |
|---|---|---:|---|
| C | `/media/cristian/7CFE1E0FFE1DC1F6/models/Strata-review-20261002/` | 93.000.847.852 | ASTRA IQ3_S calibrado/base y sus assets. Misma familia de pesos entre perfiles; ASTRA era más rápido en LC-H1, pero se priorizó Computer Use y ubicación/espacio. No se declara inferior en calidad. |
| C | `/media/cristian/7CFE1E0FFE1DC1F6/models/Orca-Qwen38-uncensored-IQ3_XXS/` | 85.202.685.829 | Orca IQ3_XXS: HE20 agotó ~1801 s; no hubo LC-H1 válido completo. Retiro por espacio/objetivo de un solo checkpoint, no por score de calidad. |
| HDD extra | `/media/cristian/HDD extra/Orca-Qwen38-uncensored-IQ3_XXS-shard2/` | 22.566 | Residuo `.part.aria2`/metadatos, no un checkpoint completo. |
| D | `/media/cristian/Disco local/Models/From-C/Qwen3.8-Flash-Next/albucino-w4a16-fp8ple/` | 128.986.587.138 | Albucino W4A16 + PLE FP8. LC-H1 en paridad y ventajas a contexto largo; requiere cerca de 128 GiB RAM. Retiro por mantener una sola variante, no por inferioridad general. |
| D | `/media/cristian/Disco local/strata-nvfp4-reddit-20261005/orca-modelopt-nvfp4/` | 69.496.707.212 | Pack de expertos/dense Orca NVFP4 de la evaluación. Sólo HE0 válido con workaround, sin LC-H1 completo. |
| D | `/media/cristian/Disco local/strata-nvfp4-reddit-20261005/mtp/` | 1.712.910.528 | MTP/runtime de la evaluación Orca NVFP4; ya no acompaña al único perfil conservado. |
| HDD extra | `/media/cristian/HDD extra/OrcaRouter-Qwen3.8-Flash-Next-Uncensored-ModelOpt-NVFP4/` | 135.253.767.574 | Fuente safetensors Orca NVFP4. Se quita junto con la conversión; para repetir la evaluación habrá que volver a descargar. |
| HDD extra | `/media/cristian/HDD extra/strata-nvfp4-eval-20261004/` | 126.411.558.786 | Conversión/intermedio GGUF + PLE + embeddings; sólo HE0 1/1 tras reparación en 355,284 s. |

Espacio inventariado que se espera recuperar: C **178.203.533.681 B**, D **200.196.204.878 B**, HDD extra **261.665.348.926 B**, total **640.065.087.485 B** (640,07 GB decimales / 596,11 GiB antes de diferencias de asignación del filesystem). Después de vaciar la Papelera por volumen y sincronizar NTFS, `df -B1` mostró 186.342.199.296 B libres en C, 332.235.694.080 B en D y 352.944.111.616 B en HDD extra. El aumento observado fue 178.203.611.136 B en C, 200.196.485.120 B en D y 261.666.078.720 B en HDD extra; la diferencia pequeña frente al tamaño aparente corresponde a metadatos/asignación NTFS.

## Se conserva / queda fuera de la limpieza

- **Swift IQ3_XXS** es el único Flash-Next retenido: `/media/cristian/Disco local/Models/Strata-swift-20261003/`, 77.514.088.073 B en el árbol completo; 75.966.073.120 B de shards de pesos. Los archivos de resultados históricos de los perfiles retirados permanecen en el repo.
- El directorio C `Qwen3.8-Flash-Next-GSQ-RCO-Coder-GGUF` sólo contiene `README.md` y directorios vacíos (~10,8 KB), sin checkpoint; se conserva el README.
- Los `.hf-cache-*` encontrados bajo C sólo contenían directorios vacíos/de referencias (40 B cada uno), no shards duplicados; se conservan.
- **Qwen3.8-27B SOL/UD-Q4/UD-Q6, ByteShape, Occamy y otros Qwen3.8-27B** no son los checkpoints Flash-Next retirados y quedan intactos.
- No se editó el catálogo de perfiles/harness. En la configuración local inspeccionada no había una ruta personalizada activa a ASTRA o Swift. Si se usa la entrada de servidor ASTRA del catálogo, la ruta del modelo deberá apuntar manualmente al Swift retenido.
- Flash-Next no reemplaza ASR/TTS de Ingi-Charla; no se hizo prueba acústica.

## Validación y trazabilidad

Se revisaron los recibos previos LC-H1 y Computer Use, rutas y tamaños exactos, el estado de los procesos/listeners antes de borrar, y luego se comprobaron ausencia de cada ruta retirada, presencia de Swift, espacio libre por volumen y copias idénticas de la planilla. El inventario marca los registros retirados como históricos; sus bytes no deben sumarse al espacio actual. La planilla y comparativa mantienen ambos resultados viejos y esta decisión final para no perder historial.

Fuentes: `artifacts/flashnext-repeat-20261005/results.json`, `artifacts/flashnext-computer-use-20261006/report.md`, `artifacts/strata-nvfp4-reddit-20261005/`, y la tabla ampliada enlazada desde el inventario externo.
