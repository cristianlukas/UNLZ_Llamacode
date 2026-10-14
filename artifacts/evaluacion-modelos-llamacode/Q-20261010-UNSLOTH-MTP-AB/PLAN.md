# A/B de MTP Unsloth Qwen3.8-Flash-Next en llama.cpp

- **ID:** `Q-20261010-UNSLOTH-MTP-AB`
- **Lock:** `f4a83150-c79c-42fb-8667-47b04110bd76`, inicio 2026-10-13T04:03:51Z.
- **Objetivo:** medir si el nuevo sidecar MTP de Unsloth acelera el mismo Flash-Next en llama.cpp, y comprobar aceptación, calidad, memoria y utilidad para coding/agentes.
- **Producción:** no modificar perfiles productivos, defaults ni HarnessSpec. Todo server y perfil de prueba queda aislado.

## Hipótesis y fuentes

El PR upstream [#29761](https://github.com/ggml-org/llama.cpp/pull/29761) publica para DGX Spark una señal de 1,55× decode y 64,0% de aceptación con Qwen3.8-Flash-Next IQ4_XS y MTP draft n-max 3, en 24 solicitudes breves. El PR anterior [#28243](https://github.com/ggml-org/llama.cpp/pull/28243) fue cerrado como supersedido por #29761; sus claims no son resultado de mainline. Un comentario del 12 de octubre en #28243 reporta una diferencia grande entre ambas implementaciones, pero usa parámetros distintos, un prompt de 23.535 tokens y dos 3090; se registra como hipótesis, no como resultado reproducido.

La carpeta oficial [Unsloth MTP](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/tree/main/MTP) incluye sidecars `shared-*` y autocontenidos. Para el build local se propone el Q8_0 **autocontenido**, revision `efc50b7c3195a10eebd8d3e32f83b27b2aeb239d`, tamaño publicado aproximado de 4,14 GB y SHA-256 `58a47d6a216307e9b97172d5bfdc3436a8994b632f5e436b9bb6edf8951da8d1`. No usar la variante `shared-` en este A/B.

## Candidato y control

- **Control:** Unsloth `Qwen3.8-Flash-Next UD-Q4_K_XL`, revision `38bb39ee97821de2c9009abb7e93950eec396e66`, exactamente los cuatro shards locales del screening Q4; hashes y tamaños están en `../Q-20261010-FLASHNEXT-Q4-P100-POST/receipts/manifest.json`. Recalcular/verificar antes de abrir el server.
- **Candidato:** mismos cuatro shards, runtime, parámetros y suite, más `MTP/mtp-Qwen3.8-Flash-Next-Q8_0.gguf` autocontenido. Añadir sólo `--model-draft`/`--spec-type draft-mtp` y `--spec-draft-n-max 3`.
- **Runtime inicial:** llama.cpp b11115, commit `d5f66492e661b63e6c74822c2b72f5146053994e`, build CUDA local ya existente. Confirmar que la ruta Qwen4Exp/MTP está compilada; si no puede cargar el sidecar por una limitación de rama, no parchear el build silenciosamente: registrar el error y evaluar una build aislada del commit publicado que corresponda.
- **SOL:** ya descargado según el inventario; no descargarlo. No se usa como control de este A/B porque es otro modelo y backend. Sus comparaciones históricas se conservan como referencia contextual, no como control MTP.

## Protocolo preregistrado

1. Recalcular SHA-256 de los shards Q4 locales; descargar sólo el sidecar si no existe una copia compatible. Fijar repo revision, SHA-256, ruta y tamaño. Guardar logs, config, hashes y límites de memoria.
2. Ejecutar smoke control/MTP con `-np 1`, contexto 32K, KV Q8 y salida de hasta 256 tokens. Verificar transporte normal, `draft acceptance` en el brazo MTP y ausencia de errores de carga/OOM.
3. **Velocidad:** 3 pares intercalados off/on, mismo prompt fijo de 23.535 tokens referido en PR #28243 (si el archivo local de `qwen4exp.cpp` no permite reproducir ese conteo, generar un fixture fijo y hashearlo antes de ambos brazos), 256 tokens de salida, mismo sampling y seed por par. Capturar prefill tok/s, decode tok/s, TTFT, tiempo total, aceptación, VRAM/RAM/swap y temperatura/potencia disponibles.
4. **Calidad de coding:** screening emparejado, primero HE0; avanzar HE20→BCB8 sólo según sus gates. Ejecutar TaskFlow ULTRA con el mismo prompt/HarnessSpec y hasta tres reparaciones por brazo. Conservar primera pasada, cada reparación, tool calls y verificadores. Parar una etapa sólo por el gate definido o por infraestructura.
5. **Tool-use complementario:** si el adaptador local soporta la suite y termina sin alterar mensajes/prompts, correr las mismas 28 tareas Hard Mode × semillas 42/43/44 para ambos brazos, en serie. Si no, registrar el motivo y no sustituirlo por una suite de distinto protocolo.
6. Sólo considerar una mejora estable si los 3 pares de velocidad son válidos y la calidad no cae; la corrida de coding es screening, por lo que no justifica promover perfil ni default.

## Hardware, recursos y abortos

- Dos RTX 3090 de 24 GiB; inventario de memoria, procesos GPU, RAM, swap, puertos y espacio se actualiza justo antes de descargar/cargar.
- Base Q4 existente en `/media/cristian/Disco local/Strata-UD-Q4-review-20261003/models/unsloth-UD-Q4_K_XL/`; el sidecar (4,14 GB) se alojará aislado en el pool local de modelos si no está disponible.
- Preflight actual: `MemAvailable` 113 GiB, swap usado 3,3 GiB; almacenamiento con 106 GiB libres en `Disco local` y 167 GiB en el volumen de modelos. No iniciar si `MemAvailable < 40 GiB`, si swap crece más de 1 GiB durante carga, si hay otro trabajo GPU activo, si una GPU no deja margen de ejecución o si falla un hash. No alterar swap ni detener procesos ajenos.
- Ejecutar brazos en serie sobre las mismas GPUs. Liberar sólo los servidores de esta tarea y comprobar puertos/GPU al terminar.

## Resultado provisional de la investigación previa al plan

El build b11115 local expone `--spec-type draft-mtp` y contiene la arquitectura Qwen4Exp, pero no se inició inferencia. Los hashes de los shards Q4 están en el recibo histórico y se volverán a calcular antes de usarlos. La MTP autocontenida no está aún en el inventario local; su SHA se verificó en la ficha Xet oficial de Hugging Face. No descargar SOL ni modificar perfiles productivos.


## Revisión preregistrada antes de descargar/cargar

El binario b11115 inicialmente propuesto expone `draft-mtp`, pero su `src/models/qwen4exp.cpp` local no implementa `LLM_GRAPH_TYPE_DECODER_MTP`; no sirve para este A/B. Se sustituye por el build CUDA ya existente de llama.cpp `0.5.0-dev`, commit `836d57176dc699a726c55418e4f96b8ca628e1bf` (03-10-2026), en `/media/cristian/Disco local/LlamaCode-cache/llama.cpp-spark-native-20261003/build-cuda/bin/llama-server`. Su fuente limpia en `/home/cristian/.cache/llamacode/llama.cpp-spark-native-20261003` incluye la cabeza MTP autocontenida de Qwen4Exp y el binario anuncia `draft-mtp`; no requiere build ni parche. Control y candidato usarán exactamente este binario. Esta comparación aplica a ese perfil completo de llama.cpp, no a Strata ni a un perfil productivo LlamaCode.

Se verificaron de nuevo tamaño y SHA-256 de los cuatro shards base Q4: todos coinciden con `../Q-20261010-FLASHNEXT-Q4-P100-POST/receipts/manifest.json` (111,334,654,784 bytes). La búsqueda dirigida no encontró el sidecar MTP en el pool local. Hay 167 GiB libres en el volumen de modelos para descargar el sidecar de ~4.14 GB; el modelo SOL queda intacto y no se descarga.

Configuración de carga de ambos brazos: dos RTX 3090, `--split-mode layer --tensor-split 1,1 --n-gpu-layers all --n-cpu-moe 40`, contexto 32768, KV Q8_0, un slot, `--flash-attn on`; mismos batch/ubatch, plantilla, sampling, seed y tareas. El candidato agrega sólo el sidecar Q8_0 autocontenido, `--spec-type draft-mtp` y `--spec-draft-n-max 3`. Antes de la primera carga se volverán a comprobar GPU, RAM, swap, procesos y puertos; durante carga se aborta el brazo si swap crece más de 1 GiB sobre la base o aparece OOM/otro proceso GPU.

El build 836d571 tiene fecha 2026-10-03, posterior a la fusión upstream de #29761 del 2026-10-01; su árbol local contiene el grafo Qwen4Exp MTP y reconoce el formato MTP autocontenido. El historial local no permite atribuir ese grafo a un cherry-pick exacto de #29761, así que el resultado se atribuirá al binario/fingerprint 836d571 y no se describirá como réplica exacta del benchmark del PR. La validez depende de que el smoke cargue el sidecar, produzca aceptación y preserve transporte.

## Addendum de cierre — 2026-10-13

El usuario fijó como corte práctico de interés 30 minutos por corrida. Las seis corridas Hard Mode válidas excedieron ese límite (MTP-on 37:54–41:19; MTP-off 44:33–46:21), por lo que se detuvo el brazo MTP-off BCB8 después de 2/8 tareas y no se ejecutó TaskFlow ULTRA. Se conservaron el receipt cancelado, eventos y archivos parciales; no se asigna score a ese BCB8. Se cierra la campaña sin promoción ni cambios productivos. Informe y recibos en RESULTS.md.
