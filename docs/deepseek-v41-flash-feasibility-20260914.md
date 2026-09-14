# Evaluación de factibilidad: DeepSeek-V4.1-Flash

Fecha: 2026-09-14  
Equipo: Ubuntu, 2× RTX 3090 de 24 GiB, 123 GiB de RAM, P2P activo

## Resumen

No se descargó el modelo porque el GGUF publicado ocupa aproximadamente 502 GB en 11 shards y el cabezal DSpark ronda 8 GB. Nuestra máquina tiene 48 GiB de VRAM y 123 GiB de RAM; el artefacto completo no entra en memoria y tampoco queda espacio suficiente en los discos locales para una copia de trabajo.

El reporte externo sí es técnicamente interesante, pero describe una ruta distinta: un fork específico de llama.cpp con streaming de expertos desde NVMe, caché de expertos en VRAM/RAM y soporte propio para DeepSeek-V4.1. El runtime de LlamaCode no contiene esa implementación V4.1 ni puede cargar el GGUF con el llama.cpp normal.

## Comprobaciones realizadas

| Comprobación | Resultado |
| --- | --- |
| Artefacto V4.1 presente en `/media/.../models` | No |
| Soporte V4.1 en los runtimes locales de LlamaCode | No validado; el soporte disponible corresponde a DeepSeek V4 anterior y DSpark compatible, no a este port V4.1 |
| Espacio libre en partición de modelos | ~21,5 GB |
| Espacio libre en `/media/cristian/Disco local` | ~261 GB |
| Espacio libre en `/media/cristian/HDD extra` | ~334 GB, en otra partición |
| Modelo completo descargable en una ubicación local | No; ninguna ubicación individual tiene 502 GB libres |
| Arranque o benchmark local V4.1 | No ejecutable sin el fork y los pesos específicos |

## Qué aportan los números externos

El port reporta 5,12 tok/s para contenido nuevo y 21,27 tok/s para contenido cuyos expertos ya están residentes, con un techo de 6,2 tok/s sin fallos de caché de disco. También reporta que más RAM, más caché de VRAM, políticas de eviction y varios métodos especulativos no resolvieron el cuello de botella de I/O.

Esos valores no son comparables directamente con SOL: se obtuvieron en una RTX 5090 con un motor de streaming especializado. Aun tomando el mejor caso residente, no hay evidencia de que sea una opción práctica para nuestras sesiones agénticas; el caso real de contenido nuevo es muy lento.

El cabezal DSpark tampoco justifica por sí solo la migración: en el reporte resultó neutro en contenido mixto porque verificar un bloque requiere acceder a la unión de expertos de todos los tokens. El propio proyecto lo deja opcional.

## Comparación con LlamaCode

| Perfil | Evidencia local | Decisión |
| --- | --- | --- |
| SOL | Qwen3.8, BCB 8/8, 74 tok/s narrativo / 102 tok/s código, 262K validado | Mantener default |
| GALACTA | DeepSeek V4, BCB 8/8, ~9,65 tok/s, 131K | Mantener como calidad validada |
| ASTRA | Qwen Flash-Next, contexto largo, sin BCB válido | Experimental |
| DeepSeek-V4.1-Flash | No ejecutable localmente; referencia externa 5,12 tok/s en contenido nuevo | No agregar |

## Conclusión y cambios

DeepSeek-V4.1-Flash no es superior ni instalable de forma razonable en nuestro setup actual. No se modificó el default, el dropdown ni los perfiles existentes. Tampoco se descargaron archivos grandes ni se alteró la carpeta de modelos.

La idea reutilizable para LlamaCode es conceptual: medir por separado contenido frío y residente, y no confundir throughput de caché caliente con latencia real de una conversación. Eso ya queda cubierto por las pruebas de contexto y caché de nuestros perfiles; no justifica cambiar SOL.

