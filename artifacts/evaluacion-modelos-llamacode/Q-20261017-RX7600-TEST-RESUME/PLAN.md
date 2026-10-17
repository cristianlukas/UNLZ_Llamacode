# Plan — Q-20261017-RX7600-TEST-RESUME

## Objetivo

A pedido del usuario, verificar si hoy existe en este host una ruta ejecutable para cerrar las pruebas que la evaluación `Q-20261010-RX7600-STRATA-MTP` dejó condicionales. No tratar un perfil distinto como réplica del post. Actualizar el documento canónico y cerrar con resultado reproducible o bloqueo concreto.

## Candidato y control prerregistrados

- A/B del post: Qwen3.6-35B-A3B GGUF Q6_K_XL con cabeza MTP, `llama.cpp` Linux fijado, MTP off vs `draft-mtp` MTP on, mismos pesos, quant, build, prompts greedy de 320 tokens, hardware RX 7600 8 GB gfx1102. La prueba de Strata Qwen3.8 IQ2_XS es distinta y sólo puede afirmarse si esos pesos/build y la GPU existen localmente.
- Las RTX 3090, AutoRound/vLLM, NInfer histórico y Qwen3.8 Flash-Next no cuentan como control equivalente para el claim Q6/RX7600. Se reutiliza su evidencia, sin repetir fingerprints ni ejecutar otro modelo por sustitución.

## Puertas antes de inferencia

1. Inventario de `lspci`, `rocminfo`, `nvidia-smi`, paths registrados y archivos exactos; leer hashes/manifiestos; detectar binario Linux y commit de llama.cpp. No descargar ni reconstruir.
2. Si falta cualquiera de RX7600/gfx1102, GGUF+MTP exactos o runtime Linux fijado, detener sin inferencia y registrar qué falta.
3. Si todos existen: verificar GPU/RAM/swap/PSI/procesos/puertos y huellas exactas antes de carga. Ejecutar secuencialmente smoke off/on; luego rendimiento greedy en 3 pares válidos, tres prompts iguales por brazo y 320 tokens; registrar TTFT/prefill/decode y aceptación MTP. No mezclar con calidad.
4. Si el smoke completa y la calidad puede medirse dentro del presupuesto: HE0→HE20→BCB8 para ambos brazos con la misma suite/seed y verificadores, más un screen TaskFlow ULTRA por brazo. No declarar mejora estable con menos de 3 pares válidos; no promover un perfil. CU, audio, visión y contexto sólo se consideran si el candidato/runtime expone esa modalidad y hay fixtures/protocolo adecuados.
5. No alterar swap, detener procesos ajenos, cambiar perfiles productivos, instalar software ni descargar modelos.

## Rama complementaria para medir transferencia local

Registrada antes de inferencia a pedido del usuario, porque el inventario halló
el checkpoint local Qwen3.6-35B-A3B AutoRound INT4 y sus pesos MTP, aunque no el
RX7600/GGUF Q6 del post. Esta rama no reemplaza la prueba original ni se
comparará numéricamente con sus 23,6/32,0 tok/s.

- Control: mismo checkpoint AutoRound INT4 local, servido por vLLM con MTP
  desactivado.
- Candidato: mismos bytes, quant, build vLLM, GPUs, prompt y sampling; MTP de
  Qwen activado con método `qwen3_next_mtp` y dos tokens especulativos, según la
  configuración del model card oficial. Sólo cambia MTP.
- Hardware/runtime objetivo: dual RTX 3090, imagen local
  `vllm/vllm-openai:v0.27.1`, contexto 32K; sin descargas ni instalaciones.
- El model card oficial de Qwen3.6 recomienda vLLM ≥0.19 y MTP con
  `qwen3_next_mtp`, dos tokens; la imagen disponible es v0.27.1 y su código
  registra ese método. Checkpoint, configuración, argumentos, pesos y modo
  offline se guardan antes de iniciar el servidor.
- Si el parser/runtime de esa imagen no acepta Qwen3.6 MTP o el modelo no inicia,
  detener el experimento y registrar el fallo de compatibilidad sin score.
- Si inicia, correr velocidad greedy de 320 tokens con el mismo prompt 4K, tres
  pares válidos por condición en orden AB/BA alternado. Guardar TTFT, prefill,
  decode, acceptance y fingerprints efectivos. Una diferencia sólo describe
  esta receta vLLM/AutoRound/3090.
- Tras un smoke funcional, hacer una pasada exploratoria por brazo en HE0→HE20→
  BCB8 y una TaskFlow ULTRA por brazo, con los mismos seeds/tareas y gates. Es un
  screen; sin tres corridas completas por condición no se afirmará estabilidad
  ni se promoverá. No iniciar CU/audio/visión en esta rama de MTP-coding.
- Aplicar guardas antes de cada carga: MemAvailable ≥40 GiB, OOM sin aumentos,
  PSI bajo, ambas GPUs sin procesos compute ajenos y puertos dedicados libres.
  SwapFree es telemetría, conforme a la reanudación previa pedida por el usuario;
  detener sólo los contenedores de esta tarea si MemAvailable <20 GiB durante
  15 muestras, PSI `some avg10` ≥80 o `full avg10` ≥60 durante 15 muestras,
  aumenta `oom_kill`, entra otro proceso CUDA o cambia el fingerprint.

Fuente técnica para esta configuración: [model card oficial Qwen3.6-35B-A3B]
(https://huggingface.co/Qwen/Qwen3.6-35B-A3B), sección vLLM/MTP.

## Registro de coordinación

Al inicio no había `WORK_QUEUE.lock` ni filas Pendiente/Activa. Cuatro filas estaban Bloqueadas con condiciones propias; este follow-up se agregó al final bajo lock exclusivo. La cola es manual y no dispara tareas automáticamente.

## Cierre de ejecución (2026-10-17)

La rama RX7600/Q6/llama.cpp quedó bloqueada por hardware y artefactos ausentes. La rama complementaria AutoRound/vLLM se ejecutó parcialmente: MTP-off dejó una muestra válida de velocidad; MTP-on cargó y pasó warmup, pero no se envió el prompt A porque apareció el proceso CUDA ajeno `wordcraft`. Se detuvo sólo el contenedor propio. No se ejecutaron coding/agentes ni otras modalidades, no se cambió producto y no se declara mejora. Ver `RESULTS.md` y `receipts/postflight-close.json`.

Reanudar el A/B complementario con ambas GPU libres, conservando off-A y midiendo on-A; completar los tres pares. La reproducción exacta del post requiere RX 7600/gfx1102, GGUF Q6_K_XL+MTP y llama.cpp Linux fijado.
