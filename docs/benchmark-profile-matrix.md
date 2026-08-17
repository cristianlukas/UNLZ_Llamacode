# Matriz de perfiles para benchmarks

Snapshot de revisión: 2026-08-17. Este archivo conserva la identidad y la configuración efectiva de los diez perfiles base, además de la variante experimental derivada de DeepSeek y los candidatos derivados del catálogo. Los cambios de perfiles deben hacerse con LlamaCode cerrada; luego hay que volver a abrir la app headless y verificar que los argumentos efectivos coincidan con esta captura.

El procedimiento reusable para agregar modelos, binarios, perfiles o harnesses está documentado en el [Manual de benchmarking](benchmark-manual.md). Esta matriz resume resultados; el manual define las condiciones de validez, el orden HE0 → HE20 → BCB y las reglas de promoción para FAST, BALANCED y QUALITY. HE0 es una compuerta dura: si falla, el perfil queda bloqueado para HE20 y BCB hasta investigar la causa raíz y repetir HE0 con resultado válido.

Política vigente: los pesos del modelo principal y el KV K/V deben ser `q8_0` o
menor. Las variantes históricas con KV `f16` fueron reemplazadas por copias
limitadas a `q8_0`; sus tiempos y scores anteriores no se mezclan con los nuevos.
Los `mmproj` `F16/BF16` se conservan únicamente como proyectores auxiliares de
visión y no representan el quant de los pesos ni del KV.

## Tabla de resultados

Los valores históricos de la tabla siguiente quedan como referencia. La tabla
vigente de la corrida corregida del 2026-08-17 aparece inmediatamente después;
no se mezclan resultados tomados con otra huella de configuración.

| Perfil | HumanEval/0 | HumanEval/20 | BigCodeBench/8 | Tiempo HE0 | Tiempo HE20 | Tiempo BCB | TPS HE0 | TPS HE20 | TPS BCB | Visión | Drafter | Quant | Parámetros (B) | Contexto | Configuración | Estado |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|---|---|---|---|---|
| BALANCE - Qwen3.8 UD-Q4 visión | 1/1 | 20/20 | 7/8 | 12,997 s | 269,96 s | 736,07 s | 56,89 | — | 39,53 | Sí | MTP3 | UD-Q4_K_XL | 27B | 131072 | `launch=sys-qwen38-27b-udq4-131k; backend=sysbe-sys-qwen38-27b-udq4-131k; modelProfile=sysmodel-sys-qwen38-27b-udq4-131k; runtimePreset=sysrt-sys-qwen38-27b-udq4-131k; model=Qwen3.8-27B-UD-Q4_K_XL.gguf; mmproj=mmproj-BF16.gguf; agent=agent-maximo; binary=official,b10331+; runtime=ctx=131072,batch=512,ubatch=64,threads=8,gpuLayers=999,slots=1,cache=q4_0,flash=on,cont=on,mmap=on,mlock=off; args=--cache-type-k q4_0 --cache-type-v q4_0 --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --jinja --predict 4096 --parallel 1 --reasoning off --spec-type draft-mtp --spec-draft-n-max 3 --chat-template-file %LOCALAPPDATA%/LlamaCode/LlamaCode/chat-templates/qwen38-tools-fixed.jinja` | HE0 válido; HE20 histórico; BCB válido |
| BALANCE - Qwen3.8 UD-Q4 MTP4 | 1/1 | 20/20 | 3/8 | 13,132 s | 332,12 s | 585,12 s | 57,06 | — | 54,85 | Sí | MTP4 | UD-Q4_K_XL | 27B | 131072 | `launch=sys-bench-qwen38-udq4-mtp4; backend=sysbe-sys-bench-qwen38-udq4-mtp4; modelProfile=sysmodel-sys-bench-qwen38-udq4-mtp4; runtimePreset=sysrt-sys-bench-qwen38-udq4-mtp4; model=Qwen3.8-27B-UD-Q4_K_XL.gguf; mmproj=mmproj-BF16.gguf; agent=agent-maximo; binary=official,b10331+; runtime=ctx=131072,batch=512,ubatch=64,threads=8,gpuLayers=999,slots=1,cache=q4_0,flash=on,cont=on,mmap=on,mlock=off; override=MTP n-max 4 sobre padre MTP3; args=--cache-type-k q4_0 --cache-type-v q4_0 --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --jinja --predict 4096 --parallel 1 --reasoning off --spec-type draft-mtp --spec-draft-n-max 4 --chat-template-file %LOCALAPPDATA%/LlamaCode/LlamaCode/chat-templates/qwen38-tools-fixed.jinja` | HE0 válido; HE20 válido; BCB calidad |
| FAST - KAT2-Coder-7-8-26 | 1/1 | 20/20 | — | 16,267 s | 307,78 s | 20,87 s | 103,93* | — | 0,00 | No | — | Q4_K_M | 35B-A3B (≈3B activos) | 262144 | `launch=sys-48-katcoder-262k; backend=sysbe-sys-48-katcoder-262k; modelProfile=sysmodel-sys-48-katcoder-262k; runtimePreset=sysrt-sys-48-katcoder-262k; model=Kwaipilot_KAT-Coder-V2.5-Dev-Q4_K_M.gguf; mmproj=ninguno; agent=agent-maximo; binary=official,b10228+; runtime=ctx=262144,batch=2048,ubatch=512,threads=8,gpuLayers=999,slots=1,cache=q8_0,flash=on,cont=on,mmap=on,mlock=off; args=--cache-type-k q8_0 --cache-type-v q8_0 --fit off --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --jinja --threads-batch 16 --predict 8192 --parallel 1 --reasoning off --cache-prompt --cache-reuse 512 --split-mode layer --tensor-split 1,1 --skip-chat-parsing --chat-template-file %LOCALAPPDATA%/LlamaCode/LlamaCode/chat-templates/kat-coder-tools.jinja` | HE0 revalidado 3/3; BCB infraestructura (`Connection closed`); repetir |
| FAST - KAT-Coder-7-8-26 | 1/1 | 20/20 | — | 13,963 s | 212,69 s | 20,60 s | 113,03 | — | 0,00 | No | — | Q4_K_M | 35B-A3B (≈3B activos) | 262144 | `launch=9dda6bf4-7aae-4806-ba3a-8466bf41e702; backend=d4e4ab3d-1188-444e-b971-5f86fe683eab; modelProfile=b933d0b2-014e-45c0-9558-3936d310e0bb; runtimePreset=8378307f-290b-4d7f-a345-1aef49db938b; model=Kwaipilot_KAT-Coder-V2.5-Dev-Q4_K_M.gguf; mmproj=ninguno; agent=agent-maximo; binary=official,b10228+; runtime=ctx=262144,batch=2048,ubatch=512,threads=8,gpuLayers=999,slots=1,cache=q8_0,flash=on,cont=on,mmap=on,mlock=off; args=--cache-type-k q8_0 --cache-type-v q8_0 --fit off --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --jinja --threads-batch 16 --predict 8192 --parallel 1 --reasoning off --cache-prompt --cache-reuse 512 --split-mode layer --tensor-split 1,1 --skip-chat-parsing --chat-template-file %LOCALAPPDATA%/LlamaCode/LlamaCode/chat-templates/kat-coder-tools.jinja` | HE0 válido; BCB infraestructura (`Connection closed`); repetir |
| FAST - BigBang · MTP · top-p 0.08 | 1/1 | 20/20 | — | 10,428 s | 136,84 s | 41,42 s | 165,87 | 107,56 | 0,00 | Sí | MTP embebido | Q4_K_M | 35B-A3B (≈3B activos) | 131072 | `launch=cbff7c85-2116-4b42-b1b9-485dd33384cc; backend=b5acf97e-a091-4925-837a-99270c093b38; modelProfile=ae10f4c4-2d39-4fc1-acdc-f16b9c75b0bc; runtimePreset=83cf0d96-d531-43e0-9fed-6a1c407047d0; model=endless-frontier_BigBang-v1-Q4_K_M.gguf; mmproj=mmproj-endless-frontier_BigBang-v1-bf16.gguf; agent=agent-maximo; binary=official,b10262+; runtime=ctx=131072,batch=4096,ubatch=1024,threads=0,gpuLayers=999,slots=1,cache=q8_0,flash=on,cont=on,mmap=on,mlock=off; args=--cache-type-k q8_0 --cache-type-v q8_0 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --no-context-shift --metrics --no-warmup --jinja --parallel 1 --reasoning on --spec-draft-n-max 5 --spec-type draft-mtp --temp 0.70 --top-p 0.08` | HE0 válido; BCB infraestructura; repetir |
| BALANCE - BigBang MTP | 1/1 | 20/20† | 2/8† | 13,365 s | 207,55 s† | 464,06 s† | 10,72 | 117,58† | 107,45† | Sí | MTP embebido | Q4_K_M | 35B-A3B (≈3B activos) | 65536 | `launch=sys-repair-48-bigbang-mtp-balance; display=24GB - BALANCE - BigBang MTP; backend=sysbe-sys-repair-48-bigbang-mtp-balance; modelProfile=sysmodel-sys-repair-48-bigbang-mtp-balance; runtimePreset=sysrt-sys-repair-48-bigbang-mtp-balance; model=endless-frontier_BigBang-v1-Q4_K_M.gguf; mmproj=24152073-986a-5470-b717-a70861d14883 (heredado); agent=agent-maximo (benchmark agent-chat); binary=official,b10262+; runtime=ctx=65536,batch=256,ubatch=64,threads=0,gpuLayers=999,slots=1,cache=q8_0,flash=on,cont=on,mmap=on,mlock=off; args=--top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --jinja --parallel 1 --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --reasoning off --spec-draft-n-max 5 --spec-type draft-mtp --temp 0.60 --top-p 0.95` | HE0 corregido y válido sin reparación; HE20/BCB históricos del perfil 131k/Flash off, repetir |
| BALANCE - ThinkingCap Qwen3.6-27B MTP4 | 1/1 | 20/20 | — | 12,922 s | 174,96 s | — | 61,62 | — | — | Sí | MTP4 | Q4_K_M | 27B | 131000 | `launch=a03e65f5-2f2c-4d45-b67b-4b1270fa2a6c; backend=1cd00b04-02bd-41bf-be45-49eb35b0c3cf; modelProfile=423c82fd-50c6-4a2d-b7b4-5c2d168dbd1c; runtimePreset=12b64031-d497-44ad-af3b-6fd2d451ce91; model=ThinkingCap-Qwen3.6-27B-Q4_K_M.gguf; mmproj=8572fc2c-29cd-5caf-b702-4e2b71fb5de3; agent=default del launch; binary=official; runtime=ctx=131000,batch=512,ubatch=64,threads=8,gpuLayers=-1,slots=1,cache=q4_0,flash=on,cont=on,mmap=off,mlock=on; args=--alias thinkingcap-qwen36-27b-q4km-mtp4 --cache-type-k q4_0 --cache-type-v q4_0 --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --cache-ram 32768 --cache-reuse 512 --jinja --threads-batch 8 --predict 4096 --parallel 1 --flash-attn on --ctx-size 131000 --reasoning off --spec-type draft-mtp --spec-draft-n-max 4` | HE0 válido; BCB bloqueado durante reparación; repetir |
| BALANCE - ThinkingCap+MTP-7-8-26 | 1/1 | 20/20 | — | 11,435 s | 197,10 s | 38,24 s | 63,90 | — | 0,00 | Sí | MTP4 | Q4_K_M | 27B | 196608 | `launch=sys-48-thinkingcap-mtp; backend=sysbe-sys-48-thinkingcap-mtp; modelProfile=sysmodel-sys-48-thinkingcap-mtp; runtimePreset=sysrt-sys-48-thinkingcap-mtp; model=ThinkingCap-Qwen3.6-27B-Q4_K_M.gguf; mmproj=fe4ff7eb-f122-53a6-bdb4-fde28253c875; agent=agent-maximo; binary=official,b10228+; runtime=ctx=196608,batch=2048,ubatch=512,threads=8,gpuLayers=999,slots=1,cache=q8_0,flash=on,cont=on,mmap=on,mlock=off; args=--cache-type-k q8_0 --cache-type-v q8_0 --fit off --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --no-context-shift --metrics --no-warmup --jinja --threads-batch 16 --predict 8192 --parallel 1 --reasoning-format auto --cache-prompt --cache-reuse 512 --split-mode layer --tensor-split 1,1 --spec-type draft-mtp --spec-draft-n-max 4` | HE0 válido; BCB infraestructura; repetir |
| BALANCE - Laguna S 2.1 118B-A8B Q2 | 1/1 | 20/20 | — | 16,980 s | 204,16 s | 56,93 s | 53,34 | — | 0,00 | No | — | UD-Q2_K_XL | 118B-A8B (≈8B activos) | 100000 | `launch=8d0dd2e0-c6c6-41ef-81d6-893c20d2f621; backend=b53df8bb-16b9-413d-8649-813e0a70d080; modelProfile=358edb77-0667-4190-b0e1-08654cb13864; runtimePreset=1b670632-3987-4047-be78-3efc93bb60d6; model=Laguna-S-2.1-UD-Q2_K_XL.gguf; mmproj=ninguno; agent=default del launch; binary=official,b10087+; runtime=ctx=100000,batch=2048,ubatch=768,threads=8,gpuLayers=999,slots=1,cache=q4_0,flash=on,cont=on,mmap=on,mlock=off; args=--cache-type-k q4_0 --cache-type-v q4_0 --fit on --split-mode layer --tensor-split 1,1 --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --jinja --threads-batch 16 --predict 4096 --parallel 1 --reasoning-format auto --reasoning-preserve --chat-template-file %LOCALAPPDATA%/LlamaCode/LlamaCode/chat-templates/laguna-tools-v24.jinja` | HE0 válido; BCB infraestructura (`Connection closed`); repetir |
| QUALITY - DeepSeek Fusion leloch | 1/1 | 20/20 | — | 70,903 s | 852,31 s | 716,23 s† | 8,53 | 9,15 | 0† | No | — | Q2/Q4 imatrix | 284B (≈13B activos) | 131072 | `launch=4f5cc556-333d-4310-955e-15042cd874d6; backend=1485cb47-757a-4a01-9f71-832567d01973; modelProfile=6ab3222e-5f71-442d-9eb9-7e895520befc; runtimePreset=20d4e6e6-9240-4926-9ea6-5bcea0eb2c50; model=DeepSeek-V4-Flash-Layers37-42Q4KExperts-OtherExpertLayersIQ2XXS...gguf; mmproj=ninguno; agent=agent-maximo (HE20 histórico agent-chat); binary=official,b10228+; runtime=ctx=131072,batch=4096,ubatch=1024,threads=8,gpuLayers=999,slots=1,cache=q4_0,flash=on,cont=on,mmap=on,mlock=off; args=--cache-type-k q4_0 --cache-type-v q4_0 --fit off --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --jinja --threads-batch 16 --predict 16384 --parallel 1 --reasoning-format auto --cache-prompt --split-mode layer --tensor-split 1,0 --override-tensor blk\.(37\|38\|39\|40\|41\|42)\.ffn_(gate\|up\|down)_exps\.weight=CUDA1,blk\.[0-9]+\.ffn_(gate\|up\|down)_exps\.weight=CPU --repeat-last-n 64 --flash-attn on --cpu-moe --cache-ram 32768` | HE0 válido; BCB sin cierre evaluable, repetir |
| QUALITY - DeepSeek Fusion leloch · VRAM balance | — | — | — | — | — | — | 8,81 | — | — | No | — | Q2/Q4 imatrix | 284B (≈13B activos) | 131072 | `launch=6b3bf7bd-0889-491a-9b6d-b12128478a5f; backend=07bf242d-0685-45d1-a752-11ddec6ef6df; modelProfile=0985be04-d2bc-455d-a3a5-e5fc19795e5d; runtimePreset=fdd4ca0a-3b8d-43a2-924b-092327aca314; model=DeepSeek-V4-Flash-Layers37-42Q4KExperts-OtherExpertLayersIQ2XXS...gguf; mmproj=ninguno; agent=agent-maximo (HE0 histórico agent-chat); binary=official,b10228+; runtime=ctx=131072,batch=4096,ubatch=1024,threads=8,gpuLayers=999,slots=1,cache=q4_0,flash=on,cont=on,mmap=on,mlock=off; args=--cache-type-k q4_0 --cache-type-v q4_0 --fit off --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --jinja --threads-batch 16 --predict 16384 --parallel 1 --reasoning-format auto --cache-prompt --split-mode layer --tensor-split 1,0 --override-tensor blk\.(0\|1)\.ffn_(gate\|up\|down)_exps\.weight=CUDA0,blk\.(37\|38\|39\|40\|41\|42)\.ffn_(gate\|up\|down)_exps\.weight=CUDA1,blk\.[0-9]+\.ffn_(gate\|up\|down)_exps\.weight=CPU --repeat-last-n 64 --flash-attn on --cpu-moe --cache-ram 32768` | Variante conservadora; HE0 histórico válido (67,039 s), requiere repetición con huella actual |

## Corrida vigente headless — 2026-08-17

Esta es la línea comparable para la implementación de la compuerta HE0 →
HE20 → BCB. Los tiempos están en segundos y los TPS son los reportados por el
harness. Cada fila se guardó con la huella SHA-256 de la configuración efectiva;
las huellas completas quedan en el registro de resultados de la aplicación.

| Perfil | HE0 | HE20 | BCB | Tiempo HE0 | Tiempo HE20 | Tiempo BCB | TPS HE0 | TPS HE20 | TPS BCB | Clasificación |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| BALANCE - Qwen3.8 UD-Q4 visión | 1/1 | 20/20 | 5/8 | 11,288 s | 237,507 s | 1430,390 s | 39,22 | 60,50 | 65,21 | BCB calidad; sin fallo de infraestructura |
| BALANCE - Qwen3.8 UD-Q4 MTP4 | 1/1 | 20/20 | 4/8 | 10,750 s | 262,737 s | 1507,487 s | — | 56,83 | 60,28 | BCB calidad; sin fallo de infraestructura |
| FAST - KAT2-Coder-7-8-26 | 1/1 | 20/20 | 3/8 | 15,817 s | 183,904 s | 401,169 s | 124,24 | 108,45 | 116,83 | BCB calidad; HE20 repetido tras reducir B512/U64 |
| FAST - KAT-Coder-7-8-26 | 1/1 | 20/20 | 3/8 | 17,102 s | 273,407 s | 639,302 s | — | 107,14 | 111,77 | BCB calidad; HE20 repetido tras reducir B512/U64 |
| FAST - BigBang · MTP · top-p 0.08 | 1/1 | 20/20 | 3/8 | 11,289 s | 222,185 s | 1055,693 s | — | 204,42 | 207,33 | BCB calidad; sin fallo de infraestructura |
| BALANCE - BigBang MTP | 1/1 | 20/20 | 3/8 | 11,266 s | 253,067 s | 406,496 s | — | 206,53 | 211,18 | BCB calidad; sin fallo de infraestructura |
| BALANCE - ThinkingCap Qwen3.6 MTP4 | 1/1 | 20/20 | 3/8 | 11,288 s | 118,098 s | 169,431 s | 48,21 | 61,96 | 52,04 | BCB calidad; sin fallo de infraestructura |
| BALANCE - ThinkingCap+MTP-7-8-26 | 1/1 | 20/20 | 3/8 | 10,265 s | 217,926 s | 401,922 s | 7,46 | 58,64 | 58,15 | BCB calidad; sin fallo de infraestructura |
| BALANCE - Laguna S 2.1 118B-A8B Q2 | 1/1 | 20/20 | 0/8 | 13,921 s | 341,545 s | 1041,378 s | 47,84 | 55,35 | 52,62 | BCB calidad; HE20 repetido tras reducir B512/U64 |
| QUALITY - DeepSeek Fusion leloch | 1/1 | 20/20 | 1/8 | 69,794 s | 802,656 s | 2397,063 s | — | 10,35 | 8,57 | BCB calidad; sin fallo de infraestructura |
| QUALITY - DeepSeek Fusion leloch · VRAM balance | 1/1 | 20/20 | 2/8 | 65,622 s | 775,223 s | 6328,761 s | — | 10,76 | 9,45 | BCB calidad; 2 reparaciones internas, sin crash/CUDA |

Los scores BCB menores que 8/8 son resultados válidos de calidad del modelo:
no se repiten ni se “arreglan” cambiando parámetros cuando el transporte, el
grader y el servidor terminaron correctamente. En cambio, las dos fallas HE20
iniciales de KAT y Laguna sí fueron de CUDA/infraestructura; se corrigieron los
presets a `batch=512, ubatch=64`, se repitió HE0 y luego HE20, y ambas quedaron
20/20. DeepSeek VRAM terminó `2/8` tras dos reparaciones internas; el límite de
generación fue del modelo durante una ejecución transportada, no un crash ni un
acceso ilegal de CUDA, por lo que se conserva como calidad.

La corrección de la fila BALANCE - BigBang se validó nuevamente en modo headless
después de recompilar el catálogo el 2026-08-17 con
`sys-repair-48-bigbang-mtp-balance`, corrida
`HumanEval_1_tems__20260817_001311`: **1/1 en 13,365 s**, `TPS HE0=10,72`, sin
reparación, crash ni cierre de transporte. La copia conserva MTP embebido, pero
usa `ctx=65536`, `batch=256`, `ubatch=64`, `flash-attn=on`, `KV=q8_0` y
sampling conservador; el perfil histórico 131k/Flash off queda archivado y no
se mezcla con esta medición.

HE0 de la variante actual: `HumanEval_1_tems__20260816_131714`, `1/1`, `67,039 s`, sin reparación ni fallo de infraestructura; `TPS HE0=8,81` es el timing nativo de `llama-server`. La corrida descartada anterior `HumanEval_1_tems__20260816_122210` usó `tensor-split=1,1` y falló al cargar por OOM en CUDA1; no se cuenta como calidad. La corrida histórica `HumanEval_1_tems__20260816_122508` también fue válida (`1/1`, `67,308 s`, `9,20 t/s`).

## Depuración del daemon y reparaciones BigBang (2026-08-16)

La intermitencia tenía dos causas independientes. Primero, las variantes BigBang originales combinaban contexto de 131k, batches altos y Flash Attention desactivado; en el equipo dual RTX 3090 se observaron `resource allocation failed` e `illegal memory access` dentro de CUDA. Segundo, los callbacks de `QProcess` de server/router consultaban el miembro global `m_proc`: durante un crash, una recarga o el teardown del benchmark ese miembro podía ya apuntar a otro proceso o ser nulo. El watchdog también podía relanzar el server mientras el benchmark todavía estaba cerrando la pasada, mezclando dos ciclos de vida.

La corrección en `AppController` captura el `QProcess` concreto con `QPointer` en cada callback, ignora señales tardías de procesos reemplazados y suprime el auto-restart del watchdog mientras el benchmark es dueño del ciclo de vida. En una ejecución manual el watchdog conserva la recuperación automática; durante un benchmark, el crash queda registrado como infraestructura y la pasada no se maquilla con un segundo server.

Los perfiles históricos no se sobrescribieron. Se agregaron copias de reparación con `ctx=65536`, `batch=256`, `ubatch=64`, `cache K/V=q8_0` y Flash Attention activado explícitamente. Las dos variantes MTP conservan `--spec-type draft-mtp --spec-draft-n-max 5`; la variante sin MTP elimina ambos argumentos. Sus IDs y nombres son:

| Perfil de reparación | ID | HE0 pasada 1 / 2 / 3 | Resultado |
|---|---|---:|---|
| REPAIR - BigBang · MTP · 64k · B256/U64 | `sys-repair-48-bigbang-mtp` | 19,673 / 13,090 / 11,463 s | 1/1 en 3/3; sin crash ni reparación |
| BALANCE - BigBang MTP | `sys-repair-48-bigbang-mtp-balance` | 11,480 / 13,056 / 11,468 s | 1/1 en 3/3; sin crash ni reparación |
| REPAIR - BigBang · sin MTP · 64k · B256/U64 | `sys-repair-48-bigbang-base` | 13,047 / 13,045 / 21,641 s | 1/1 en 3/3; sin crash ni reparación |
| FAST - KAT2-Coder-7-8-26 | `sys-48-katcoder-262k` | 19,606 / 14,993 / 16,058 s | 1/1 en 3/3; sin crash del daemon |

La evidencia de esta validación fría está en `benchmark-runs/HumanEval_1_tems__20260816_140058`. La primera pasada de KAT2 necesitó dos reparaciones del agente, pero las tres pasadas cerraron con `1/1` y no hubo `Connection closed`, crash nativo ni nuevo `APPCRASH` de LlamaCode. El último `APPCRASH` de `LlamaCode.exe` observado en Event Viewer corresponde a la ejecución previa, antes del binario recompilado y de la corrección de callbacks.

La reparación de BigBang es deliberadamente conservadora: primero demuestra estabilidad en HE0. Después de esa promoción, corresponde repetir HE20 y recién entonces BCB; no se deben mezclar los scores históricos de los perfiles originales con los de estas copias.

## Procedimiento de benchmarking

El orden es deliberado y se aplica a cada perfil base o candidato, siempre en modo headless y con el mismo harness, agente, semilla y criterios de reparación:

1. **HumanEval/0 (smoketest):** ejecutar una sola tarea. Verifica que el modelo, backend, plantilla, MTP/mmproj y transporte funcionen; registra `Calidad HE0` y `TPS HE0`. Un `server-load`, `server-crash`, `timeout`, conexión cerrada o respuesta sin cierre es un fallo de infraestructura, no calidad cero, y bloquea las etapas siguientes de ese perfil.
2. **HumanEval/20:** sólo después de HE0 válido para la misma configuración efectiva. Ejecutar las 20 tareas para medir calidad del perfil y del harness; registrar score, tiempo total y TPS. Si HE0 falló, no se ejecuta HE20: se investiga, se corrige y se repite HE0.
3. **BigCodeBench/8:** sólo después de HE0 y HE20 válidos —o como repetición explícita de una fila ya marcada— ejecutar las 8 tareas difíciles para medir tool-calls, reparaciones, loops y estabilidad sostenida; registrar score, tiempo total y TPS. Un score bajo con transporte, harness y grader funcionando es una medición válida del modelo y no obliga a cambiar ni repetir el perfil. Sólo un fallo de harness/infraestructura, carga, timeout sin progreso, conexión, crash o `CUDA illegal memory access` obliga a investigar, corregir y repetir BCB después de HE0.

La promoción de un perfil requiere pasar HE0. Un fallo de HE0 exige diagnóstico antes de cualquier HE20/BCB. En HE20 y BCB se separan los resultados válidos de calidad del modelo de las fallas de harness/infraestructura: las primeras se conservan aunque sean bajas; las segundas se corrigen y se repiten. Por eso no se mezclan `0/0` de infraestructura con una puntuación de inteligencia, y todo resultado queda anotado junto con la configuración efectiva usada.

La aplicación aplica esta compuerta en tiempo de ejecución mediante una huella
SHA-256 del comando efectivo: los HE0 históricos sin huella no habilitan HE20;
deben repetirse con el binario/harness actual. La verificación headless quedó
probada el 2026-08-16: solicitar HE20 para `sys-bench-48-kat-f16` sin HE0
compatible devolvió estado bloqueado y no arrancó ningún servidor.

## Revalidación de perfiles modificados por la política q8 — HE0 (2026-08-16)

Después de limitar los pesos y el KV K/V del catálogo a `q8_0` o menor, se
repitió el smoketest en modo headless para los 16 perfiles afectados, incluidos
los perfiles derivados que heredan el runtime del padre. La evidencia queda en
`benchmark-runs/HumanEval_1_tems__20260816_162242`. Estos resultados son una
nueva línea base: no se mezclan con tiempos tomados cuando el perfil usaba
`f16`.

| Perfil | ID | HumanEval/0 | Tiempo HE0 | TPS HE0 del agente | Estado |
|---|---|---:|---:|---:|---|
| `[bench 48GB KAT] KV q8_0 · 262k` | `sys-bench-48-kat-f16` | 1/1 | 16,267 s | 127,43 | Válido |
| `[bench antirez stress] 32k · B4096 · U512 · KV q8_0` | `sys-48-antirez-dsv4-q2q4-kvf16` | 1/1 | 75,781 s | — | Válido; sin tokens medibles del agente |
| `Fable Fusion Qwen3.6-27B Q6 · MTP · visión` | `sys-48-fablefusion-q6-mtp` | 1/1 | 11,419 s | 8,62 | Válido |
| `Fable Q6 · MTP 1 · 120k` | `sys-bench-48-fable-mtp1` | 1/1 | 12,871 s | 2,91 | Válido |
| `Fable Q6 · MTP 3 · 120k` | `sys-bench-48-fable-mtp3` | 1/1 | 10,315 s | — | Válido; sin tokens medibles del agente |
| `Fable Q6 · KV q8/q8 · MTP 3` | `sys-bench-48-fable-kv-q8` | 1/1 | 11,342 s | 35,37 | Válido |
| `Fable Q6 · sin MTP · 120k` | `sys-bench-48-fable-nospec` | 1/1 | 15,261 s | 16,39 | Válido |
| `BigBang-v1 35B-A3B Q4_K_M · visión` | `sys-48-bigbang-v1-q4km` | 1/1 | 10,349 s | 29,02 | Válido |
| `BigBang · 131k · sin MTP · KV q8_0` | `sys-bench-48-bigbang-base` | 1/1 | 11,761 s | — | Válido; sin tokens medibles del agente |
| `BigBang · 131k · MTP embebido · KV q8_0` | `sys-bench-48-bigbang-mtp` | 1/1 | 11,313 s | — | Válido; sin tokens medibles del agente |
| `BigBang · 131k · MTP · B1024/U256` | `sys-bench-48-bigbang-fast` | 1/1 | 11,291 s | — | Válido; sin tokens medibles del agente |
| `BigBang · 196k · MTP · KV q8_0` | `sys-bench-48-bigbang-long` | 0/1 | 15,260 s | 0,66 | Infraestructura: `Connection closed` y transporte sin cierre evaluable; repetir |
| `FAST - BigBang · MTP · top-p 0.08` | `sys-bench-48-bigbang-post` | 1/1 | 11,306 s | — | Válido; sin tokens medibles del agente |
| `REPAIR - BigBang · MTP · 64k · B256/U64` | `sys-repair-48-bigbang-mtp` | 1/1 | 11,283 s | 46,43 | Válido |
| `REPAIR - BigBang · sin MTP · 64k · B256/U64` | `sys-repair-48-bigbang-base` | 1/1 | 18,379 s | — | Válido; sin tokens medibles del agente |
| `BALANCE - BigBang MTP` | `sys-repair-48-bigbang-mtp-balance` | 1/1 | 12,851 s | 16,46 | Válido |

`TPS HE0 del agente` es el `avgTps` reportado por el harness para esta tanda;
cuando la respuesta fue evaluable pero no incluyó tokens de generación, se
deja `—` y no se inventa un throughput. La variante BigBang de 196k queda
fuera de la promoción hasta repetirla con transporte completamente cerrado.

La tanda HE20 posterior se canceló a pedido antes de iniciar BCB. En
`benchmark-runs/HumanEval_20_tems__20260816_163945` sólo alcanzó a completarse
`sys-bench-48-kat-f16`: `20/20` en `137,29 s`; los otros 15 perfiles quedaron
pendientes. Este resultado HE20 es válido como medición del perfil, pero no
promueve por sí solo a los restantes ni reemplaza sus resultados históricos.

## Candidatos derivados para medir

No se duplican manualmente los perfiles base. Se incorporan al plan las variantes ya existentes en el catálogo y dos variantes nuevas de Laguna. Cada fila sigue HE0 → HE20 → BCB; el HE0 de esta tanda ya fue ejecutado en modo headless y sus resultados están debajo.

| Candidato | Derivado de | Hipótesis | Cambio controlado | Orden |
|---|---|---|---|---|
| `[bench Qwen3.8] UD-Q4 · MTP2 · 64k · mmproj` (`sys-bench-qwen38-udq4-mtp2-64k`) | BALANCE - Qwen3.8 UD-Q4 visión | Menos contexto y MTP pueden mejorar velocidad/estabilidad | ctx 65k; MTP2; B512/U64 | HE0 → HE20 → BCB |
| `[bench Qwen3.8] UD-Q4 · MTP3 · B1024 · mmproj` (`sys-bench-qwen38-udq4-mtp3-b1024`) | BALANCE - Qwen3.8 UD-Q4 visión | Menor batch puede evitar fallos de infraestructura | B1024/U128; MTP3 | HE0 → HE20 → BCB |
| `[bench Qwen3.8] UD-Q4 · MTP3 · 131k · KV q8 · mmproj` (`sys-bench-qwen38-udq4-mtp3-kv8`) | BALANCE - Qwen3.8 UD-Q4 visión | KV q8 puede sostener mejor contexto y calidad | KV K/V q8_0 | HE0 → HE20 → BCB |
| `[bench Qwen3.8] Q4_K_M · MTP4 · 131k · mmproj` (`sys-bench-qwen38-q4km-mtp4`) | Qwen3.8-27B Q4_K_M visión | Comparar MTP4 sin cambiar quant/contexto | MTP4 | HE0 → HE20 → BCB |
| `[bench Qwen3.8] Q5_K_M · MTP3 · 64k · KV q8 · mmproj` (`sys-bench-qwen38-q5km-mtp3-64k-kv8`) | Qwen3.8-27B Q5_K_M visión | Más precisión/KV puede mejorar BCB a costa de velocidad | ctx 65k; KV q8_0 | HE0 → HE20 → BCB |
| `[bench 48GB KAT] KV q8_0 · 262k (cap de política)` (`sys-bench-48-kat-f16`) | FAST - KAT-Coder-7-8-26 | Repetir la variante histórica con la cota vigente | KV K/V q8_0 | HE0 → HE20 → BCB |
| `[bench BigBang] 131k · MTP · batch 1024 · ubatch 256` (`sys-bench-48-bigbang-fast`) | FAST - BigBang MTP | Mantener MTP y bajar presión de prefill para corregir `Connection closed` | B1024/U256; MTP5 | HE0 → HE20 → BCB |
| `[bench BigBang] 131k · sin MTP · KV q8_0` (`sys-bench-48-bigbang-base`) | BALANCE - BigBang MTP | Aislar si el fallo pertenece al MTP o al harness/modelo | MTP desactivado; KV q8_0 | HE0 → HE20 → BCB |
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
| `[bench 48GB KAT] KV q8_0 · 262k (cap de política)` | Pendiente | — | — | Resultado histórico con f16 archivado; repetir con q8_0 |
| `[bench BigBang] 131k · MTP · batch 1024 · ubatch 256` | — | 58,638 s | — | Infraestructura: server-load |
| `[bench BigBang] 131k · sin MTP · KV q8_0` | Pendiente | — | — | Resultado histórico con f16 archivado; repetir con q8_0 |
| `[bench 48GB MAX-Q] MTP4 · 131k · visión` | 1/1 | 11,498 s | 58,02 | Válido |
| `[bench Laguna] Q2 · 64k · B1024 · U256` | 1/1 | 15,004 s | 51,46 | Válido |
| `[bench Laguna] Q2 · 100k · B1024 · U256` | 1/1 | 13,961 s | 51,99 | Válido |
| `[bench antirez] 32k · B2048 · U256 · KV q4_0` | 1/1 | 93,540 s | 10,00 | Válido |
| `[bench antirez] 32k · B4096 · U512 · KV q8_0` | 1/1 | 76,189 s | 10,00 | Válido |

Evidencia de la tanda: `benchmark-runs/HumanEval_1_tems__20260816_130505` a `HumanEval_1_tems__20260816_133559`. Los 24 IDs fueron ejecutados aisladamente. KAT2 (`sys-48-katcoder-262k`) cargó y llegó a timing nativo de `103,93 t/s`, pero el daemon terminó en `APPCRASH` de `LlamaCode.exe` dentro de `Qt6Core.dll` antes de persistir el JSON; queda como `HE0 daemon-crash`, no como calidad.

Las variantes DeepSeek mantienen la regla de seguridad del perfil histórico: `--tensor-split 1,0`, expertos residentes alineados con sus capas y resto en CPU. No se propone `tensor-split 1,1`, porque la prueba local anterior terminó en OOM/corrupción y no es una mejora válida.

`*` En KAT2, `103,93 t/s` es timing nativo observado antes del `APPCRASH`; no hay JSON evaluable y debe repetirse.

`†` En DeepSeek, el tiempo/TPS de BCB es el último intento observado antes de cerrar la serie; la respuesta no tuvo cierre evaluable. Debe repetirse después de HE0/HE20 válidos del perfil o variante correspondiente.

La nota histórica de KAT2 que sigue a esta sección describe el fallo anterior; no invalida la repetición 3/3 documentada arriba.

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

### BALANCE - BigBang · MTP · top-p 0.08 (histórico)

```text
tablaName: BALANCE - BigBang · MTP · top-p 0.08
launchId: sys-bench-48-bigbang-mtp
internalName: [bench BigBang] 131k · MTP embebido · KV q8_0
backendProfileId: sysbe-sys-bench-48-bigbang-mtp
modelProfileId: sysmodel-sys-bench-48-bigbang-mtp
runtimePresetId: sysrt-sys-bench-48-bigbang-mtp
agentProfileId: agent-maximo
runtime: ctx=131072, batch=512, ubatch=128, threads=0, gpuLayers=999, parallelSlots=1, cache=q8_0, flashAttention=off, contBatching=on, mmap=on, mlock=off
mmprojId: 24152073-986a-5470-b717-a70861d14883
extraArgs: --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn off --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --jinja --parallel 1 --reasoning on --spec-draft-n-max 5 --spec-type draft-mtp
WARNING: el nombre visible de la tabla no coincide con el nombre interno ni con top-p 0.08. No publicar esta fila como definitiva hasta resolver la identidad.
```

### BALANCE - BigBang MTP

```text
launchId: sys-repair-48-bigbang-mtp-balance
internalName: BALANCE - BigBang MTP
agentProfileId: agent-chat
runtime: ctx=65536, batch=256, ubatch=64, threads=0, gpuLayers=999, parallelSlots=1, cache=q8_0, flashAttention=on, contBatching=on, mmap=on, mlock=off
mmprojId: heredado del BigBang-v1; visión disponible
extraArgs: --cache-type-k q8_0 --cache-type-v q8_0 --flash-attn on --temp 0.60 --top-p 0.95 --top-k 20 --min-p 0.0 --repeat-penalty 1.0 --presence-penalty 0.0 --no-context-shift --metrics --no-warmup --jinja --parallel 1 --reasoning off --spec-draft-n-max 5 --spec-type draft-mtp
HE0: 1/1, 13,365 s, TPS 10,72; sin reparación del agente, crash ni transporte truncado
```

La fila histórica no se sobrescribe: la copia reparada es la que queda
habilitada para repetir HE20 y luego BCB, siempre respetando la compuerta HE0.

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
