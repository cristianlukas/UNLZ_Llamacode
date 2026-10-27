# Q160 · corregir gate de formato y reabrir Q152 por el CUDA oficial

**Estado actualizado:** fuente fijada y validada, build CUDA `llama-server` completado, y enumeración detecta ambas RTX 3090. No se descargó el modelo ni se inició un servidor HTTP/inferencia. La enmienda Q152 queda habilitada para descargar el GGUF exacto y continuar el screen. Lock paraguas Q146: `2242863e-c78e-4fa9-9649-c1d1541f3919`.

## Por qué se reabre

La comprobación Q159 interpretó `TQ3_0` del nombre del GGUF como un tipo interno requerido. La tarjeta del publicador aclara que `TQ2_0`/`TQ3_0` son clases de tamaño para Hub; el archivo Gyro real usa tipos internos `TQ2_T`, `TQK6`, `TQK7` y `TQP5–TQP7`. También indica que se necesita el fork Agention, no llama.cpp stock. La fuente oficial es el GitLab `agentionai-group/llama.cpp`, no el mirror GitHub que se había inspeccionado en Q159.

Inspección pública de `main` en GitLab devolvió commit `9aa51ce4fdd3435a91531ffe16a17414ccc6dc6f`. El checkout real contiene `qwen4exp` y rutas CUDA para los tipos Gyro enumerados. Se compiló `llama-server` en Release con CUDA y `CMAKE_CUDA_ARCHITECTURES=86`; el build finalizó con exit code 0. `--list-devices` enumeró `CUDA0` y `CUDA1`, ambas NVIDIA GeForce RTX 3090. La advertencia HTTPS de OpenSSL ausente no afecta el servicio local; los assets de UI se descargaron y verificaron durante el build. El archivo exacto v1.1 de Q152 seguía respondiendo HEAD 200 en la revisión HF fijada y su longitud coincide con el prerregistro.

## Alcance de esta iteración

1. Volver a leer instrucciones y confirmar lock Q146 propio.
2. Revalidar que no haya procesos/puertos/contenedores de inferencia y espacio suficiente en D. Buscar el artefacto candidato por nombre/hash antes de descargarlo.
3. Clonar superficialmente y fijar el commit GitLab indicado. Confirmar en el checkout `qwen4exp`, `TQ2_T`, `TQK6`, `TQK7`, `TQP5`, `TQP6`, `TQP7` y rutas CUDA. Si falla una condición, parar antes del build.
4. Compilar sólo `llama-server` con backend CUDA para SM86, sobre D (no sobre `/`), y ejecutar únicamente `--list-devices`. Ningún modelo ni servidor HTTP se iniciará en Q160.
5. Gate satisfecho: habilitar Q152 mediante la enmienda adjunta. Descargar a D la revisión/archivo exactos ya fijados, verificar tamaño y SHA-256 antes de cargar, probar carga/health request serial con el modelo montado read-only, y exigir compute del proceso propio en ambas GPU. Sin fallback single-GPU/CPU.

## Resultado del gate de runtime

- Fuente: `https://gitlab.com/agentionai-group/llama.cpp`, commit `9aa51ce4fdd3435a91531ffe16a17414ccc6dc6f`.
- Build: `cmake -S <source> -B <build> -DGGML_CUDA=ON -DCMAKE_CUDA_ARCHITECTURES=86 -DCMAKE_BUILD_TYPE=Release`; `cmake --build <build> --target llama-server --parallel 16`; ambos completaron correctamente.
- Device gate: `llama-server --list-devices` mostró `CUDA0` (RTX 3090, 23,020 MiB libres) y `CUDA1` (RTX 3090, 23,803 MiB libres).
- Memoria durante build: 101 GiB disponibles; PSI `some/full avg10=0.00`; sin límites artificiales. D quedó con 495,309,963,264 B libres.
- Procesos objetivo PeritoSoft/llama-server: ninguno. No se envió señal ni se tocó ArtCraft/Codex.
- Advertencia de compilación: `src/models/qwen4exp.cpp:563` tiene un formato `fprintf` `%d` para `long int`; el build la toleró y el binario se generó. Se registra como aviso del proveedor, no se cambia este fork.
- Recibos: `receipts/source-build.json`, `receipts/device-enumeration.json`, `receipts/peritosoft-process-check.json`; salida resumida en `RESULTS.md`.

## Ruta y configuración propuesta

- Repo: `https://gitlab.com/agentionai-group/llama.cpp`; commit fijo `9aa51ce4fdd3435a91531ffe16a17414ccc6dc6f`.
- CUDA local: toolkit reportado 12.0; arquitectura `86` (RTX 3090), `GGML_CUDA=ON`; build/checkout en D.
- Candidato Q152 sin cambios: HF repo `agentionai/Qwen3.8-Flash-Next-Gyro-Coder-GGUF`, revision `87d31357f4cfeb8555cf32fc63a707c5fa10ae7a`, archivo `Qwen3.8-Flash-Next-Gyro-Coder-L-TQ3_0-v1.1.gguf`, 83.975.624.672 bytes, SHA-256 preregistrado `377d5aa5b473a89b4d0d0c9fbd54fd8fcc46da19c16fc881860577189c1403df`. La descarga debe demostrar exactamente ese SHA.
- Q152 fixture/gates de calidad siguen sin cambio: BCB-Hard-8 seed 4242, 8 tareas, ASTRA Q97 histórico 2/8; requiere 8/8 transporte, 0 sandbox errors, 0 vacíos y candidato ≥4/8 para habilitar una nueva evaluación. Resultado de una semilla no promociona modelo.

## Reglas de recursos

Una sola tarea/servidor; puerto de Q152 18382 sólo loopback. No tocar ASTRA IQ2_XS, SOL, modelos/configuración PeritoSoft o GUI. Sin límites artificiales de RAM/VRAM; aplicar las barreras severas ya fijadas en Q152. En Q160 (preflight/build/list-devices) no se descargará el GGUF y no se iniciará inferencia.

## Fuentes primarias consultadas

- [Tarjeta Gyro-Coder GGUF](https://huggingface.co/agentionai/Qwen3.8-Flash-Next-Gyro-Coder-GGUF): el nombre TQ3_0 representa clase de tamaño, lista los tipos internos y apunta al fork del proveedor.
- [API de branch main del fork en GitLab](https://gitlab.com/api/v4/projects/agentionai-group%2Fllama.cpp/repository/branches/main): commit fijado.
- [llama-arch.cpp del fork](https://gitlab.com/api/v4/projects/agentionai-group%2Fllama.cpp/-/blob/main/src/llama-arch.cpp): `qwen4exp`.
- [mmq.cu del fork](https://gitlab.com/api/v4/projects/agentionai-group%2Fllama.cpp/-/blob/main/ggml/src/ggml-cuda/mmq.cu): dispatch CUDA para TQ2_T/TQK6/TQK7/TQP5–7.
- [Especificación Gyro](https://gitlab.com/agentionai-group/agention-gyro): IDs y empaquetado de tipos internos.
