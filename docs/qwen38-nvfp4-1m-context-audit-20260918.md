# Auditoría: Qwen3.8 NVFP4 con `max-model-len=1M` — 2026-09-18

## Resultado ejecutivo

El reporte demuestra que vLLM puede reservar una ventana de un millón de
tokens con cuatro GPU de 24 GB, usando NVFP4, KV FP8 y una extrapolación YaRN
de RoPE. No demuestra que Qwen3.8 conserve calidad, recuperación ni latencia
útil a 1M. Los comentarios del mismo reporte sitúan una zona más prudente cerca
de 200–256K y advierten degradación importante por encima de ~550K.

No es una mejora instalable en nuestro equipo: tenemos 2× RTX 3090 de 24 GB,
48 GB de VRAM total, y el perfil SOL ya usa TP2/P2P, AutoRound INT4, KV FP8 y
262.144 tokens. No se descargó NVFP4 ni se modificó SOL.

## Qué cambia respecto de SOL

| Elemento | Reporte | SOL local |
| --- | --- | --- |
| GPU | 4× RTX Pro 4000 de 24 GB | 2× RTX 3090 de 24 GB |
| Tensor parallel | TP4 | TP2/P2P |
| Pesos | Qwen3.8-27B NVFP4 | Qwen3.8-27B AutoRound INT4 |
| KV | FP8 | FP8 |
| Contexto anunciado | 1.000.000 asignado | 262.144 validado |
| Tokens batched | 16.384 | 8.192 por defecto, con umbral de long-prefill configurable |
| Calidad publicada | Sin BCB/HE/tool-use reproducible | BCB 8/8, tool-use OK |

La única parte directamente portable es KV FP8, que SOL ya utiliza. La ruta
NVFP4 no ofrece una ventaja útil en SM86: en Ampere se admite por una ruta de
dequantización A16, no por el fast path NVFP4/MXFP4 de hardware más nuevo.

## El millón de tokens no equivale a contexto operativo

El comando del reporte combina `--max-model-len 1000000`, la variable que
permite superar el límite declarado y `rope_parameters` con `factor=4.0` y
`original_max_position_embeddings=262144`. Eso es extrapolación de posición,
no validación del modelo en 1M. La asignación de KV puede arrancar y aceptar
una petición sin que el modelo recupere bien información ubicada cerca del
final.

Para promover un contexto extremo habría que superar una escalera de
needle/retrieval, tool-use y BCB con contexto creciente, no sólo comprobar que
`/health` responde.

## Qué ideas sí sirven para LlamaCode

1. Mantener KV FP8 en SOL; ya está activo y validado.
2. Mantener `max-num-batched-tokens` separado de `max-model-len`.
3. Medir 131K, 196K y 262K con recuperación real, no sólo carga.
4. Mantener el prefijo MCP canónico: el prefix cache de SOL ya reduce TTFT
   cuando las herramientas llegan con el mismo orden y claves.
5. Registrar por separado contexto asignado, contexto llenado, TTFT, PP, TG,
   preemptions y calidad final.

La configuración SOL ya incluye prefix caching, `prefix-match-unit=16`,
chunked prefill, `mamba-cache-mode=align`, KV FP8, TP2/P2P y MTP4. No hay una
bandera del reporte que justifique cambiar esos valores.

## Qué no se incorpora

- No se intenta TP4: faltan dos GPU y la topología actual sólo expone dos 3090.
- No se cambia SOL a NVFP4: no aporta un kernel compatible con este hardware.
- No se eleva SOL a 1M: el modelo fue validado hasta 262K y la extrapolación
  no tiene una validación de calidad equivalente.
- No se aumenta arbitrariamente `max-num-batched-tokens` a 16K.
- No se interpreta el reporte como superioridad de velocidad: no publica PP,
  TG sostenido, TTFT ni calidad comparable con nuestro BCB.

## Decisión

El reporte no agrega un perfil útil para LlamaCode. SOL permanece como default
para coding y agentes. El contexto operativo recomendado sigue siendo 200K
aproximadamente, con 262K como techo validado; para sesiones más largas conviene
resumir/compactar o usar subagentes con prefijos estables.

La referencia queda registrada para una futura campaña sólo si aparecen cuatro
GPU compatibles y una suite de retrieval/BCB a 256K, 400K, 550K y 1M.
