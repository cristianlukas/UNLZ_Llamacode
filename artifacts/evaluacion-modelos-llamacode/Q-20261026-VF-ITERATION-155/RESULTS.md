# Q155 — PeritoSoft shutdown check and Gyro-Coder-L runtime revalidation

**Date:** 2026-10-26 23:48 UTC  
**Umbrella lock:** Q146, token `2242863e-c78e-4fa9-9649-c1d1541f3919`  
**Outcome:** shutdown request satisfied by absence; Q152 remains blocked before model download/inference.

## PeritoSoft and server check

The user authorized terminating PeritoSoft and its LlamaServers. Process, listener, and Docker-container checks found no PeritoSoft app process, `llama-server` process, inference listener, or running container. No process was terminated. `artcraft-launcher` on loopback port 47413 and the unrelated desktop processes were left alone. ASTRA, SOL, PeritoSoft files/configuration, and the shared runtime were not changed.

## Q152 gate revalidation

- Host `nvidia-smi` reports both GeForce RTX 3090 cards with driver 615.71.09 and 24,576 MiB each. Host `vulkaninfo --summary` enumerates both NVIDIA Vulkan devices. This confirms the host driver/runtime is currently healthy.
- Docker registry inspection of `agentionai/agention-llama:server` still resolves to `sha256:ddcba819dfa58332e408aa734d3cde13572331a57683abd3afb1e0a620f543d6`, the exact image digest that failed Q152's in-container Vulkan `vkCreateInstance`/`--list-devices` gate. That image is not currently present locally, and `docker ps` reports no active containers.
- The current AgentionAI model card still labels Gyro-Coder-L v1.1 as preview and says Strata support is coming. The current Strata issue #3640 documents a manual path for a different TQ2_T Gyro-Coder artifact on one RTX 3090; it does not validate the preregistered TQ3_0 v1.1 file or its dual-3090 path. Therefore the Q152 target and gate remain unchanged.
- No GGUF was downloaded, no image was pulled, no build/server/request/benchmark/inference was run, and no GPU kernel was used. This was a preflight-only check.

## Pending batch gates

The 69-entry inbox has seven unresolved entries and none is runnable with the evidence/host state now available: #26 needs a reproducible Qwen2.5-72B/A100 result and a transferable local hypothesis; #28 needs an authorized fixture and independent acceptance tests; #31 needs ROCm/RX7900 support and at least 570 GB free on the compatible NVMe (current D: has 498,122,457,088 bytes free); #32 needs a transcript/capture; #65 needs Windows and about 1.1 TB free on NVMe (this executor is Ubuntu; current C: has 145,110,867,968 bytes free); #66 needs a corrected/pinned runtime that enumerates both 3090s and loads the exact TQ3_0 v1.1 artifact; #69 remains blocked by the open Strata Qwen3.6-35B-A3B layer-split issue and absence of a matching local quant.

No quality or speed conclusion was added for Q152. Reopen only after its concrete runtime gate changes; do not substitute CPU, single-GPU, TQ2, or another model for the preregistered screen. There is no other justified model benchmark ready to start in this batch at this checkpoint.

## Evidence

Receipt: `receipts/runtime-and-queue-revalidation.json`.  
Q152 preregistration and prior failed container result: `../Q-20261026-VF-ITERATION-152/PLAN.md` and `../Q-20261026-VF-ITERATION-152/RESULTS.md`.  
Upstream sources checked 2026-10-26: [AgentionAI Gyro-Coder model card](https://huggingface.co/agentionai/Qwen3.8-Flash-Next-Gyro-Coder-GGUF), [Strata issue #3640](https://github.com/Niko1221/Strata/issues/3640), [Strata issue #3294](https://github.com/Niko1221/Strata/issues/3294).


## Google Sheets readback confirmed 2026-10-27 00:03 UTC

Fresh readback found Q152 status at `Accionables!A25:N25` and `Evaluaciones LlamaCode!A356:J356`; the inventory row remains at `Inventario de modelos!A17:R17`. These rows show the runtime blocker, no model score, and unchanged pinned digest. Resultados contains only completed Q154 measurements in rows 356–357; Q155 correctly has no result row. The current sheet state and adjacent rows are saved in Q156's prewrite snapshot.
