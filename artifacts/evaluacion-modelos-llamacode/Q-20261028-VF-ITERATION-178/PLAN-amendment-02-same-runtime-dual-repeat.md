# Q178 A02 — Repetir NInfer preview Q173 con ambas RTX 3090

## Motivo y comparación

El usuario indicó conservar la medición histórica de NInfer Flash-Next Q171/Q173 en una RTX 3090 y repetirla usando las dos GPU. Para aislar el efecto de la topología, se fija el mismo binario NInfer Linux preview v0.16.1 y los mismos artefactos IQ2_XS/n-gram de Q173. La fila Q173 de una sola GPU queda intacta y el resultado de dos GPU se agrega como una fila nueva. No se atribuirá al perfil dual el Q172 77/100 medido previamente en GPU1.

La CLI verificada del binario fijado acepta `--devices N,M`. Las dos tarjetas se consideran etapas consecutivas de pipeline (no tensor-parallel). Si el smoke no demuestra el mismo PID como compute en GPU0 y GPU1, se detiene sin fallback.

## Fijaciones

- Modelo: Q171 artifact `qwen4exp.ninfer` y `.part-0001`, SHA-256 heredados y verificados por Q171/Q173; no modificar.
- Tabla n-gram: Q39 `qwen4exp.ninfer.ngram`, SHA-256 heredado y verificado por Q171/Q173; no modificar.
- Runtime: `/media/cristian/Disco local/LlamaCode-cache/Q171-ninfer-build-r1/apps/ninfer-serve`, NInfer Linux preview v0.16.1, SHA-256 `59e5f3e21246ac9f4bd871943e1e1348fbcb7ad6b3d2d32d046b5d4595bb3bac`.
- Client: llama-benchy 0.4.0 existente y tokenizer Qwen fijado en Q173; el preflight recalcula sus SHA antes de usarlo.
- Endpoint de evaluación: `127.0.0.1:18479`; el puerto histórico Q173 `18473` queda sin cambios.
- Topología dual: `--devices 0,1`; `CUDA_VISIBLE_DEVICES=0,1`; máximo una petición; ambas GPU deben aparecer como compute para el PID exacto.

## Protocolo

El servidor se configura con la misma ventana y parámetros de Q173: contexto/KV 262144, KV int8, sin prefix reuse, sin speculative decoding, n-gram drafting desactivado, expert state persistente desactivado, límite de salida 128 y sampling temp 0.6/top-p 0.95/top-k 20/min-p 0/repetition 1/presence 0/seed 42. Se mide `Popen → GET /v1/models` para el primer proceso y para un relanzamiento limpio inmediato. Son medidas de inicio de proceso con caché de disco no purgada; se llamarán cold-process y hot-likely, no cold-disk.

Después de un smoke no puntuado de 16 tokens, se reutiliza la matriz Q173 sin cambiar sus muestras: 8K×3 y 32K/64K/128K/261888×1; cada respuesta debe generar exactamente 128 tokens. Se reutiliza el mismo cliente, tokenizer, prompt sintético Sherlocked cacheado, salida 128 y reporte de TTFT/prefill/decode cliente observado. No 512K ni 1M para NInfer. No ejecutar Q172 de nuevo; el 77/100 y sus fallos críticos se muestran como evidencia histórica GPU1-only.

## Guardas y cierre

Un servidor de inferencia ajeno bloquea el inicio. Mantener el bloqueo si MemAvailable cae por debajo de 32 GiB durante cuatro muestras de 15 s, si hay OOM/Xid/crash, error de hashes, salida/tokenización inválida, listener fuera de loopback, puerto ocupado o ausencia de compute dual. No cerrar GUI/PeritoSoft; ningún modelo o perfil productivo se modifica. Detener únicamente el proceso Q178 propio y verificar puerto/procesos tras cada cierre.

Al cerrar, agregar una fila dual separada a la matriz y al Google Sheet; no sobrescribir la fila Q173 histórica. Identificar explícitamente que el único factor intencional que cambia es `--devices 1` frente a `--devices 0,1`; cualquier diferencia de carga de escritorio/GPU se conserva como caveat.

## Conversión v3 supersedida

A01 comenzó una conversión CPU del mismo GGUF al formato requerido por el runtime Q174; se interrumpió en el tensor 89/1027 al comprobarse que el binario exacto v0.16.1 de Q173 sí expone `--devices`. La conversión habría cambiado la versión del motor y reducido la comparabilidad. No produjo ningún archivo de modelo nuevo ni asignó GPU. Recibo: `receipts/conversion-v3-superseded.json`. El source-config preparado por A01 se conserva como evidencia auxiliar; los GGUF originales, Q171 artifact y caché no se tocaron.
