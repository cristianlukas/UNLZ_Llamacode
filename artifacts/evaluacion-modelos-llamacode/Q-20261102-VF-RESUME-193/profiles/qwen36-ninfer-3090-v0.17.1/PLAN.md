# Q193 — Qwen3.6-35B-A3B · NInfer-3090 v0.17.1 Linux · pipeline dual

**Estado inicial:** preregistrado; aún sin descargar el runtime ni ejecutar inferencia. El tercer artefacto DeepSeek FP8 Engram incompleto que aparecía en una captura ya fue retirado en Q190/Q192; no forma parte de esta prueba.

## Pregunta de decisión

¿El runtime distinto NInfer-3090 v0.17.1 Linux puede ejecutar el mismo artefacto Qwen3.6-35B-A3B ya evaluado en Q190, en pipeline `--devices 0,1` sobre las dos RTX 3090, y ofrecer una alternativa de throughput/Q172 que justifique conservar el perfil? No volver a descargar el modelo ni mezclarlo con los resultados Q190 de NInfer-all v3, llama.cpp, otro quant o otra revisión.

El valor de la prueba es resolver el soporte local de pipeline en dos dispositivos distintos: el README de v0.17.1 documenta `--devices 0,1` y resultados de pipeline, pero también marca el engine de contexto actual con dispositivos distintos como no verificado. Por eso el primer gate es un smoke mínimo de carga y respuesta dual; no se salta al ladder si falla.

## Preregistro de runtime y pesos

- Runtime fijado: `ashalliants/ninfer-3090`, release `v0.17.1-rtx3090`, Linux x86-64, archive `ninfer-rtx3090-linux-x64-0.17.1-rtx3090.tar.gz`, 1,048,862,833 bytes, SHA-256 `2f469d9171fa9a1e6fca1de85f6a5d5cfb7326302f69a0561dcd9ef81415febb`.
- El archive descargado se conserva en HDD extra; la expansión de 2,356,558,649 B se hace junto al modelo en Disco local D, como recomienda el README, para evitar el acceso lento al HDD durante arranque. D tiene 87,414,194,176 B libres antes de la expansión, conserva el piso preregistrado de 10 GB y no se duplica ningún peso del modelo.
- Pesos: `qwen3_6_35b_a3b.ninfer`, v3, ruta `/media/cristian/Disco local/Modelos-eval/Qwen3.6-35B-A3B-NInfer-all-20261101/qwen3_6_35b_a3b.ninfer`, tamaño esperado 22,790,484,480 bytes, SHA-256 esperado `3e33297645dc33557751be1a3c407a74ed7c00f34909b5d4e8cfdce91b3dbe84` (confirmado en Q190). El archivo parcial antiguo de 124,428,288 bytes queda excluido y no se sobrescribe.
- Perfil: Linux nativo, CUDA 12.8, SM86, **2× RTX 3090** por pipeline de etapas `--devices 0,1`; no llamarlo tensor parallel. La configuración base sigue el launcher Qwen3.6 del release (KV `rk4v4`, MTP3 + draft head, visión activa, prefill cuBLAS chunk 4096); se fijará a una solicitud para la ladder/Q172. Toda desviación para hacer el smoke seguro se anotará antes del primer request y se conservará idéntica en Q173 y Q172.
- **Aclaración de lanzamiento, preregistrada antes de GPU (2026-11-02T02:35:44Z):** `run.sh qwen36-35b-a3b` no expone `--devices`; el launcher rechaza `NINFER_DEVICES` porque esa variable es específica del perfil Flash-Next. La ayuda del `ninfer-serve` 0.17.1 sí ofrece `--devices N,M,...`. Para poder probar Qwen3.6 dual sin cambiar el wrapper ni reutilizar un perfil Flash-Next, Q193 lanzará directamente `ninfer-serve` con los argumentos de abajo. La limitación upstream sobre pipeline en dos dispositivos distintos permanece explícita y el smoke es una compuerta de parada.
- **Args exactos del smoke 8K y base Q173/Q172:** `ninfer-serve <modelo> --host 127.0.0.1 --port 18503 --devices 0,1 --max-concurrency 1 --max-context <contexto> --kv-capacity <contexto> --kv-dtype rk4v4 --spec mtp --draft-tokens 3 --lm-head-draft --mtp-experts-q4 --gdn-state-fp16 --prefill-cublas --prefill-chunk 4096 --vision --vision-residency overlay --host-context-mib 8192 --min-p 0.03 --presence-penalty 0.5`. En el smoke, `<contexto>=8192`; en Q173 se sustituye por cada nivel preregistrado, incluido 261888 como máximo. No se pasan `--stage-layers`, `--fit-context` ni el env `NINFER_DEVICES`; el particionado por defecto del motor se valida en logs antes de seguir.
- Request smoke: Chat Completions a `127.0.0.1:18503`, prompt `Respond exactly PONG and nothing else.`, `temperature=0`, `max_tokens=16`. Aprobar sólo si la salida es válida/no vacía, el log demuestra stages en GPU0 y GPU1 y ambas tarjetas muestran uso de compute por este PID. Fallar/parar si una GPU no recibe etapas, hay error, salida vacía, OOM/Xid o CUDA fault.
- Puerto reservado de evaluación: `127.0.0.1:18503`.
- Comparador local: Q190 NInfer-all v3 con los mismos pesos — Q173 media P/D 5155.87/230.02 tok/s y cold/hot 46.776/44.597 s; Q172 seeds 73/70/79, media 74/100, safety FAIL 3/3. Es una comparación entre engines y perfiles distintos, no un reemplazo retroactivo de esos datos.

## Secuencia y métricas preregistradas

1. Verificar lock Q193, ningún inference server/puerto en conflicto, GPU0+GPU1 visibles, ASUS quarantine 1636/1636, P2P bidireccional, `gpu_unlock` en ambas tarjetas, al menos 32 GiB `MemAvailable`, al menos 10 GB libres en D, 20 GB en HDD y 2 GB en `/`. Confirmar artefacto por tamaño/SHA. Si cualquier gate falla, detener antes de inferencia.
2. Descargar el archive oficial sólo después del preregistro; comprobar el SHA publicado. Extraer en HDD, comprobar `ninfer-serve --version/--help`, `run.sh --help`, `ldd` sin dependencias faltantes. No compilar ni instalar paquetes del sistema.
3. **Smoke dual de parada:** iniciar el comando directo preregistrado arriba con contexto/capacidad 8192; enviar el request determinista preregistrado; confirmar salida no vacía, logs de asignación de etapas a GPU0 y GPU1, memoria/utilización en ambas, proceso sólo en el puerto 18503 y ausencia de Xid/OOM/fault. Apagar sólo el proceso Q193. Si falla, registrar evidencia y detener; no repetir en una GPU.
4. Sólo si smoke PASS: medir cold/hot y ejecutar Q173 ladder 8192 (3 repeticiones), 32768, 65536, 131072 y 261888 (1 cada uno), con 128 tokens de salida exactos, serial, sin 523K. Calcular medias por nivel y media equiponderada de niveles. Registrar TTFT, decode, tokens reales, errores y ambas GPUs. Actualizar la pestaña Resultados y Modelos locales por peso después de cada hito válido; leer cada rango de vuelta antes de continuar.
5. Sólo al cerrar Q173: Q172 Tool-Eval Hard Mode 2.8.0, seeds 42/43/44 seriales, 28 escenarios, timeout 120 s, `fail_on_safety`; publicar cada semilla y actualizar Accionables / Modelos locales por peso tras cada una. Comparar seguridad por separado del score.
6. No borrar ni sobrescribir el modelo por este experimento. Sólo proponer retiro si una comparación válida demuestra dominancia simultánea en prefill, decode y Q172 y no hay consumidor PeritoSoft; si no, preservar los archivos y reportar la decisión.

## Criterios de parada

Detener ante lock cambiado, servidor ajeno, falta de una GPU, gates de arranque no verdes, fingerprint incorrecto, `MemAvailable` <32 GiB, pisos de disco incumplidos, GPU no usada, salida vacía/incorrecta, tokens fuera del conteo pedido, OOM/Xid/CUDA/runtime fault, o resultados no persistidos. No matar procesos ajenos ni la GUI; detener sólo el servidor Q193 iniciado por esta evaluación.

## Fuentes primarias

- Release Linux y versión/verificación: https://github.com/ashalliants/ninfer-3090/releases/tag/v0.17.1-rtx3090
- README fijado a `v0.17.1-rtx3090`: https://raw.githubusercontent.com/ashalliants/ninfer-3090/v0.17.1-rtx3090/README.md
- Modelo y fingerprint Q190: `artifacts/evaluacion-modelos-llamacode/Q-20261029-VF-ITERATION-190/profiles/qwen36-ninfer-all-v3/PLAN.md` y `receipts/hf-artifact-verified.json`.
