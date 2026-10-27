# Q152 · Gyro-Coder-L v1.1 vs ASTRA Flash-Next IQ2_XS · BCB-Hard-8

**Estado:** screen habilitado por Q160 y GGUF exacto descargado; tamaño y SHA-256 verificados al 2026-10-27T03:30:33Z. El preflight/servidor/inferencia/screen dual-3090 siguen pendientes. Lock compartido del lote VF: `2242863e-c78e-4fa9-9649-c1d1541f3919`.

## Pregunta de decisión

¿El perfil de coding Qwen3.8 Flash-Next Gyro-Coder-L TQ3_0 v1.1, ejecutado sobre las dos RTX 3090, supera el screen local de coding de ASTRA RCO IQ2_XS y justifica una evaluación más amplia como perfil rápido/especialista?

La tarjeta del publicador reporta 15/16 tareas de coding y 95,5% top-1 en C++, pero son mediciones propias. La versión v1.1 está etiquetada como preview. El screen local no se interpretará como calidad general, seguridad de agentes ni equivalencia de hardware/runtime.

## Artefactos fijados

- Modelo: `agentionai/Qwen3.8-Flash-Next-Gyro-Coder-GGUF`, revisión `87d31357f4cfeb8555cf32fc63a707c5fa10ae7a`.
- Archivo: `Qwen3.8-Flash-Next-Gyro-Coder-L-TQ3_0-v1.1.gguf`, 83.975.624.672 bytes, SHA-256/LFS `377d5aa5b473a89b4d0d0c9fbd54fd8fcc46da19c16fc881860577189c1403df`.
- Runtime: `agentionai/agention-llama:server`, amd64 manifest fijado `sha256:ddcba819dfa58332e408aa734d3cde13572331a57683abd3afb1e0a620f543d6`; las capas OCI declaradas suman 169.900.531 bytes comprimidos. No usar un tag móvil sin comprobar el digest.
- Fuente y fabricante: [tarjeta oficial Gyro-Coder GGUF](https://huggingface.co/agentionai/Qwen3.8-Flash-Next-Gyro-Coder-GGUF). Strata upstream lista Gyro-S/M, pero no Gyro-Coder-L; la tarjeta indica que requiere el build llama.cpp del proveedor.
- Holdout: `artifacts/bigcodebench-hard-ubuntu-8.json`, SHA-256 preregistrado en el runner Q89 como `11279cde14113fc8527f141c53e14cb5ccf0dba65749081a4f914408e391c268`.
- Control: ASTRA RCO IQ2_XS, Q97, BCB-Hard-8 seed 4242, 2/8, mismo fixture y límites de petición. Recibo `Q-20261024-VF-ITERATION-97/runs/astra/bcb8-result.json`.

## Diseño del screen

- Una corrida del candidato, seed 4242, ocho casos completos del mismo BCB-Hard-8; se conserva la referencia ASTRA Q97 como control histórico de la misma cohorte.
- Dos RTX 3090, ejecución serial, sin límites artificiales de RAM o VRAM. Confirmar proceso de inferencia propio usando ambas GPU antes de calificar casos. Si el runtime no puede distribuir el TQ3_0 entre ambas, detener el screen sin fallback de una GPU.
- Contexto 8.192; thinking activado; `max_tokens=6144`; temperatura 0,6; `top_p=0,95`; `top_k=20`; `min_p=0`; repetición 1,0; presencia 0. El servidor debe aceptar el contrato JSON del runner. El candidato no recibe un `reasoning_budget_tokens` no soportado; esta diferencia de perfil se documenta.
- El candidato usa el build llama.cpp del publicador, sin MTP. ASTRA control histórico usa Strata/MTP4. Se comparan perfiles completos, no el efecto aislado de los pesos. Orden: candidato después de confirmar que no quedan otros servidores; el control histórico no se vuelve a correr.
- Puerto loopback reservado para el servidor candidato: `18382`; modelo montado read-only desde D. Imagen fijada por digest; sin privilegios de contenedor y con salida local ligada a loopback.
- El runner Q89 conserva el sandbox de grading sin red. Antes del primer request se comprueban los hashes del fixture, runner y control; registrar timings, score, transporte, contenido final, VRAM/RAM/PSI/swap y cleanup.

## Gates preregistrados

1. **Runtime:** digest correcto, endpoint saludable, dos GPU visibles y asignación del proceso del contenedor en ambas GPU. Si falla, marcar bloqueo técnico; no puntuar.
2. **Screen de calidad:** 8/8 transportes, cero errores de sandbox y cero salidas vacías. Para habilitar fase amplia: candidato ≥4/8 frente a ASTRA 2/8 en Q97. Con menos de 4/8, no hay señal local suficiente para justificar más pruebas de calidad; detener y retirar el archivo candidato.
3. **Fase amplia, sólo si pasa el screen:** preregistrar aparte tres semillas emparejadas para ASTRA y candidato, y un gate de seguridad antes de recomendar integración en agentes. Una sola semilla nunca autoriza promoción.
4. **Velocidad:** reportar E2E total/mediano y prefill/decode sólo si la telemetría es comparable. Para una recomendación de adopción, exigir calidad no inferior en la fase amplia, cero regresiones críticas y ≥15% de mejora E2E en tareas correctas; no convertir TPS de una muestra en afirmación general.

## Reglas de recursos y limpieza

- Preflight actual: no hay servidores de inferencia ni listeners en los puertos inspeccionados; GPU0 1.100 MiB y GPU1 110 MiB usados antes del test. El uso de escritorio en GPU0 no bloquea el screen.
- C tiene 155.461.754.880 bytes libres; D tiene 500.149.567.488 bytes libres. Docker usa `/var/lib/docker` en `/`, con 9.486.487.552 bytes libres; la imagen fijada cabe según el manifiesto remoto, sin podman/skopeo instalado. Model file destino: D, nunca la raíz de Docker.
- No establecer `MemoryMax`, `MemoryHigh` ni `MemorySwapMax`. Registrar RAM, PSI, swap y VRAM. RSS/VRAM altos y swap bajo por sí solos no abortan, dado el historial exitoso de ASTRA 1M y SOL. Sólo detener por salida/crash del servicio, OOM confirmado, PSI global severa sostenida (full ≥60% o some ≥80% durante 15 muestras consecutivas), limpieza insegura o interrupción explícita del usuario.
- No tocar ASTRA, SOL ni archivos/modelos de PeritoSoft. Si Gyro no supera el gate, retirar sólo el GGUF de Q152 y la imagen que se descargó exclusivamente para esta prueba; conservar recibos y resultados.

## Fuentes primarias

- [Tarjeta oficial AgentionAI](https://huggingface.co/agentionai/Qwen3.8-Flash-Next-Gyro-Coder-GGUF): revisión, archivo v1.1, advertencia de preview, configuración Docker y resultados del publicador.
- [Issue de soporte Strata #3640](https://github.com/Niko1221/Strata/issues/3640): confirma ruta manual validada para Gyro-Coder TQ2 en Strata 0.1.47 y que sus 119 tok/s son un smoke de otra variante, no evidencia de TQ3_0 v1.1 ni de este equipo.
- [Catálogo oficial Strata](https://github.com/Niko1221/Strata): Gyro-Coder-L no figura entre los paquetes soportados; no atribuirle soporte Strata.

## Enmienda Q160 · runtime CUDA nativo del proveedor · 2026-10-27

El gate Docker/Vulkan falló en Q158; no se usará para esta prueba. La inspección estática Q159 se corrigió en Q160: `TQ3_0` en el nombre es una clase de tamaño, no un tensor interno requerido. Se usa el fork oficial GitLab de Agention fijado en commit `9aa51ce4fdd3435a91531ffe16a17414ccc6dc6f`.

Se compiló `llama-server` Release con `GGML_CUDA=ON` y arquitectura CUDA 86. La compilación concluyó con exit code 0. Su `--list-devices` detectó ambas RTX 3090 (23,020 y 23,803 MiB libres). Este resultado habilita el siguiente gate, pero no prueba que cargue el archivo ni ejecuta inferencia.

**Enmienda del runtime Q152:** usar el binario local `/media/cristian/Disco local/Models-eval/Q160-agention-llama-build/bin/llama-server`, sin contenedor, y el mismo archivo/revisión/SHA y fixture ya fijados arriba. El servidor usa `--host 127.0.0.1 --port 18382 --ctx-size 8192 --n-gpu-layers 999 --split-mode layer --tensor-split 1,1 --fit on --flash-attn on --jinja --ngram-on-disk --reasoning on`; sampling se envía desde el runner fijo. La tarjeta oficial informa 27,54 GiB de pesos GPU para Gyro-Coder-L y recomienda `--ngram-on-disk` para su tabla de 50,7 GiB. Ejecutar una tarea a la vez y exigir proceso propio en ambas GPUs. Descargar el GGUF a D y comprobar 83,975,624,672 bytes + SHA-256 `377d5aa5b473a89b4d0d0c9fbd54fd8fcc46da19c16fc881860577189c1403df` antes de iniciar el servidor. Mantener las gates de 8/8 transportes, sin error de sandbox ni salida vacía, ≥4/8 para habilitar evaluación amplia; un screen no autoriza adopción. El runner Q89 hace el grading aislado con bubblewrap/seccomp y sin red. ASTRA, SOL y archivos/configuración PeritoSoft no se modifican.

**Enmienda de supervisión previa al server:** el binario recibe `--alias Gyro-Coder-L-Q152`; el runner usa el mismo alias en la solicitud. Antes de lanzar, `scripts/q152_supervise_bcb.py` verifica tamaño/SHA del GGUF, SHA del fixture y runner, GPUs, puerto y ausencia de otro inference server. El script arranca server y runner en grupos de procesos propios, registra logs y muestras JSONL, y termina sólo esos grupos. El gate de readiness es hasta 2.700 s; requiere `/health` y el proceso propio visible en ambas RTX 3090 antes del primer caso. SHA-256 del supervisor: `72acdbb1b68e897f09ca6473b1aa7438ca0bba8ff1ebe5a70aa48e81edcf2ddf`; recibo `receipts/supervisor-preregistration-20261027T025202Z.json`.

**Monitor de recursos de Q152:** muestrear cada segundo MemAvailable, swap, global memory PSI, contadores globales/cgroup de OOM, VRAM y PID/UUID de cómputo. No abortar por RSS, VRAM ocupada, MemAvailable baja aislada o swap usado. Detener sólo por crash/exit del servidor o runner, incremento confirmado de OOM, PSI global full≥60% o some≥80% durante 15 muestras consecutivas, limpieza insegura o interrupción del usuario. Sin MemoryMax/MemoryHigh/MemorySwapMax ni límite artificial. Registrar los archivos de log y cerrar el grupo de procesos del test al terminar.

No se encontraron procesos/listeners/contenedores de PeritoSoft o llama-server al revalidar; no hubo nada que matar. No se limita RAM/VRAM artificialmente.


## Corrección y revalidación del SHA · 2026-10-27T03:34:02Z

El recibo `download-verification-20261027T033033Z.json` conservaba por error una cadena SHA de 61 caracteres. Se preserva como evidencia histórica y esta enmienda la supersede: la API oficial de Hugging Face publica el LFS SHA-256 `377d5aa5b473a89b4d0d0c9fbd54fd8fcc46da19c16fc881860577189c1403df` (64 hex); el archivo local se volvió a leer completo con `hashlib.sha256` y `sha256sum`, ambos coinciden, tamaño 83975624672 B. No se cambió el modelo, revisión, runtime ni protocolo. Recibo: `artifacts/evaluacion-modelos-llamacode/Q-20261026-VF-ITERATION-152/receipts/model-sha256-correction-20261027T033402Z.json`.
