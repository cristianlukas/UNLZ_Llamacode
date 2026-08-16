# Matriz de perfiles para benchmarks

Snapshot de revisión: 2026-08-16. Este archivo conserva la identidad y la configuración efectiva de los diez perfiles que deben aparecer en la tabla final. Los cambios de perfiles deben hacerse con LlamaCode cerrada; luego hay que volver a abrir la app headless y verificar que los argumentos efectivos coincidan con esta captura.

## Tabla de resultados

Los guiones indican que todavía no existe una corrida comparable guardada. Los valores históricos se conservan hasta que una repetición válida los reemplace.

| Perfil | HumanEval/20 | BigCodeBench/8 | Tiempo HE20 | Tiempo BCB | TPS HE20 | TPS BCB | Estado | Configuración |
|---|---:|---:|---:|---:|---:|---:|---|---|
| BALANCE - Qwen3.8 UD-Q4 visión | 20/20 | 7/8 | 269,96 s | 736,07 s | — | 39,53 | HE20 histórico; BCB válido | 131k · MTP3 · texto + imagen · UD-Q4_K_XL |
| BALANCE - Qwen3.8 UD-Q4 MTP4 | 20/20 | 3/8 | 332,12 s | 585,12 s | — | 54,85 | HE20 válido; BCB calidad | 131k · MTP4 · texto + imagen · UD-Q4_K_XL |
| FAST - KAT2-Coder-7-8-26 | 20/20 | — | 307,78 s | 20,87 s | — | 0,00 | BCB infraestructura (`Connection closed`); repetir | 262k · texto · Q4_K_M |
| FAST - KAT-Coder-7-8-26 | 20/20 | — | 212,69 s | 20,60 s | — | 0,00 | BCB infraestructura (`Connection closed`); repetir | 262k · texto · Q4_K_M |
| FAST - BigBang · MTP · top-p 0.08 | 20/20 | — | 136,84 s | 41,42 s | 107,56 | 0,00 | BCB infraestructura; repetir | 131k · MTP · texto + imagen · Q4_K_M · top-p 0.08 |
| BALANCE - BigBang · MTP · top-p 0.08 | 20/20 | 2/8 | 207,55 s | 464,06 s | 117,58 | 107,45 | BCB calidad; 2 reparaciones y anti-loop; el ID interno corresponde a MTP embebido KV f16 | 131k · MTP · texto + imagen · KV f16 |
| BALANCE - ThinkingCap Qwen3.6-27B MTP4 | 20/20 | — | 174,96 s | — | — | — | BCB bloqueado durante reparación 2/2; cancelar y repetir | 131k · MTP4 · texto + imagen · Q4_K_M |
| BALANCE - ThinkingCap+MTP-7-8-26 | 20/20 | — | 197,10 s | — | — | — | BCB pendiente | 196k · MTP · texto + imagen · Q4_K_M |
| BALANCE - Laguna S 2.1 118B-A8B Q2 | 20/20 | — | 204,16 s | — | — | — | BCB pendiente | 100k · texto · Q2 |
| QUALITY - DeepSeek Fusion leloch | 20/20 | — | 852,31 s | — | 9,15 | — | HE20 repetido válido; BCB pendiente | 131k · B4096 · U1024 · Flash ON · CPU-MoE · cache RAM 32 GiB · texto · Q2/Q4 híbrido · agent-chat |

## Captura completa de configuración

La configuración se separa en: launch profile, runtime preset y argumentos adicionales. Los IDs son importantes: si cambia uno, el perfil puede apuntar silenciosamente a otro modelo, backend o runtime.

### BALANCE - Qwen3.8 UD-Q4 visión

```text
launchId: sys-qwen38-27b-udq4-131k
backendProfileId: sysbe-sys-qwen38-27b-udq4-131k
modelProfileId: sysmodel-sys-qwen38-27b-udq4-131k
runtimePresetId: sysrt-sys-qwen38-27b-udq4-131k
agentProfileId: agent-maximo
runtime: ctx=131072, batch=512, ubatch=64, threads=8, gpuLayers=999, parallelSlots=1, cache=q4_0, flashAttention=on, contBatching=on, mmap=on, mlock=off
mmprojId: 4eff47c9-3c8c-5163-aa3a-b7262ff17af7
extraArgs: --cache-type-k q4_0 --cache-type-v q4_0 --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --jinja --predict 4096 --parallel 1 --reasoning off --spec-type draft-mtp --spec-draft-n-max 3 --chat-template-file %LOCALAPPDATA%/LlamaCode/LlamaCode/chat-templates/qwen38-tools-fixed.jinja
```

### BALANCE - Qwen3.8 UD-Q4 MTP4

```text
launchId: sys-bench-qwen38-udq4-mtp4
backendProfileId: sysbe-sys-bench-qwen38-udq4-mtp4
modelProfileId: sysmodel-sys-bench-qwen38-udq4-mtp4
runtimePresetId: sysrt-sys-bench-qwen38-udq4-mtp4
agentProfileId: agent-maximo
runtime: ctx=131072, batch=512, ubatch=64, threads=8, gpuLayers=999, parallelSlots=1, cache=q4_0, flashAttention=on, contBatching=on, mmap=on, mlock=off
mmprojId: 4eff47c9-3c8c-5163-aa3a-b7262ff17af7
extraArgs: --cache-type-k q4_0 --cache-type-v q4_0 --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --jinja --predict 4096 --parallel 1 --reasoning off --spec-draft-n-max 4 --spec-type draft-mtp --spec-draft-n-max 3 --chat-template-file %LOCALAPPDATA%/LlamaCode/LlamaCode/chat-templates/qwen38-tools-fixed.jinja
```

### FAST - KAT2-Coder-7-8-26

```text
launchId: sys-48-katcoder-262k
backendProfileId: sysbe-sys-48-katcoder-262k
modelProfileId: sysmodel-sys-48-katcoder-262k
runtimePresetId: sysrt-sys-48-katcoder-262k
agentProfileId: agent-maximo
runtime: ctx=262144, batch=2048, ubatch=512, threads=8, gpuLayers=999, parallelSlots=1, cache=q8_0, flashAttention=on, contBatching=on, mmap=on, mlock=off
extraArgs: --cache-type-k q8_0 --cache-type-v q8_0 --fit off --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --jinja --threads-batch 16 --predict 8192 --parallel 1 --reasoning off --cache-prompt --cache-reuse 512 --split-mode layer --tensor-split 1,1 --skip-chat-parsing --chat-template-file %LOCALAPPDATA%/LlamaCode/LlamaCode/chat-templates/kat-coder-tools.jinja
```

### FAST - KAT-Coder-7-8-26

```text
launchId: 9dda6bf4-7aae-4806-ba3a-8466bf41e702
backendProfileId: d4e4ab3d-1188-444e-b971-5f86fe683eab
modelProfileId: b933d0b2-014e-45c0-9558-3936d310e0bb
runtimePresetId: 8378307f-290b-4d7f-a345-1aef49db938b
agentProfileId: agent-maximo
runtime: ctx=262144, batch=2048, ubatch=512, threads=8, gpuLayers=999, parallelSlots=1, cache=q8_0, flashAttention=on, contBatching=on, mmap=on, mlock=off
extraArgs: --cache-type-k q8_0 --cache-type-v q8_0 --fit off --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --jinja --threads-batch 16 --predict 8192 --parallel 1 --reasoning off --cache-prompt --cache-reuse 512 --split-mode layer --tensor-split 1,1 --skip-chat-parsing --chat-template-file %LOCALAPPDATA%/LlamaCode/LlamaCode/chat-templates/kat-coder-tools.jinja
```

### FAST - BigBang · MTP · top-p 0.08

```text
launchId: cbff7c85-2116-4b42-b1b9-485dd33384cc
backendProfileId: b5acf97e-a091-4925-837a-99270c093b38
modelProfileId: ae10f4c4-2d39-4fc1-acdc-f16b9c75b0bc
runtimePresetId: 83cf0d96-d531-43e0-9fed-6a1c407047d0
agentProfileId: agent-maximo
runtime: ctx=131072, batch=4096, ubatch=1024, threads=0, gpuLayers=999, parallelSlots=1, cache=q8_0, flashAttention=on, contBatching=on, mmap=on, mlock=off
mmprojId: debe4716-71b7-5cfa-9d7a-045546810eda
extraArgs: --cache-type-k q8_0 --cache-type-v q8_0 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --no-context-shift --metrics --no-warmup --jinja --parallel 1 --reasoning on --spec-draft-n-max 5 --spec-type draft-mtp --temp 0.70 --top-p 0.08
```

### BALANCE - BigBang · MTP · top-p 0.08

```text
tablaName: BALANCE - BigBang · MTP · top-p 0.08
launchId: sys-bench-48-bigbang-mtp
internalName: [bench BigBang] 131k · MTP embebido · KV f16
backendProfileId: sysbe-sys-bench-48-bigbang-mtp
modelProfileId: sysmodel-sys-bench-48-bigbang-mtp
runtimePresetId: sysrt-sys-bench-48-bigbang-mtp
agentProfileId: agent-maximo
runtime: ctx=131072, batch=512, ubatch=128, threads=0, gpuLayers=999, parallelSlots=1, cache=f16, flashAttention=off, contBatching=on, mmap=on, mlock=off
mmprojId: 24152073-986a-5470-b717-a70861d14883
extraArgs: --flash-attn off --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --jinja --parallel 1 --reasoning on --spec-draft-n-max 5 --spec-type draft-mtp
WARNING: el nombre visible de la tabla no coincide con el nombre interno ni con top-p 0.08. No publicar esta fila como definitiva hasta resolver la identidad.
```

### BALANCE - ThinkingCap Qwen3.6-27B MTP4

```text
launchId: a03e65f5-2f2c-4d45-b67b-4b1270fa2a6c
backendProfileId: 1cd00b04-02bd-41bf-be45-49eb35b0c3cf
modelProfileId: 423c82fd-50c6-4a2d-b7b4-5c2d168dbd1c
runtimePresetId: 12b64031-d497-44ad-af3b-6fd2d451ce91
agentProfileId: (vacío; usa el default del launch)
runtime: ctx=131000, batch=512, ubatch=64, threads=8, gpuLayers=-1, parallelSlots=1, cache=q4_0, flashAttention=on, contBatching=on, mmap=off, mlock=on
mmprojId: 8572fc2c-29cd-5caf-b702-4e2b71fb5de3
extraArgs: --alias thinkingcap-qwen36-27b-q4km-mtp4 --cache-type-k q4_0 --cache-type-v q4_0 --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --cache-ram 32768 --cache-reuse 512 --jinja --threads-batch 8 --predict 4096 --parallel 1 --flash-attn on --ctx-size 131000 --reasoning off
```

### BALANCE - ThinkingCap+MTP-7-8-26

```text
launchId: sys-48-thinkingcap-mtp
backendProfileId: sysbe-sys-48-thinkingcap-mtp
modelProfileId: sysmodel-sys-48-thinkingcap-mtp
runtimePresetId: sysrt-sys-48-thinkingcap-mtp
agentProfileId: agent-maximo
runtime: ctx=196608, batch=2048, ubatch=512, threads=8, gpuLayers=999, parallelSlots=1, cache=q8_0, flashAttention=on, contBatching=on, mmap=on, mlock=off
mmprojId: fe4ff7eb-f122-53a6-bdb4-fde28253c875
extraArgs: --cache-type-k q8_0 --cache-type-v q8_0 --fit off --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --no-context-shift --metrics --no-warmup --jinja --threads-batch 16 --predict 8192 --parallel 1 --reasoning-format auto --cache-prompt --cache-reuse 512 --split-mode layer --tensor-split 1,1 --spec-type draft-mtp --spec-draft-n-max 4
```

### BALANCE - Laguna S 2.1 118B-A8B Q2

```text
launchId: 8d0dd2e0-c6c6-41ef-81d6-893c20d2f621
backendProfileId: b53df8bb-16b9-413d-8649-813e0a70d080
modelProfileId: 358edb77-0667-4190-b0e1-08654cb13864
runtimePresetId: 1b670632-3987-4047-be78-3efc93bb60d6
agentProfileId: (vacío; usa el default del launch)
runtime: ctx=100000, batch=2048, ubatch=768, threads=8, gpuLayers=999, parallelSlots=1, cache=q4_0, flashAttention=on, contBatching=on, mmap=on, mlock=off
extraArgs: --cache-type-k q4_0 --cache-type-v q4_0 --fit on --split-mode layer --tensor-split 1,1 --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --jinja --threads-batch 16 --predict 4096 --parallel 1 --reasoning-format auto --reasoning-preserve --chat-template-file %LOCALAPPDATA%/LlamaCode/LlamaCode/chat-templates/laguna-tools-v24.jinja
```

### QUALITY - DeepSeek Fusion leloch

```text
launchId: 4f5cc556-333d-4310-955e-15042cd874d6
backendProfileId: 1485cb47-757a-4a01-9f71-832567d01973
modelProfileId: 6ab3222e-5f71-442d-9eb9-7e895520befc
runtimePresetId: 20d4e6e6-9240-4926-9ea6-5bcea0eb2c50
agentProfileId: agent-maximo (para reproducir el histórico HE20 usar agent-chat)
runtime: ctx=131072, batch=4096, ubatch=1024, threads=8, gpuLayers=999, parallelSlots=1, cache=q4_0, flashAttention=on, contBatching=on, mmap=on, mlock=off
extraArgs: --cache-type-k q4_0 --cache-type-v q4_0 --fit off --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --jinja --threads-batch 16 --predict 16384 --parallel 1 --reasoning-format auto --cache-prompt --split-mode layer --tensor-split 1,0 --override-tensor blk\.(37|38|39|40|41|42)\.ffn_(gate|up|down)_exps\.weight=CUDA1,blk\.[0-9]+\.ffn_(gate|up|down)_exps\.weight=CPU --repeat-last-n 64 --flash-attn on --cpu-moe --cache-ram 32768
historical HE20 agent: agent-chat; thinkingEnabled=false
```

## Regla de edición y verificación

1. Cerrar LlamaCode antes de editar cualquier perfil o runtime desde la UI/archivo de perfiles.
2. Guardar una copia de esta matriz antes de modificar.
3. Abrir LlamaCode headless y verificar `getLaunchProfile`, `getRuntimePreset` y la línea de comandos efectiva de `llama-server`.
4. No aceptar un resultado 0/0 como calidad: clasificarlo como `Infraestructura`, `server-load`, `server-crash` o `timeout`.
5. Actualizar primero la fila de resultados y luego el bloque de configuración, manteniendo el ID histórico de la corrida.
