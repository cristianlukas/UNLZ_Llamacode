# Q34 — Comparación directa de velocidad contra SOL

## Pregunta

¿La mejora de velocidad de Qwen3.8-27B NInfer v3 observada en Q32 frente a llama.cpp se mantiene frente al perfil productivo SOL que está configurado hoy? La comparación es de perfiles completos y velocidad; no aísla pesos ni reabre el gate de calidad.

## Prioridad y decisión que puede cambiar

P2, después del gate P1 Flash-Next (que sigue bloqueado en Linux por soporte Windows-only). Una mejora directa puede respaldar un piloto aislado de generación sin tools; no puede habilitar la adopción con tools: Q32 obtuvo 78/100 y falló TC-74 3/3, TC-84 2/3 y TC-92 2/3 con divulgación entre tenants.

## Perfiles fijados

- **Control SOL actual:** `177_SOL`, Qwen3.8-27B Frozenlock AutoRound INT4/W4A8, vLLM OpenAI `v0.27.1`, TP=2 en las 2×RTX 3090, MTP n=4, máximo configurado 262144, W4A8=1 y MAX_NUM_SEQS=8 (defaults del compose tras verificar `.env` sin sobreescritura de esas claves). Fuente de verdad local: `profiles/launches.json` (backend Linux `2baf3292-033d-4a6c-9f84-ea13ae4aae3b`), compose `models/qwen3.8-27b/vllm/compose/dual/autoround-int4/mtp.yml`, su `.env` y override de cuarentena GPU0. El test debe clonar sólo el puerto/nombre del contenedor; no editar ni iniciar el servicio productivo.
- **Candidato:** artefacto NInfer 0.16.0-rtx3090 v3 usado en Q32; SHA-256 preregistrado `7f2a0086a071ee932c66106e1552d118a85cfec8ddef13c67a54cd64abb39706`; GPU física 1, contexto 32768, KV int8, prefill cuBLAS chunk 2048, DFlash2=7 + LM-head draft + n-gram=15.
- Se preservan perfiles ASTRA, SOL, Flash-Next y PeritoSoft, configuraciones productivas y archivos de modelos. Nunca se borra ni sobrescribe peso alguno.

## Carga y métrica

Misma matriz de Q32: generación nueva con objetivos de 1024, 8192 y 24576 tokens; copia del prompt con objetivos 2048 y 24576; tres repeticiones por celda y perfil; máximo 256 tokens de salida; un warmup excluido. Semillas `prompt=4000` y `orden=32103`; usar las mismas cadenas y el mismo orden en ambos perfiles. Registrar tokens reales (abortar si cualquier entrada supera 30000 o si una pareja difiere más de 1%), tiempo E2E del cliente, TTFT, prefill/decode TPS del servidor sólo cuando exista telemetría por solicitud confiable, arranque, RAM/VRAM, temperatura, errores y OOM.

La señal primaria es la mediana E2E por celda. “≥10% más rápido” requiere mejora en al menos 2/5 celdas emparejadas y cero errores/OOM; informar el arranque por separado y el break-even de requests. Si no se puede obtener telemetría comparable para prefill/decode, registrar `N/D`; no inferirla del claim externo.

## Secuencia, abortos y protección

Antes de cada perfil, verificar el lock Q34, cero inference servers ajenos, cero trabajos CUDA de inferencia, al menos 30 GiB RAM disponible, ≥1 GiB swap y temperatura <80 °C. Ejecutar un solo servidor a la vez. SOL se levanta en un proyecto Docker Compose separado, `BIND_HOST=127.0.0.1`, puerto `18113`, nombre `q34-sol-speed`; el candidato usa sólo GPU1, puerto `18132` y unidad systemd/cgroup Q34. Parar únicamente el contenedor/proceso creado por Q34. Si aparece otro inference server, hay error/OOM, falla el fingerprint, el servicio productivo intenta ocupar el puerto o el modelo no queda listo dentro de 30 min, abortar y guardar el recibo; no repetir sin corregir una causa material.

## Artefactos

Preregistro y plan bajo `artifacts/evaluacion-modelos-llamacode/Q-20261022-VF-ITERATION-34/`; matriz cruda append-only, logs separados por perfil, fingerprints de Compose/modelos/runtime y recibos pre/postflight. Tras la prueba, actualizar `WORK_QUEUE.md`, el documento canónico, la tarjeta Actionables local y el Sheet `Accionables`; leer de vuelta la fila escrita.


## Enmienda preregistrada Q34-A2 · diagnóstico único del arranque SOL

**Motivo material:** el intento 01 cargó el perfil SOL y respondió `/v1/models` tras 232,9 s, pero el warmup de 8 tokens devolvió HTTP 500 (`EngineCore encountered an issue`) antes de cualquier solicitud medida. No hubo OOM ni reinicio de contenedor; se limpió sólo `q34-sol-speed`; el postflight quedó sin servidores de inferencia y sin apps CUDA visibles. El intento 01 queda como fallo de warmup, sin datos comparables.

**Prueba permitida:** un único intento diagnóstico, con el mismo Compose/weights/GPU y un request OpenAI mínimo (`model`, un mensaje “Reply READY”, `max_tokens=8`, `reasoning_effort=medium`), omitiendo los campos de sampling redundantes porque la configuración SOL ya los fija en el servidor. Guardar `docker logs` antes de retirar el contenedor para inspeccionar la causa raíz. Este smoke no es una repetición de la matriz ni cuenta como velocidad.

Si responde correctamente, cambiar sólo el cuerpo del request del perfil SOL para omitir esos overrides redundantes y ejecutar la matriz una vez, con el mismo sampler efectivo del servidor; capturar logs de cualquier error. Si vuelve a fallar, detener el contenedor Q34 y cerrar la comparación directa como bloqueada por fallo del runtime SOL. No hacer tercer arranque ni cambiar el perfil productivo.

## Resultado del diagnóstico único Q34-A2

SOL llegó a `/v1/models` en 141,99 s. La petición mínima, sin overrides de sampling, respondió HTTP 200 en 1,019 s y el contenedor seguía `running` (sin restart ni OOM); usó sus 8 tokens de salida en razonamiento y finalizó `length`, por lo que el smoke confirma salud del endpoint pero no contenido final. El log capturado antes del cleanup no reprodujo el HTTP 500/EngineCore ni un fallo NCCL; sí registra warnings de TritonBundler por cubins ausentes del autotuner estático. Hash del log: `40df0873da0855aa776658d098766c692a22dd1e943ac9003d40f865a39976cd`. Postflight: sin inference servers ajenos ni contenedor propio.

El contraste no demuestra que los overrides hayan causado el primer HTTP 500; prompt y overrides cambiaron juntos. Para resolver la pregunta útil sin repetir el diagnóstico, se preregistra una sola matriz completa en `attempts/direct-sol-speed-02`, omitiendo overrides duplicados únicamente en SOL (el compose ya fija exactamente esos valores). Se conserva el mismo contenido de prompts, orden, límite de salida, perfil y criterios; NInfer sigue recibiendo los parámetros registrados. El runner captura logs SOL antes del cleanup tanto si termina bien como si falla. Cualquier error, desajuste, OOM o gate fallido aborta; no habrá tercer startup de SOL.


## Cierre Q34 · resultado final · 2026-10-22T12:48:13Z

La matriz A3 completó 30/30 requests sin error/OOM y con los 15 pares de prompt-token iguales. El gate directo NInfer-vs-SOL pasa 2/5 celdas por ≥10%; no pasa en generación nueva. NInfer arranca 33,78 s más lento y el break-even simple del workload es ~42,2 requests. Mantener SOL para agentes: la calidad/seguridad Q32 sigue bloqueando adopción. El log del warmup 01 no permitió confirmar su causa; el diagnóstico A2 y cleanup quedaron en receipts. Ver `RESULTS.md` y `receipts/final-summary.json`.
