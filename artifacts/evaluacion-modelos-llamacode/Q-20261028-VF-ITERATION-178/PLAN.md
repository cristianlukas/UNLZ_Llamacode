# Q178 — Comparación dual de Flash-Next con NInfer-all

> **Estado A02–A05:** se conserva intacta la fila histórica Q171/Q173 (NInfer preview v0.16.1, GPU1). A02 confirmó que ese preview rechaza Flash-Next con dos GPU antes de cargar pesos. A03 reconvirtió en CPU los mismos GGUF IQ2_XS/RCO a NInfer v3. A04 abortó antes de readiness en el stream de expertos desde disco (`cudaErrorInvalidResourceHandle`). A05 completó la ladder con expertos residentes en GPU, ambas 3090 y KV sparse en host después de 32K: P/D 2166,9/94,60 a 8K; 2261,1/92,04 a 32K; 2209,4/90,48 a 64K; 2052,7/83,05 a 128K; 1743,6/76,39 a 256K. Init de proceso 287,783 s y relanzamiento inmediato 287,917 s. A05 cambia runtime, formato y residencia frente a Q173; es una fila separada, no un A/B puro de topología. No se vuelve a correr Q172 ni se atribuye a A05 el 77/100 de Q173.

## Objetivo

Comprobar si el artefacto Qwen3.8 Flash-Next RCO IQ2_XS que antes se midió con el preview NInfer de una sola GPU puede ejecutarse con el build Linux NInfer-all fijado en Q174, usando ambas RTX 3090. Si pasa el gate de humo, medir prefill/decode serialmente hasta el límite nativo de 256K. Esto completa la celda dual que Q176 dejó como N/D; no reemplaza resultados de Strata ni cambia el perfil productivo.

## Artefactos fijados

- Texto v3 en HDD extra: `reconverted-v3/text/qwen4exp.ninfer`, 32.000.000.000 B, SHA-256 `c599a10d696118a8235c953dda3fb45ef55b8c40356f4c688787cef116b8053d`; parte `qwen4exp.ninfer.part-0001`, 6.640.145.152 B, SHA-256 `fa72b1f0f2d57615500a6c3568a8e8583cf1b403b2be617fa67e864c890314a2`.
- Tabla n-gram v3 en Disco local: `reconverted-v3/ngram/qwen4exp-ngram.ninfer`, 28.800.142.336 B, SHA-256 `2a3c7868c550171376785ff393ceff26d5b43ed7c9d2c341838582ff1f625656`.
- Runtime: NInfer-all Q174, commit `3d882fc116941d9233c40bf30f4d66dbaa3d24bd`, binario SHA-256 `09145c529015ac7d27ce63214138625927c70c1e89e4291594d74be59bd5f895`.
- Los GGUF fuente son los mismos de Q173 (hashes en `PLAN-amendment-03-v3-reconversion-after-preview-dual-limit.md`). La conversión CPU finalizó en 372,166 s para texto y 17,328 s para la tabla; `artifact.inspect` confirma formato v3, 48 capas, 512 expertos y PLE presente.
- Topología: `--devices 0,1`, una etapa de pipeline por GPU; no es tensor-parallel. Se exige al mismo servidor compute en GPU0 y GPU1; no hay fallback single-GPU.

## Perfil y protocolo

- Perfil A05 medido: bind `127.0.0.1:18478`; máximo una petición; KV int8 y capacidad/contexto 262.144; expertos residentes en GPU (`--expert-residency device`), pipeline `--devices 0,1` y KV residente hasta 32.768 posiciones (`--kv-resident 32768`), con KV sparse restante en host; tabla n-gram en disco; speculative/MTP y draft n-gram desactivados. A04, separado, usó expertos en disco y falló antes de readiness.
- Medir dos inicios secuenciales: proceso/modelo ausente de VRAM → `/health`; luego parar limpiamente y relanzar de inmediato → `/health`. `cold` y `hot` son etiquetas de proceso/caché probable: no se vaciará ni instrumentará el page cache, y no se enviará generación durante los cronómetros. Tras el segundo inicio, un smoke no puntuado exige exactamente 16 tokens antes de permitir la ladder.
- Si ambos inicios pasan, ladder serial de fixture sintético determinista tokenizado por el propio servidor: 8.192×3, 32.768×1, 65.536×1, 131.072×1 y 261.888×1 prompt tokens; 128 tokens de salida exacta; `cache_prompt=false`; sampling temp 0,6, top-p 0,95, top-k 20, min-p 0, repeat 1, presence 0, seed 42. Se excluye 512K por instrucción del usuario. No se intenta 1M con este perfil; el resultado Qwen Flash-Next YaRN×4/1M existente es el de Strata Q14/Q35 y Q176.
- Guard: detener sólo el proceso propio si ocurre error de checksum, otra inferencia activa, falta de cualquier GPU, OOM/Xid/crash, truncamiento/token-count incorrecto, listener no local, puerto ocupado o MemAvailable <32 GiB durante cuatro muestras consecutivas de 15 s. No limpiar swap global ni cerrar otras apps.
- Calidad: no ejecutar Q172 de nuevo en esta prueba de rendimiento. Q173 tiene Q172 77/100 del mismo GGUF en NInfer preview v0.16.1/GPU1, con fallos TC-75/82/84/92; se reporta solo en la fila histórica y no se atribuye como score del runtime nuevo ni se promueve el perfil.
- No modificar los perfiles productivos ASTRA/SOL, el contexto 1M de Strata ni PeritoSoft.

## Cierre A05

La primera carga llegó a readiness en 287,783 s y la recarga inmediata en 287,917 s. En ambas el mismo PID apareció como proceso CUDA en GPU0 y GPU1, con aproximadamente 20,8 GiB ocupados por tarjeta. Aunque no se purgó el page cache, ambas cargas leyeron los 36 GiB de artefactos a velocidades cercanas a 130 MiB/s; por eso se informa “proceso inicial / relanzamiento inmediato”, no disco frío/caliente. Q176/Q173 históricos no se sobrescriben.

La ladder completó sin errores: 8K×3 (medianas) y 32K/64K/128K/261.888×1, con 128 tokens de salida exacta. Los puntos son P/D en tok/s: 2166,9/94,60; 2261,1/92,04; 2209,4/90,48; 2052,7/83,05; 1743,6/76,39. MemAvailable posterior 112.296.708 KiB; PSI sin presión; cero compute PIDs, proceso propio detenido con exit 0 y puerto 18478 libre. No hubo OOM/Xid. El contexto 512K/1M no se ejecutó; Qwen Strata YaRN×4/1M sigue siendo una medición aparte.

Resultados completos y límites: `RESULTS.md`; JSON/eventos: `runs/ninfer-device-dual-context-ladder.json`, `runs/ninfer-device-dual-8k.json`, `runs/ninfer-device-dual-contexts.json` y sus JSONL de eventos; preregistro: `receipts/prereg-amendment-05-device-residency.json`.

## Criterio

Compatibilidad/ladder válidos sólo si el smoke genera texto, el mismo PID aparece como compute en ambas GPU, cada muestra tiene el prompt y output exactos, cache cero, timing positivo y limpieza verificable. Un fallo previo a inferencia se registra y detiene; no se fuerza un fallback ni se repite sin amendment.

