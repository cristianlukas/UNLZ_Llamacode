# Q178 A04 — NInfer-all v3 dual RTX 3090: contextos y arranque

## Motivo y alcance

El intento same-runtime Q173/A02 no pudo continuar: NInfer preview v0.16.1 rechaza Flash-Next en `--devices 0,1` antes de cargar pesos. Se conserva su fila histórica Q173 de una GPU y se usa NInfer-all Q174 para comprobar una ruta dual. El cambio de runtime y la reconversión se muestran como perfil separado; no se interpretará como una comparación causal de sumar una GPU.

## Identidad fijada

- Pesos: GGUF IQ2_XS/RCO originales de Q173, convertidos con NInfer v3 desde commit `3d882fc116941d9233c40bf30f4d66dbaa3d24bd`.
- Texto: `/media/cristian/HDD extra/Modelos-eval/Q-20261028-VF-ITERATION-178/reconverted-v3/text/qwen4exp.ninfer`, 32.000.000.000 B, SHA-256 `c599a10d696118a8235c953dda3fb45ef55b8c40356f4c688787cef116b8053d`; parte `qwen4exp.ninfer.part-0001`, 6.640.145.152 B, SHA-256 `fa72b1f0f2d57615500a6c3568a8e8583cf1b403b2be617fa67e864c890314a2`.
- Tabla n-gram: `/media/cristian/Disco local/Modelos-eval/Q-20261028-VF-ITERATION-178/reconverted-v3/ngram/qwen4exp-ngram.ninfer`, 28.800.142.336 B, SHA-256 `2a3c7868c550171376785ff393ceff26d5b43ed7c9d2c341838582ff1f625656`.
- El texto y la tabla fueron convertidos en CPU (372,166 s y 17,328 s); los artefactos se inspeccionaron con `artifact.inspect`: texto v3, 48 capas, 512 expertos, `ple_layers=[1]`, 1.032 objetos y 74.597 usos; tabla v3, 320.001.536 filas IQ4_NL. Los GGUF fuente no se modificaron.
- Runtime de inferencia: `/tmp/q174-d/ninfer-build-short/apps/ninfer-serve`, SHA-256 `09145c529015ac7d27ce63214138625927c70c1e89e4291594d74be59bd5f895`.
- Cliente: llama-benchy 0.4.0, SHA-256 `e8a892fe937d5ae1b6a43c31e8cb286ce4774f70396f62ab71008c9ddb0a01a1`; tokenizer Qwen3.6-27B y hashes de sus JSON fijados en `receipts/prereg-amendment-04-ninfer-all-dual-context-ladder.json` para mantener exactamente la cohorte Q173.
- Runner preregistrado: `scripts/run_ninfer_all_dual_ladder.py`, SHA-256 `3bcbb98686393458fdbf19705e68b955af19214372bb1732bc2e03a93a7024a7`.

## Protocolo preregistrado

- Pipeline por capas en GPU0+GPU1 (`--devices 0,1`), no tensor-parallel; misma instancia debe figurar como proceso compute en ambas GPU antes de aceptar cada etapa.
- Servidor local `127.0.0.1:18478`, contexto/KV de 262.144, KV int8, concurrencia 1, expertos y n-gram en disco, prefix reuse/speculation desactivados. Muestreo: temperature 0,6; top-p 0,95; top-k 20; min-p 0; repetition penalty 1; presence penalty 0; seed 42.
- Arranque uno: proceso sin instancia anterior, Popen→`/health` y `/v1/models`; luego cierre limpio. Arranque dos: relanzamiento inmediato, mismo readiness. Son **inicio de proceso** y **relanzamiento probable-cache-warm**; el SHA completo de los artefactos ya los leyó y no se limpia el page cache, así que no se llamarán “disco frío/caliente”.
- Escalera serial llama-benchy igual a Q173: 8.192 tokens ×3; 32.768, 65.536, 131.072 y 261.888 ×1; generación exacta de 128 tokens; sin cache ni warmup por contexto. 261.888 deja espacio para plantilla de chat y salida bajo el límite de 262.144.
- Prefill = tokens reales reportados por el endpoint / TTFT; decode = 128 tokens / segundos de decode; reportar medianas en 8K y la única muestra por los demás contextos. Son tasas observadas por cliente, no temporización de kernel.
- No se ejecuta Q172: la calidad 77/100 y los fallos TC-75/82/84/92 quedan atribuidos exclusivamente a Q173 preview v0.16.1/GPU1. No 512K ni 1M en esta prueba; el 1M YaRN×4 de Strata permanece como fila distinta.
- No purgar cachés, no detener apps ajenas, no fallback a una GPU. Abort ante servidor ajeno, puerto ocupado, identidad/hash distinto, GPU ausente, proceso sin compute en ambas, error de servidor, contexto/output incorrecto, OOM/Xid, MemAvailable <32 GiB durante cuatro muestras consecutivas de 15 s o limpieza no verificable.

## Estado

La conversión y la inspección de artefactos pasaron. Esta enmienda y su preregistro fueron escritos antes de usar GPU. El preflight final se vuelve a ejecutar inmediatamente antes del primer arranque. Los resultados se añaden como fila dual separada; no se reemplaza ni elimina Q173.
