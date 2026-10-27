# Q152 results — Gyro-Coder-L v1.1 runtime preflight

**Status: blocked; no quality result.** The preregistered dual-RTX3090 BCB-Hard-8 screen did not start because the publisher's pinned Docker image did not expose a usable NVIDIA Vulkan backend.

The host reports both RTX 3090s through `nvidia-smi` and host `vulkaninfo`. Inside the exact pinned image, `nvidia-smi` sees both cards, but `/app/llama-server --list-devices` reports `(none)`. Vulkan loader output ends in `vkCreateInstance: Found no drivers`. The image includes `libggml-vulkan.so`; the image initially lacked `libXext.so.6`. A diagnostic retry mounted the host NVIDIA ICD JSON, `libXext.so.6`, `/dev/dri`, and `libvulkan.so.1`, yet the server still could not obtain `vkCreateInstance`. The result is an image/driver integration failure, not a model quality failure.

No GGUF was downloaded, no model was loaded, no inference or benchmark ran, and no GPU compute was used. Only GPU enumeration/NVML checks ran. The test image (digest `sha256:ddcba819…`, 169,911,998 bytes) had no consuming containers and was removed after the preflight; Docker reclaimed 2,396,160 physical bytes because other images share layers.

**Resume condition:** use a corrected/pinned runtime or a reproducible container invocation for which `llama-server --list-devices` lists both RTX 3090s. Then validate exact TQ3_0 v1.1 load/distribution before downloading the 83,975,624,672-byte model. Do not fall back to CPU or a single GPU. The original screen and pass gates remain in `PLAN.md`.

The Google Sheet records the block in `Evaluaciones LlamaCode!A356:J356`, `Accionables!A25:N25`, and `Inventario de modelos!A17:R17`. No row was added to `Resultados` because there are no measurements. ASTRA, SOL, and PeritoSoft were not touched.

## Revalidación Q158/Q159 · 2026-10-27T02:16:29Z

- Q158 probó la imagen GHCR oficial fijada `sha256:0f0547624f92df823ef7bdbfc1e497a3674cebeaaaefb2c59012ba1716799fc6` con `NVIDIA_DRIVER_CAPABILITIES=all`; `/app/llama-server --list-devices` devolvió `(none)`. La imagen se retiró después; no hubo modelo/inferencia.
- Q159 inspeccionó el fork oficial en `dc255f2a4b6e4211b555b0c05260b2523281f314`: los tipos registrados incluyen TQ2_0/TQ2_T/TQK6/TQK7, no TQ3_0. Se paró antes de build y GPU.
- Q152 queda bloqueada por soporte del formato exacto. No es una evaluación de calidad. Recibos Q158/Q159 enlazados en WORK_QUEUE.md.
