# Matriz de perfiles para benchmarks

Snapshot de revisión: 2026-08-16. Este archivo conserva la identidad y la configuración efectiva de los diez perfiles base, además de la variante experimental derivada de DeepSeek y los candidatos derivados del catálogo. Los cambios de perfiles deben hacerse con LlamaCode cerrada; luego hay que volver a abrir la app headless y verificar que los argumentos efectivos coincidan con esta captura.

## Tabla de resultados

Los guiones indican que todavía no existe una corrida comparable guardada. Los valores históricos se conservan hasta que una repetición válida los reemplace.

| Perfil | HumanEval/20 | Calidad HE0 | BigCodeBench/8 | Tiempo HE20 | Tiempo BCB | TPS HE20 | TPS BCB | TPS HE0 | Estado | Configuración |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| BALANCE - Qwen3.8 UD-Q4 visión | 20/20 | 1/1 | 7/8 | 269,96 s | 736,07 s | — | 39,53 | 56,89 | HE0 válido (12,997 s); HE20 histórico; BCB válido | 131k · MTP3 · texto + imagen · UD-Q4_K_XL |
| BALANCE - Qwen3.8 UD-Q4 MTP4 | 20/20 | 1/1 | 3/8 | 332,12 s | 585,12 s | — | 54,85 | 57,06 | HE0 válido (13,132 s); HE20 válido; BCB calidad | 131k · MTP4 · texto + imagen · UD-Q4_K_XL |
| FAST - KAT2-Coder-7-8-26 | 20/20 | — | — | 307,78 s | 20,87 s | — | 0,00 | 103,93* | HE0 daemon-crash; sólo timing nativo; BCB infraestructura (`Connection closed`); repetir | 262k · texto · Q4_K_M |
| FAST - KAT-Coder-7-8-26 | 20/20 | 1/1 | — | 212,69 s | 20,60 s | — | 0,00 | 113,03 | HE0 válido (13,963 s); BCB infraestructura (`Connection closed`); repetir | 262k · texto · Q4_K_M |
| FAST - BigBang · MTP · top-p 0.08 | 20/20 | 1/1 | — | 136,84 s | 41,42 s | 107,56 | 0,00 | 165,87 | HE0 válido (10,428 s); BCB infraestructura; repetir | 131k · MTP · texto + imagen · Q4_K_M · top-p 0.08 |
| BALANCE - BigBang · MTP · top-p 0.08 | 20/20 | — | 2/8 | 207,55 s | 464,06 s | 117,58 | 107,45 | — | HE0 infraestructura (`Connection closed`, resultado bruto 0/1); BCB calidad; repetir | 131k · MTP · texto + imagen · KV f16 |
| BALANCE - ThinkingCap Qwen3.6-27B MTP4 | 20/20 | 1/1 | — | 174,96 s | — | — | — | 61,62 | HE0 válido (12,922 s); BCB bloqueado durante reparación 2/2; cancelar y repetir | 131k · MTP4 · texto + imagen · Q4_K_M |
| BALANCE - ThinkingCap+MTP-7-8-26 | 20/20 | 1/1 | — | 197,10 s | 38,24 s | — | 0,00 | 63,90 | HE0 válido (11,435 s); BCB infraestructura; repetir | 196k · MTP · texto + imagen · Q4_K_M |
| BALANCE - Laguna S 2.1 118B-A8B Q2 | 20/20 | 1/1 | — | 204,16 s | 56,93 s | — | 0,00 | 53,34 | HE0 válido (16,980 s); BCB infraestructura (`Connection closed`); repetir | 100k · texto · Q2 |
| QUALITY - DeepSeek Fusion leloch | 20/20 | 1/1 | — | 852,31 s | 716,23 s† | 9,15 | 0† | 8,53 | HE0 válido (70,903 s); reintento BCB en curso; no contar respuesta sin cierre como calidad | 131k · B4096 · U1024 · Flash ON · CPU-MoE · cache RAM 32 GiB · texto · Q2/Q4 híbrido · agent-chat |
| QUALITY - DeepSeek Fusion leloch · VRAM balance | — | 1/1 | — | — | — | — | — | 8,81 | HE0 válido (67,039 s); variante conservadora; VRAM medida 35,7 GiB | 131k · B4096 · U1024 · tensor-split 1,0 · expertos 0–1 en CUDA0 y 37–42 en CUDA1 · CPU-MoE · Q2/Q4 híbrido |

HE0 de la variante actual: `HumanEval_1_tems__20260816_131714`, `1/1`, `67,039 s`, sin reparación ni fallo de infraestructura; `TPS HE0=8,81` es el timing nativo de `llama-server`. La corrida descartada anterior `HumanEval_1_tems__20260816_122210` usó `tensor-split=1,1` y falló al cargar por OOM en CUDA1; no se cuenta como calidad. La corrida histórica `HumanEval_1_tems__20260816_122508` también fue válida (`1/1`, `67,308 s`, `9,20 t/s`).

## Procedimiento de benchmarking

El orden es deliberado y se aplica a cada perfil base o candidato, siempre en modo headless y con el mismo harness, agente, semilla y criterios de reparación:

1. **HumanEval/0 (smoketest):** ejecutar una sola tarea. Verifica que el modelo, backend, plantilla, MTP/mmproj y transporte funcionen; registra `Calidad HE0` y `TPS HE0`. Un `server-load`, `server-crash`, `timeout`, conexión cerrada o respuesta sin cierre es un fallo de infraestructura, no calidad cero.
2. **HumanEval/20:** sólo después de HE0 válido. Ejecutar las 20 tareas para medir calidad del perfil y del harness; registrar score, tiempo total y TPS. Las repeticiones reemplazan el valor histórico únicamente cuando terminan con cierre evaluable.
3. **BigCodeBench/8:** después de HE20 válido —o como repetición explícita de una fila ya marcada— ejecutar las 8 tareas difíciles para medir tool-calls, reparaciones, loops y estabilidad sostenida; registrar score, tiempo total y TPS.

La promoción de un perfil requiere pasar HE0. HE20 separa calidad general y problemas del harness; BCB separa los casos difíciles. Por eso no se mezclan `0/0` de infraestructura con una puntuación de inteligencia, y todo resultado queda anotado junto con la configuración efectiva usada.

## Candidatos derivados para medir

No se duplican manualmente los perfiles base. Se incorporan al plan las variantes ya existentes en el catálogo y dos variantes nuevas de Laguna. Cada fila sigue HE0 → HE20 → BCB; el HE0 de esta tanda ya fue ejecutado en modo headless y sus resultados están debajo.

| Candidato | Derivado de | Hipótesis | Cambio controlado | Orden |
|---|---|---|---|---|
| `[bench Qwen3.8] UD-Q4 · MTP2 · 64k · mmproj` (`sys-bench-qwen38-udq4-mtp2-64k`) | BALANCE - Qwen3.8 UD-Q4 visión | Menos contexto y MTP pueden mejorar velocidad/estabilidad | ctx 65k; MTP2; B512/U64 | HE0 → HE20 → BCB |
| `[bench Qwen3.8] UD-Q4 · MTP3 · B1024 · mmproj` (`sys-bench-qwen38-udq4-mtp3-b1024`) | BALANCE - Qwen3.8 UD-Q4 visión | Menor batch puede evitar fallos de infraestructura | B1024/U128; MTP3 | HE0 → HE20 → BCB |
| `[bench Qwen3.8] UD-Q4 · MTP3 · 131k · KV q8 · mmproj` (`sys-bench-qwen38-udq4-mtp3-kv8`) | BALANCE - Qwen3.8 UD-Q4 visión | KV q8 puede sostener mejor contexto y calidad | KV K/V q8_0 | HE0 → HE20 → BCB |
| `[bench Qwen3.8] Q4_K_M · MTP4 · 131k · mmproj` (`sys-bench-qwen38-q4km-mtp4`) | Qwen3.8-27B Q4_K_M visión | Comparar MTP4 sin cambiar quant/contexto | MTP4 | HE0 → HE20 → BCB |
| `[bench Qwen3.8] Q5_K_M · MTP3 · 64k · KV q8 · mmproj` (`sys-bench-qwen38-q5km-mtp3-64k-kv8`) | Qwen3.8-27B Q5_K_M visión | Más precisión/KV puede mejorar BCB a costa de velocidad | ctx 65k; KV q8_0 | HE0 → HE20 → BCB |
| `[bench 48GB KAT] KV f16 · 262k` (`sys-bench-48-kat-f16`) | FAST - KAT-Coder-7-8-26 | Aislar si KV f16 mejora calidad sin penalizar el decode | KV K/V f16 | HE0 → HE20 → BCB |
| `[bench BigBang] 131k · MTP · batch 1024 · ubatch 256` (`sys-bench-48-bigbang-fast`) | FAST - BigBang MTP | Mantener MTP y bajar presión de prefill para corregir `Connection closed` | B1024/U256; MTP5 | HE0 → HE20 → BCB |
| `[bench BigBang] 131k · sin MTP · KV f16` (`sys-bench-48-bigbang-base`) | BALANCE - BigBang MTP | Aislar si el fallo pertenece al MTP o al harness/modelo | MTP desactivado | HE0 → HE20 → BCB |
| `[bench 48GB MAX-Q] MTP4 · 131k · visión` (`sys-bench-48-tc-mtp-131k`) | BALANCE - ThinkingCap Qwen3.6 MTP4 | Mantener MTP4 y reducir contexto para evitar bloqueo sostenido | ctx 131k; MTP4 | HE0 → HE20 → BCB |
| `[bench Laguna] Q2 · 64k · B1024 · U256` (`sys-bench-laguna-s-2-1-q2-48gb-64k-b1024`) | BALANCE - Laguna S 2.1 | Reducir KV y batch para salir del bucle de evaluación | ctx 65k; B1024/U256 | HE0 → HE20 → BCB |
| `[bench Laguna] Q2 · 100k · B1024 · U256` (`sys-bench-laguna-s-2-1-q2-48gb-100k-b1024`) | BALANCE - Laguna S 2.1 | Aislar batch como causa manteniendo el contexto histórico | B1024/U256; ctx 100k | HE0 → HE20 → BCB |
| `[bench antirez] 32k · B2048 · U256 · KV q4_0` (`sys-48-antirez-dsv4-q2q4-0731-32k-b2048`) | QUALITY - DeepSeek Fusion leloch | Bajar contexto/batch para mejorar estabilidad sin repartir capas base | ctx 32k; B2048/U256; `tensor-split 1,0` | HE0 → HE20 → BCB |
| `[bench antirez] 32k · B4096 · U512 · KV q8_0` (`sys-48-antirez-dsv4-q2q4-kv8`) | QUALITY - DeepSeek Fusion leloch | KV q8 puede mejorar calidad sostenida; medir coste real | ctx 32k; KV K/V q8_0 | HE0 → HE20 → BCB |

## Resultados HE0 de los candidatos

TPS es el decode nativo informado por `llama-server` en `eval time`, no el `avgTps` del agente cuando el harness no recibió tokens de generación. Un `—` indica que no hubo timing evaluable por fallo de carga o cierre de conexión.

| Candidato | HumanEval/0 | Tiempo HE0 | TPS HE0 | Estado |
|---|---:|---:|---:|---|
| `[bench Qwen3.8] UD-Q4 · MTP2 · 64k · mmproj` | 1/1 | 12,926 s | 51,68 | Válido |
| `[bench Qwen3.8] UD-Q4 · MTP3 · B1024 · mmproj` | 1/1 | 10,378 s | 64,66 | Válido |
| `[bench Qwen3.8] UD-Q4 · MTP3 · 131k · KV q8 · mmproj` | 1/1 | 12,925 s | 57,87 | Válido |
| `[bench Qwen3.8] Q4_K_M · MTP4 · 131k · mmproj` | 1/1 | 12,968 s | 45,38 | Válido |
| `[bench Qwen3.8] Q5_K_M · MTP3 · 64k · KV q8 · mmproj` | 1/1 | 14,982 s | 52,48 | Válido |
| `[bench 48GB KAT] KV f16 · 262k` | 0/1 | 13,930 s | 104,98 | HE0 evaluable; calidad fallida |
| `[bench BigBang] 131k · MTP · batch 1024 · ubatch 256` | — | 58,638 s | — | Infraestructura: server-load |
| `[bench BigBang] 131k · sin MTP · KV f16` | — | 12,470 s | — | Infraestructura: `Connection closed` (bruto 0/1) |
| `[bench 48GB MAX-Q] MTP4 · 131k · visión` | 1/1 | 11,498 s | 58,02 | Válido |
| `[bench Laguna] Q2 · 64k · B1024 · U256` | 1/1 | 15,004 s | 51,46 | Válido |
| `[bench Laguna] Q2 · 100k · B1024 · U256` | 1/1 | 13,961 s | 51,99 | Válido |
| `[bench antirez] 32k · B2048 · U256 · KV q4_0` | 1/1 | 93,540 s | 10,00 | Válido |
| `[bench antirez] 32k · B4096 · U512 · KV q8_0` | 1/1 | 76,189 s | 10,00 | Válido |

Evidencia de la tanda: `benchmark-runs/HumanEval_1_tems__20260816_130505` a `HumanEval_1_tems__20260816_133559`. Los 24 IDs fueron ejecutados aisladamente. KAT2 (`sys-48-katcoder-262k`) cargó y llegó a timing nativo de `103,93 t/s`, pero el daemon terminó en `APPCRASH` de `LlamaCode.exe` dentro de `Qt6Core.dll` antes de persistir el JSON; queda como `HE0 daemon-crash`, no como calidad.

Las variantes DeepSeek mantienen la regla de seguridad del perfil histórico: `--tensor-split 1,0`, expertos residentes alineados con sus capas y resto en CPU. No se propone `tensor-split 1,1`, porque la prueba local anterior terminó en OOM/corrupción y no es una mejora válida.

`*` En KAT2, `103,93 t/s` es timing nativo observado antes del `APPCRASH`; no hay JSON evaluable y debe repetirse.

`†` En DeepSeek, el tiempo/TPS de BCB es el último intento observado antes de cerrar la serie; la respuesta no tuvo cierre evaluable. Debe repetirse después de HE0/HE20 válidos del perfil o variante correspondiente.

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

### QUALITY - DeepSeek Fusion leloch · VRAM balance

Variante duplicada mientras LlamaCode estaba cerrada. El perfil original no comparte backend, modelo ni runtime persistidos con esta copia; sólo comparten el mismo archivo de modelo identificado por `modelId`.

```text
launchId: 6b3bf7bd-0889-491a-9b6d-b12128478a5f
backendProfileId: 07bf242d-0685-45d1-a752-11ddec6ef6df
modelProfileId: 0985be04-d2bc-455d-a3a5-e5fc19795e5d
runtimePresetId: fdd4ca0a-3b8d-43a2-924b-092327aca314
agentProfileId: agent-maximo (el smoketest HE0 se ejecutó con agent-chat)
runtime: ctx=131072, batch=4096, ubatch=1024, threads=8, gpuLayers=999, parallelSlots=1, cache=q4_0, flashAttention=on, contBatching=on, mmap=on, mlock=off
mmprojId: (vacío)
extraArgs: --cache-type-k q4_0 --cache-type-v q4_0 --fit off --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --jinja --threads-batch 16 --predict 16384 --parallel 1 --reasoning-format auto --cache-prompt --split-mode layer --tensor-split 1,0 --override-tensor blk\.(0|1)\.ffn_(gate|up|down)_exps\.weight=CUDA0,blk\.(37|38|39|40|41|42)\.ffn_(gate|up|down)_exps\.weight=CUDA1,blk\.[0-9]+\.ffn_(gate|up|down)_exps\.weight=CPU --repeat-last-n 64 --flash-attn on --cpu-moe --cache-ram 32768
```

La variante conserva `--tensor-split 1,0` para no desalinear las capas base de los expertos. Su única diferencia funcional respecto del original es el primer tramo de `-ot`, que coloca los expertos de los bloques 0 y 1 en CUDA0; los bloques 37–42 siguen en CUDA1 y el resto sigue en CPU. La vista previa efectiva verificada antes del benchmark resolvió `--override-tensor` con esa misma regla.

Backup de los cuatro archivos antes de la edición: `profiles/{launches,backends,models,runtimes}.json.bak.vram-variant.20260816_121921`.

## Regla de edición y verificación

1. Cerrar LlamaCode antes de editar cualquier perfil o runtime desde la UI/archivo de perfiles.
2. Guardar una copia de esta matriz antes de modificar.
3. Abrir LlamaCode headless y verificar `getLaunchProfile`, `getRuntimePreset` y la línea de comandos efectiva de `llama-server`.
4. No aceptar un resultado 0/0 como calidad: clasificarlo como `Infraestructura`, `server-load`, `server-crash` o `timeout`.
5. Actualizar primero la fila de resultados y luego el bloque de configuración, manteniendo el ID histórico de la corrida.
