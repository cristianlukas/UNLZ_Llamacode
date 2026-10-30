# Q-20261030-MODEL-DRIVE-AUDIT — resultados

**Estado:** auditoría de almacenamiento y conciliación con `Modelos locales por peso` completadas. Sólo se hizo inventario y lectura de metadatos; no se usaron GPU, servidores de inferencia ni benchmarks. No se eliminó ningún archivo en este barrido: los artefactos recién encontrados no tienen el trío de mediciones requerido para probar supersession y el único perfil que sí está estrictamente dominado todavía figura como favorito en LlamaCode.

## Alcance y método

Se recorrieron los volúmenes montados C:, D: y HDD extra, además de `/home`, `/opt`, `/mnt`, `/var/lib`, `/root`, `/usr/local`, `/var/cache`, `/srv`, `/tmp` y `/var/tmp`. El inventario buscó archivos con extensiones de pesos/checkpoints (`.gguf`, `.safetensors`, `.pt`, `.pth`, `.ckpt`, `.onnx`, `.model`, `.ggml`, `.bin`, `.ninfer`, `.cact`, `.tflite`, `.pb`, `.h5`, `.weights`, `.params`). El listado bruto está en `/tmp/llamacode-model-audit-20261030.jsonl` y contiene 3.799 coincidencias; es una lista de extensiones, no 3.799 modelos.

| Volumen | Coincidencias brutas | Tamaño acumulado de coincidencias |
| --- | ---: | ---: |
| C: | 1.907 | 203,36 GB |
| D: | 818 | 650,72 GB |
| HDD extra | 796 | 294,57 GB |
| Linux home | 278 | 4,41 GB |

La mayoría de las coincidencias no son pesos de modelos de conversación: por ejemplo, unas 700 `.bin` de Bannerlord en HDD extra, modelos de OCR integrados en Chrome, vocabularios de compilación llama.cpp, cachés de aplicaciones y piezas de runtime. Se excluyeron esas coincidencias de la comparación de calidad de LLMs. Los auxiliares de visión, audio, embeddings, draft/MTP y checkpoints siguen siendo artefactos de IA, pero no son targets generativos independientes y no se pueden comparar con Q172 sin un test propio aplicable.

## Diferencias incorporadas en el Sheet

La pestaña `Modelos locales por peso` quedó leída de vuelta en estas zonas y los valores están en las filas previstas:

- Fila 2: Qwen3.6-35B-A3B NInfer existe en D, pero el archivo mide 124.428.288 B frente a un manifiesto esperado de 22.783.094.528 B. Es un artefacto truncado, no un modelo ejecutable ni un resultado de inferencia.
- Filas 9–12: se localizaron los cuatro GGUF TQW phase2 de 5.680.522.464 B en C:, dentro de `Documents/PeritoSoft`. Se dejaron sin identidad/calidad atribuida y conservados mientras no se confirme su dependencia.
- Fila 13: SHARP checkpoint, 2.809.738.232 B, en caché Torch de C:. Sin perfil Q172 ni ladder TPS atribuibles.
- Fila 14: `party_european_langs.safetensors`, 858.061.536 B, en caché htrmopo de C:. Identidad/tarea no resueltas.
- Fila 15: Unlimited-OCR tiene copias del mismo tamaño en D: y `PeritoSoftBench` en C:. No se comparó hash entre las copias; se conserva la de PeritoSoftBench.
- Filas 18–19: corregidos perfiles NInfer: Q178/Q179 es pipeline dual en ambas RTX 3090; Q171/Q173 es el preview histórico de una RTX 3090, GPU1. Las filas se mantienen separadas porque el runtime y el número de GPU son distintos.
- Fila 82: anotado el GGUF MTP Q8_0 de Flash-Next de 4.137.429.120 B y que los packs residuales hallados son auxiliares, no targets retirados.
- Filas 88–92: se agregaron Maya-XS Q189, Gemma4 E2B, Qwen3.5-2B, Bonsai NInfer v0.17.0 y el staging Engram FP8 incompleto.

Otros modelos nuevos del inventario, como Qwen3.5-4B, ya estaban en la fila 87. En Q189 Maya-XS hay cinco shards repartidos en C:/D:, 276.626.308.260 B en total. Su Q172 fue 83,67/100 en tres semillas, con TC-92 fallando en 2/3; Q173 se omitió por el gate de seguridad. No se extrapola velocidad ni se trata como reemplazo seguro de ASTRA.

## Revisión de supersession

El filtro aplicado es estricto: un artefacto sólo se puede marcar superseded si otro perfil medido tiene **mayor Prefill promedio, mayor Decode promedio y mayor Q172** simultáneamente. Un valor ausente, cero histórico invalidado, score de otra huella o un test sintético no sustituye uno de esos tres valores. También se revisa la dependencia del artefacto antes de borrar.

- **TERRA · Qwen3.8-27B AutoRound** muestra menores promedios tabulados que SOL · Flash-Next RCO Strata (1.743,98 / 49,51 / 62 frente a 2.880,75 / 117,75 / 73), pero esos promedios no son comparables: TERRA Q173 cubrió 8K–256K y SOL Q14 131K–1M. Por eso no concluyo supersession ni borrado. Además, el perfil `177_TERRA · Qwen3.8 27B · vLLM TP2 P2P MTP4 · 262K` sigue configurado como `best=true` y `favorite=true` en `profiles/launches.json`; borrar sus 19.016.938.816 B dejaría ese launcher sin el checkpoint. La fila 24 del Sheet quedó anotada como pendiente de ladder homologado y de retirar/remapear ese launcher.
- **Gemma 4 12B IT QAT** tiene Q173 en 8K–256K, mientras SOL Strata usa 131K–1M; por lo tanto, sus menores medias tabuladas tampoco demuestran supersession. Además, hay fixtures locales de PeritoSoft que apuntan a esa huella exacta. Se conserva.
- Qwen3.5-9B no queda dominado por SOL en Prefill/Decode; los perfiles rápidos que superan su calidad tienen otro intercambio en al menos una métrica. ASTRA, SOL, Bonsai y los otros perfiles con resultados tampoco forman un dominador común en las tres métricas.
- Los artefactos nuevos sin Q172 y/o ladder Q173 no se pueden eliminar como inferiores: faltan mediciones comparables, aunque algunos sean paquetes sin terminar o históricos.

### Artefactos recién hallados sin evidencia para borrado por supersession

| Artefacto | Ubicación / tamaño | Resultado de auditoría |
| --- | --- | --- |
| Maya-XS IQ1_S Q189 | C: + D:, 276,63 GB | Test Q172 conocido; Q173 omitido por seguridad. No sustituye ASTRA por seguridad/velocidad. |
| Gemma4 E2B Q4_0 + mmproj | D:, 3,35 GB + 0,99 GB | Sin Q172 ni Q173 vinculados a esta huella. |
| Qwen3.5-2B Q4_K_M + mmproj | D:, 1,33 GB + 0,67 GB | Sin Q172 ni Q173 vinculados a esta huella. |
| Bonsai 2 NInfer v0.17.0 | D:, 9,52 GB | SHA distinto del NInfer v3 medido; no heredar sus métricas. |
| DeepSeek FP8 Engram staging | HDD extra, 203,07 GB | Sólo 2 de 48 shards. No es ejecutable; su retirada liberaría espacio, pero no cumple la regla de supersession por métricas. |
| Qwen3.8 Flash-Next MTP Q8_0 | D:, 4,14 GB | Auxiliar/drafter, sin calidad ni TPS independiente. |
| TQW phase2 ×4, SHARP, htrmopo | C:, 22,73 GB combinados | Los TQW están dentro de PeritoSoft; los otros no tienen identidad o resultados suficientes. No borrados. |

## Conclusión

El barrido amplió el inventario en cinco filas y corrigió rutas/estados que antes aparecían como ausentes. No encontró “muchos modelos inferiores” fuera del Sheet con pruebas completas: los pesos grandes no listados carecían de Q172/Q173, eran piezas auxiliares o estaban incompletos. Los promedios de TERRA y SOL/Gemma vienen de rangos de contexto distintos, así que no demuestran supersession; TERRA además sigue como launcher favorito/mejor, y Gemma 12B aparece en fixtures de PeritoSoft. No se borraron archivos. Para aplicar el filtro del usuario hace falta comparar los perfiles con niveles de contexto Q173 homologados; el resto de artefactos encontrados requiere sus propias mediciones Q173/Q172 antes de poder clasificarlos.
