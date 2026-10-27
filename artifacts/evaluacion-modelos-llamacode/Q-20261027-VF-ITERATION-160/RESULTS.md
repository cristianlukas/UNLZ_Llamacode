# Q160 resultados · gate CUDA del proveedor

**Resultado del gate Q160:** PASS para el runtime; Q152 quedó habilitada para descargar el GGUF exacto. Actualización posterior: la descarga Xet finalizó; tamaño 83,975,624,672 B y SHA-256 `377d5aa5b473a89b4d0d0c9fbd54fd8fcc46da19c16fc881577189c1403df` verificados al 2026-10-27T03:30:33Z. Aún no se inició servidor HTTP, inferencia ni benchmark.

- Procesos PeritoSoft/`llama-server`: ninguno. Listeners de inference: ninguno. Docker no mostró contenedores activos relevantes. No se envió señal; ArtCraft y Codex quedaron intactos.
- Fuente fijada: AgentionAI llama.cpp GitLab commit `9aa51ce4fdd3435a91531ffe16a17414ccc6dc6f`.
- Static check: checkout incluye arquitectura `qwen4exp` y kernels CUDA para Gyro `TQ2_T`, `TQK6`, `TQK7`, `TQP5`, `TQP6`, `TQP7`.
- CMake configure: Release, `GGML_CUDA=ON`, `CMAKE_CUDA_ARCHITECTURES=86`; exit code 0.
- Build: target `llama-server`, `--parallel 16`; exit code 0. Se generó `/media/cristian/Disco local/Models-eval/Q160-agention-llama-build/bin/llama-server`.
- Device enumeration: `CUDA0` NVIDIA GeForce RTX 3090 (23,020 MiB libres); `CUDA1` NVIDIA GeForce RTX 3090 (23,803 MiB libres). Gate dual-3090 satisfecho.
- Memoria durante build: MemAvailable ~101 GiB; PSI some/full avg10 0.00/0.00; no se aplicaron límites artificiales. D tenía 495,309,963,264 B libres al terminar.
- Warning no bloqueante del proveedor: `src/models/qwen4exp.cpp:563` usa `%d` para `long int` en `fprintf`. No se modificó la fuente.
- La ausencia de OpenSSL desactiva HTTPS en el binario, pero no impide una prueba en loopback. El build obtuvo y verificó los assets de UI.

**Siguiente paso de Q152:** completar la descarga del archivo v1.1 y revisión preregistrados a D; exigir tamaño 83,975,624,672 B y SHA-256 `377d5aa5b473a89b4d0d0c9fbd54fd8fcc46da19c16fc881860577189c1403df` antes de iniciar el servicio. Mantener las RTX 3090 en uso serial y el puerto loopback 18382. No usar fallback de una GPU o CPU. Recibo de progreso: `Q-20261026-VF-ITERATION-152/receipts/download-progress-20261027T024810Z.json`.

Este PASS confirma soporte de dispositivos en el runtime; no demuestra que el GGUF cargue ni dice nada de calidad/velocidad del modelo.
