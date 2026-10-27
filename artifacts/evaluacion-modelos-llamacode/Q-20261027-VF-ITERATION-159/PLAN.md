# Q159 · probar ruta CUDA oficial de Agention para Gyro-Coder-L

**Estado:** preregistrado antes de clonar código, compilar o consultar las GPU. Lock compartido del lote VF: Q146, token `2242863e-c78e-4fa9-9649-c1d1541f3919`.

## Pregunta

¿El fork oficial `agentionai/llama.cpp`, fijado al commit `dc255f2a4b6e4211b555b0c05260b2523281f314` y compilado con CUDA en este host, enumera ambas RTX 3090 y contiene soporte de loader para el GGUF Gyro-Coder-L TQ3_0 v1.1? Esto determina si se puede reabrir la descarga/model screen preregistrada Q152 después de fallar sus dos rutas Vulkan.

## Evidencia que justifica esta prueba

- Q152 Docker Hub digest: Vulkan no inicializó.
- Q158 GHCR actual + la variable oficial `NVIDIA_DRIVER_CAPABILITIES=all`: `--list-devices` devuelve `(none)`; el digest se retiró sin consumidores.
- La guía oficial actual dice para NVIDIA que se use el build CUDA del fork con toolkit 12.x+. El host tiene CUDA Toolkit 12.0, CMake 3.28.3, Ninja 1.11.1 y ambas RTX 3090.
- Fuente primaria: https://www.agention.ai/models/gyro/ ; repo oficial: https://github.com/agentionai/llama.cpp .
- El commit se resolvió por `git ls-remote` a `dc255f2a4b6e4211b555b0c05260b2523281f314` antes del clone.

## Diseño / gates

1. Clonar en D/NVMe, fetch shallow del SHA exacto y verificar `HEAD` antes de compilar. No modificar el repo LlamaCode.
2. Configurar Release/Ninja, `GGML_CUDA=ON`, `GGML_VULKAN=OFF`, arquitectura CUDA `86` (RTX 3090), build del target `llama-server`. No instalar paquetes ni actualizar CUDA/driver.
3. Inspeccionar la fuente para el tipo/formato TQ3_0 de Gyro-Coder y ejecutar solo `llama-server --list-devices` (sin servidor HTTP, modelo ni requests).
4. PASS requiere: build limpio; ambas RTX 3090 enumeradas; soporte TQ3_0 presente. En otro caso, detener antes de descargar el GGUF y retirar solo source/build de esta prueba, conservando logs/recibos.
5. Si pasa, enmendar Q152 con el runtime CUDA y verificar espacio en D. Después descargar solo revisión `87d31357f4cfeb8555cf32fc63a707c5fa10ae7a` / archivo TQ3_0 v1.1 / SHA `377d5aa5b473a89b4d0d0c9fbd54fd8fcc46da19c16fc881860577189c1403df`, y aplicar el screen BCB-Hard-8 preregistrado con uso serial de ambas GPU. No promocionar por una semilla.

## Límites de uso/limpieza

- No hay proceso PeritoSoft/inference server ni contenedor activo; los dos contenedores históricos de vLLM están detenidos y permanecen intactos.
- No se fijan límites de RAM/swap/VRAM; no se termina la GUI ArtCraft. No tocar ASTRA, SOL, PeritoSoft ni sus archivos/configuración.
- D/NVMe tiene 496.142.651.392 B libres; raíz 9.446.719.488 B. Source/build permanece en D; modelo de 83.975.624.672 B no se baja hasta PASS.
- La prueba de Q159 es de compilación/backend y formato; no produce puntuación de modelo ni TPS.
