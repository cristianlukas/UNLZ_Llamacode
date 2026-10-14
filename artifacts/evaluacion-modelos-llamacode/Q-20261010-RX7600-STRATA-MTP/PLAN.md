# Evaluación del post RX 7600 / Strata gfx1102 / Qwen3.6 MTP

- **ID:** `Q-20261010-RX7600-STRATA-MTP`
- **Estado:** completada el 2026-10-13 bajo lock `b133271c-32f9-4191-974d-2256e5118f6b`; auditoría documental, sin inferencia ni descarga.
- **Objetivo:** evaluar si el post aporta evidencia transferible a modelos/perfiles/harness de LlamaCode y si merece una prueba local no redundante.
- **Fuente encontrada:** [post r/LocalLLaMA sobre RX 7600](https://www.reddit.com/r/LocalLLaMA/comments/1wynz8o/rx_7600_8_gb_on_linux_qwen38flashnext_125b_at_24/), publicado según el índice el 5 de octubre de 2026; describe Strata 0.1.39/IQ2_XS en RX 7600 8 GB con un parche gfx1102 y, en una prueba aparte, Qwen3.6-35B-A3B Q6_K_XL en llama.cpp con/sin MTP.

## Claims recibidos para verificar

1. Strata 0.1.39 puede ejecutarse en AMD gfx1102 tras un parche comunitario; RX 7600, 64 GiB RAM, contexto 32K, IQ2_XS; 24 tok/s decode y 59,1 tok/s prompt con una tabla hipBLASLt ajustada.
2. Aumentar `--vram-reserve-mib` a 2048–2560 MiB estabiliza una sesión de escritorio que comparte la RX 7600; el autor relata tres bloqueos previos de GNOME.
3. Qwen3.6-35B-A3B Q6_K_XL en llama.cpp: 151 tok/s de prefill a 4K; 23,6 tok/s decode sin MTP y 32,0 tok/s con MTP2, aceptación de drafts 98%; medición de tres respuestas greedy de 320 tokens.
4. En el fork de Strata, el port gfx1102 y la integración experimental de Qwen3.6 aparecen en PRs separados. No asumir que el post ejecutó Qwen3.6 en Strata ni que el cambio de una PR ya se integró a upstream.

## Hipótesis, controles y alcance

- La señal de soporte gfx1102 interesa a usuarios con Radeon de 8 GB; no se puede reproducir en las RTX 3090 del host y no justifica inferir ventaja local para CUDA.
- La comparación MTP vs no-MTP es una hipótesis de rendimiento para Qwen3.6; el claim de 32 tok/s no demuestra mejor calidad ni transferencia al harness.
- Primero se auditarán PRs, fuentes oficiales, configuración y recibos locales. Se inventariarán, sin cargar ni descargar, los pesos/builds existentes de Qwen3.6-35B-A3B MTP y el perfil llama.cpp de control sin MTP. Se revisará el historial para no repetir una huella ya medida.
- **Candidatos provisionales:** Qwen3.6-35B-A3B GGUF Q6_K_XL con MTP2 de llama.cpp, si existe localmente; control del mismo checkpoint/quant y runtime sin MTP, sólo si hay una configuración técnicamente equivalente. **Control adicional contextual:** los resultados existentes de QWEN35-A3B AutoRound/vLLM y otros perfiles disponibles se usarán como evidencia histórica, no como brazo A/B si cambian pesos/runtime.
- La ruta Strata gfx1102/IQ2_XS se considerará sólo documental en este host salvo que se encuentre hardware AMD gfx1102 local, cosa que no se presupone.

## Plan de pruebas condicional

1. Fijar URL, commits/PRs y contenido del post; separar afirmaciones de benchmark, compatibilidad y estabilidad.
2. Inventariar peso, quant, MTP head, runtime/build, comandos, hardware y recibos existentes. Confirmar hashes y detectar fingerprints previos antes de ejecutar.
3. No descargar pesos ni alterar perfiles productivos. Si no hay control/candidato exactos o build compatible, cerrar como auditoría documental con el bloqueo concreto.
4. Si existe un A/B MTP/no-MTP comparable, registrar un preflight de memoria/VRAM/GPU y el fingerprint efectivo antes de iniciar. Usar primero smoke con varios requests y verificación de salida; después, calidad coding con verificadores independientes (HE0→HE20→BCB8, ADV o TaskFlow sólo si la decisión los requiere) y rendimiento en una medición separada. Para speed, igualar prompts, 320 tokens y estrategia greedy del post como una sonda aparte; reportar TTFT/prefill/decode/latencia y aceptación MTP sin mezclar con calidad.
5. Screening inicial; para recomendar mejora estable, exigir tres pares válidos, seeds/tareas alineadas, misma build, modelo, cuantización y hardware salvo la variable MTP. Si sólo se pueden comparar perfiles completos, etiquetar el resultado así.
6. No promover cambios de perfil, HarnessSpec ni defaults a partir del post o de una sonda aislada. No inferir Computer Usage E2E, visión, voz ni contexto efectivo.

## Guardas de recursos

- Lock exclusivo vigente: `WORK_QUEUE.lock`, token `b133271c-32f9-4191-974d-2256e5118f6b`.
- No GPU/inferencia hasta cerrar la auditoría documental, identificar candidatos y controles exactos, comprobar procesos/VRAM/RAM/swap y crear un recibo preflight.
- Si se necesita GPU, ejecutar perfiles secuencialmente; no detener procesos ajenos. Servidores aislados en loopback y limpieza sólo de procesos propios.
- En Linux, sampling conservador por defecto (`temp .6`, `top-p .95`, `top-k 20`, `min-p 0`, repeat penalty 1, presence 0), salvo una sonda de velocidad que replica explícitamente el post (greedy); los dos protocolos quedarán separados.

## Resultado esperado antes de cerrar

Informe con claims verificados/no verificados, evidencia primaria enlazada, estado de pesos/builds y una decisión explícita: ejecutar A/B compatible, documentar transferencia parcial, o cerrar bloqueado/no evaluable por falta de hardware/modelo/control. Guardar recibos, hashes, limitaciones y actualizar el documento canónico y la cola.

## Cierre

- Se documentaron claims y limitaciones en `RESULTS.md`; el preflight local está en `receipts/local-preflight.json`.
- El post separa Qwen3.8/Strata y Qwen3.6/llama.cpp. El Qwen3.6 Q6_K_XL GGUF y RX 7600 gfx1102 no están disponibles localmente. El checkout llama-mtp revisado sólo contiene un servidor Windows antiguo.
- Ya existe un par local MTP3/no-MTP de Qwen3.6 en NInfer/RTX 3090 (+19,05% TG), pero es otra cuantización/runtime/perfil. No se repitió una huella existente ni se presentó como réplica.
- PR #1000 (gfx1102 8 GB) y PR #824 (engine Qwen3.6 separado) cerraron al reescribirse el historial de `main`, sin rechazo según el mantenedor. La compatibilidad Qwen3.6 del engine principal continúa como propuesta abierta en PR #1402. No se cambió producción.
- Próxima acción para medir la receta del post: disponer de RX 7600/gfx1102, GGUF Q6_K_XL con MTP y build Linux llama.cpp fijada; comparar MTP on/off para velocidad y, por separado, correr calidad de agente con verificadores independientes.
