# Runbook — Comparativa de los 5 NIVELES de agente (handoff)

Handoff para continuar (IA o persona) la medición **tiempo + calidad** de las
respuestas del agente a través de los 5 niveles, sobre una tarea autocontenida.
Todo se maneja **headless** vía ControlApi (ver `docs/control-api.md`).

## Objetivo

Medir, para un mismo modelo (perfil de inferencia **MAX-Q**), cómo varían **tiempo**
y **calidad** según el **NIVEL de agente** (capacidades + directivas + MCP):

| Nivel (agentProfileId) | tools | directivas | MCP |
|---|---|---|---|
| `agent-chat` (Chat liviano) | 5 (read/list/grep/write/edit) | — | off |
| `agent-basico` | core 7 | — | on |
| `agent-intermedio` | 10 | discipline | on |
| `agent-avanzado` | 16 | discipline/testNet/projectContext/efficiency/style | on |
| `agent-maximo` | todas (`*`) | todas menos opt-in puras | on |

**Hipótesis a validar/refutar:** en una tarea AUTOCONTENIDA (un HTML single-file,
sin repo/búsqueda/web), el nivel mínimo **Chat liviano gana en tiempo y calidad**;
los niveles altos agregan latencia (más contexto/atención) y se distraen
sobre-ingenierizando (testNet→escribe tests, projectContext→lee memoria, tools/MCP
irrelevantes), sin upside de calidad. Ver el presupuesto de contexto por nivel en
`tests/test_appcontroller.cpp::agentLevels_contextBudgetLadder` y `[[agent-levels-context-budget]]`.

## Tarea (EvalSuite)

`assets/eval/snake_retro_singlefile.json` — “Snake retro, un HTML autocontenido con
CSS+JS, estética NES/8-bit”. Es el prompt real del usuario.

> ⚠️ **Acceptance demasiado estricta (corregir).** La acceptance actual exige varios
> substrings A LA VEZ (incluye `requestAnimationFrame`). Un Snake válido que use
> `setInterval` “falla” → el benchmark dispara su **bucle de reparación** (gen + hasta
> 2 repairs), triplicando el tiempo por nivel y metiendo falsos negativos. **Antes de
> correr, aflojá la acceptance** a marcadores mínimos que cualquier Snake jugable
> cumpla (p.ej. `<canvas`, `getContext`, `keydown`, `score`) — sin exigir el método de
> loop concreto. Objetivo: que un buen Snake pase en la primera, sin repair.

## Identificadores (verificar, pueden cambiar)

- **MAX-Q launchId**: `5c3d9bda-8810-4331-a770-1c981461fe17`
  (alias “MAX Q QWEN”, `1_Llama.cpp_Qwen_27b_Q4XS_262k_Q4kv_MTP_NGRAM_MMPROJ`).
  Reconfirmá con `POST /invoke {"method":"launchMenu","args":[]}`.
- **Modelo**: Qwen3.6-27B-MTP-IQ4_XS, **ctx 262144**, KV q4, MTP+ngram spec,
  mmproj (visión). GGUF en `D:/Models/llamacpp/Qwen3.6-27B-MTP-IQ4_XS-GGUF/`.
- **Niveles**: `agent-chat`, `agent-basico`, `agent-intermedio`, `agent-avanzado`, `agent-maximo`.
- ControlApi en `http://127.0.0.1:8765` (env `LLAMACODE_CONTROL_PORT`).

## ⛔ Consideración #1 — VRAM (esto te va a frenar)

El 27B con **262k de contexto** entra **justo** en una 3090 de 24 GB **solo si la GPU
está vacía** (~50 t/s). Cualquier otra app que use VRAM (navegadores, EdgeWebView,
Claude/Codex/Antigravity desktop, Steam/Epic/Xbox, etc.) empuja el KV/compute a la
**“shared GPU memory” de Windows (RAM por PCIe)** → CUDA no da OOM, **decodifica a ~1 t/s**
(15× más lento, y peor a medida que crece el KV).

**Antes de cargar el modelo:**
```bash
nvidia-smi --query-gpu=memory.used,memory.total --format=csv,noheader
```
Querés **>20 GB libres** (used < ~3–4 GB). Si no, cerrá apps que usen GPU:
```bash
nvidia-smi --query-compute-apps=pid,process_name --format=csv,noheader
```
Baseline sano confirmado: corridas viejas del mismo setup dieron **avgTps 56–70 t/s**.
Si tras cargar medís ~3 t/s o menos, **es VRAM** (no el harness): liberá y reintentá.

## Otras consideraciones / gotchas

- **`startServer abort: No model selected`** (en `logs/server.log`, `serverState` queda
  `stopped`): el modelo no está catalogado esta sesión →
  `POST /invoke?target=rootRegistry {"method":"scanAll","args":[]}`, esperar `scanning=false`, reintentar.
- **El agente no arranca solo** si usaste `startServer` suelto: llamá `startAgent(launchId)`
  cuando `serverState=="running"` y `agentRunning` siga `false`.
- **`/prop` devuelve `value`**, `/invoke`/`/setprop` devuelven `result`/`ok`. No confundir.
- **Benchmark de agente sin server+agente cargado** → corre en ~0s con `qualityScore 0`
  (no hay agente). Cargá TODO antes.
- Quedó un resultado basura (Snake `qualityScore 0/0`, ~0.17s) de un intento sin server:
  borralo con `removeBenchmarkResultById(id)` o filtralo por timestamp.

## Procedimiento (PowerShell)

```powershell
$base="http://127.0.0.1:8765"; $id="5c3d9bda-8810-4331-a770-1c981461fe17"
function Inv($m,$a){ Invoke-RestMethod "$base/invoke" -Method Post -ContentType application/json -Body (@{method=$m;args=$a}|ConvertTo-Json -Compress) }
function Prop($n){ (Invoke-RestMethod "$base/prop?name=$n").value }   # .value !

# 0) VRAM > 20 GB libre (ver arriba). Si no, cerrar apps.

# 1) cargar modelo + agente
Inv "startServerAndAgent" @($id)
while ((Prop "serverState") -ne "running") { Start-Sleep 3 }   # ~30-60s
if (-not (Prop "agentRunning")) { Inv "startAgent" @($id); Start-Sleep 3 }

# 2) PROBE de velocidad ANTES de gastar horas: querés ~40-60 t/s
#    (POST directo al server llama.cpp, lee timings.predicted_per_second)
$probe = Invoke-RestMethod "http://127.0.0.1:8021/v1/chat/completions" -Method Post `
  -ContentType application/json -Body '{"messages":[{"role":"user","content":"Conta del 1 al 50 separados por coma."}],"max_tokens":120,"stream":false,"cache_prompt":false}'
$probe.timings.predicted_per_second    # < ~10 => abortar, es VRAM

# 3) importar la suite (con acceptance YA aflojada)
$custom = (Inv "importEvalSuite" @("C:/Users/cristian/Documents/LlamaCode/assets/eval/snake_retro_singlefile.json")).result

# 4) correr los 5 niveles; capturar el resultado más nuevo por timestamp
$levels = "agent-chat","agent-basico","agent-intermedio","agent-avanzado","agent-maximo"
$out = @()
foreach ($lvl in $levels) {
  Inv "startCustomBenchmark" @(@($id), $custom, 1, "agent", 1800, $lvl)
  Start-Sleep 5
  while ((Prop "benchmarkRunning")) { Start-Sleep 15 }   # ~4-6 min/nivel a 50 t/s sin repair
  $r = (Prop "benchmarkResults" | Where-Object { $_.runLabel -like "*Snake*" } | Sort-Object timestamp -Desc)[0]
  $out += [ordered]@{ level=$lvl; q="$($r.qualityScore)/$($r.qualityTotal)"; sec=$r.elapsedSec; tps=$r.avgTps; ttft=$r.avgTtftMs; files=$r.agentFiles; runDir=$r.runDir }
}
$out | ConvertTo-Json -Depth 6
```

## Qué reportar (por nivel)

`qualityScore/qualityTotal`, `elapsedSec`, `avgTps`, `avgTtftMs`, `agentFiles` (¿escribió
1 HTML o se fue a tests/archivos extra?), y abrir el HTML de `runDir` para juzgar calidad
real (jugable, retro, single-file). Armar tabla y contrastar con la hipótesis: ¿Chat
ganó tiempo y calidad? ¿los niveles altos sobre-ingenierizaron / tardaron más?

## Estado actual (2026-06-29)

- **Incompleto, 0 niveles capturados.** El primer intento (agent-chat) entró en bucle de
  reparación bajo **contención de VRAM** (~1–3 t/s) y se canceló.
- Causa raíz confirmada: VRAM saturada por otras apps. Tras liberarla quedó **756 MiB
  used / 24 GB (1%)** → recargar limpio y **probar t/s antes** de las 5 corridas.
- Pendiente: (1) aflojar acceptance del suite; (2) re-cargar MAX-Q con GPU libre;
  (3) PROBE t/s ≈ 50; (4) correr los 5 niveles; (5) borrar el resultado basura 0/0;
  (6) tabla final + veredicto.
- Driver de referencia (efímero, en scratchpad): replicá los comandos de arriba.
