# Q178 A03 — Reconversión NInfer-all para calificación dual Flash-Next

## Motivo

El intento A02 reutilizó el binario y los pesos exactos de Q173 para aislar el cambio de topología, pero el NInfer preview v0.16.1 abortó en 193 ms con `Qwen3.8-Flash-Next: runs on one GPU`. No cargó pesos ni usó CUDA. No se fuerza otro intento con ese runtime. Para cumplir la solicitud de medir Flash-Next con las dos RTX 3090, A03 usa el build NInfer-all Q174, que implementa pipeline stages. Como cambia la versión del runtime, la fila dual se identificará aparte y no se presentará como comparación causal de GPUs contra Q173.

## Conversión CPU fijada

- Runtime de conversión: repo `/tmp/q174-d/ninfer-src`, commit `3d882fc116941d9233c40bf30f4d66dbaa3d24bd`; venv CPU existente en `/media/cristian/Disco local/Modelos-eval/Q-20261028-VF-ITERATION-178/tooling/cpu-converter-venv`; validar `torch.cuda.is_available() == false` antes de ejecutar.
- Source config ya validado en A01: `/media/cristian/HDD extra/Modelos-eval/Q-20261028-VF-ITERATION-178/reconverted-v3/source-config`; 48 capas, 512 expertos y PLE válido. SHA del config `9449ef5a1f98e0c0beadc0e4f182f163ae1cedb201abf8e47a721aefe1adf4b8`.
- GGUF fuente sin modificar: shard 1 en `.../00001-of-00002.gguf`, 39.225.954.592 B, SHA-256 `92cee27ae5bbadcd732416a0f7a7f0acc092399dbbe8f5a5efa707c2ec0a49d7`; shard 2 es la fuente de la tabla n-gram y su fingerprint heredado debe cotejarse con Q173 antes de convertir.
- Preflight de espacio inmediatamente anterior: HDD extra ≥50 GB libres, Disco local ≥100 GB y `/` ≥5 GB. El `TMPDIR` se fija en Disco local para no usar `/tmp`. Salir antes de convertir si un umbral no se cumple.
- Salidas nuevas, ninguna preexistente: texto en HDD extra `reconverted-v3/text/qwen4exp.ninfer` (límite 32.000.000.000 B por archivo) y tabla en Disco local `reconverted-v3/ngram/qwen4exp-ngram.ninfer`. No sobrescribir el artifact Q171, n-gram Q39, GGUF originales ni copias productivas.
- Conversión de texto: recipe `qwen3_8_flash_next_gguf`, components `text`, sources `gguf=<shard1>` y `ngram=<shard2>`, device `cpu`, rows-per-chunk `65536`, max-file-bytes `32000000000`.
- Conversión separada de n-gram: mismos recipe/source shard2, components `ngram`, device `cpu`, rows-per-chunk `65536`.
- Cada tarea CPU se ejecuta en serie. Tras ambas, revisar artifact manifests/configs, `ple_layers`, dimensiones y compatibilidad runtime; calcular SHA/tamaño de todos los archivos antes de cualquier prueba con GPU.

## Gate previo a GPU

No cargar modelos al terminar la conversión. Una enmienda A04 debe fijar hashes de los artefactos nuevos y del runner de inferencia, y revalidar Q178 lock, ningún servidor activo, puertos, MemAvailable, dos RTX 3090 visibles, espacio en disco y CLI del build Q174. Luego medir cold/hot process startup y contexto 8K×3 + 32K/64K/128K/261888×1 con salida 128 y sin 512K/1M. La prueba exige el mismo PID compute en GPU0+GPU1 y no permite fallback. El Q172 77/100 de Q173 se conserva con etiqueta GPU1/runtime v0.16.1; no se atribuye al v3 ni se vuelve a ejecutar en esta enmienda.

## Resultado de A03

Conversión de texto completada en 372,166 s y conversión n-gram en 17,328 s, ambas en CPU; inspección de los dos artefactos v3 pasó y hashes completos quedaron asentados en `receipts/conversion-v3-completion.json`. El preflight de la enmienda A04 y el runner fijado están en `receipts/prereg-amendment-04-ninfer-all-dual-context-ladder.json` y `scripts/run_ninfer_all_dual_ladder.py`. No se usó GPU en A03.
