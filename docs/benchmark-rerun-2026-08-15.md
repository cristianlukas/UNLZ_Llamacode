# Repetición headless de HumanEval/20 — 2026-08-15

## Alcance

Se cancelaron las corridas interrumpidas y se intentó repetir únicamente la
selección de perfiles mostrada en las capturas del usuario. La ejecución se
hizo contra el build Debug actualizado, sin abrir ni controlar la interfaz:

- ejecutable: `build/Debug/LlamaCode.exe`
- modo: `--headless`
- ControlApi: `http://127.0.0.1:8876`
- suite: `HumanEval (20 ítems)`
- benchmark custom: `267bb33d-4510-417b-ae3c-6dbbfb2cb08d`
- objetivo: `agent`
- agente: `agent-chat` / `Chat liviano`
- pasadas: 1 por perfil
- límite duro: 1200 segundos por perfil en la última tanda

La orden lógica enviada al daemon fue equivalente a:

```powershell
$body = @{
  method = 'startCustomBenchmark'
  args = @($profileIds, '267bb33d-4510-417b-ae3c-6dbbfb2cb08d', 1,
           'agent', 1200, 'agent-chat')
} | ConvertTo-Json -Depth 8
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8876/invoke' `
  -ContentType 'application/json' -Body $body
```

La lista seleccionada fue:

```text
sys-48-katcoder-262k
sys-48-thinkingcap-mtp
sys-laguna-s-2-1-q2-48gb
sys-qwen38-27b-udq4-131k
9dda6bf4-7aae-4806-ba3a-8466bf41e702
cbff7c85-2116-4b42-b1b9-485dd33384cc
a03e65f5-2f2c-4d45-b67b-4b1270fa2a6c
8d0dd2e0-c6c6-41ef-81d6-893c20d2f621
4f5cc556-333d-4310-955e-15042cd874d6
sys-bench-48-bigbang-post
sys-bench-qwen38-udq4-mtp4
sys-qwen38-27b-q4km-131k
sys-qwen38-27b-q5km-131k
```

## Última medición válida disponible por perfil

Estos son los últimos registros con una medición cuantificable. Un resultado
de calidad inferior a 20/20 se conserva como dato válido; los fallos de carga,
crash o timeout no se consideran mediciones de calidad.

| Perfil | HumanEval/20 | Tiempo |
|---|---:|---:|
| KAT-Coder-7-8-26 | 20/20 | 307,78 s |
| ThinkingCap+MTP-7-8-26 | 20/20 | 197,10 s |
| Laguna S 2.1 118B-A8B Q2 | 20/20 | 204,16 s |
| Qwen3.8 UD-Q4 visión | 20/20 | 269,96 s |
| FAST-KAT-Coder-7-8-26 | 20/20 | 212,69 s |
| FAST-BigBang MTP top-p 0.08 | 1/20 | 344,57 s |
| ThinkingCap Qwen3.6-27B MTP4 | 20/20 | 174,96 s |
| DeepSeek Fusion leloch | 1/20 | 2231,29 s |
| BigBang MTP top-p 0.08 | 1/20 | 395,65 s |
| Qwen3.8 UD-Q4 MTP4 | 20/20 | 332,12 s |
| Qwen3.8-27B Q4_K_M visión | — | Sin medición válida |
| Qwen3.8-27B Q5_K_M visión | — | Sin medición válida |

## Resultado de la última tanda headless

La última tanda quedó registrada en:

```text
%LOCALAPPDATA%\LlamaCode\LlamaCode\benchmark-runs\HumanEval_20_tems__20260815_193802
```

Resultados nuevos confirmados:

- `sys-48-katcoder-262k`: **20/20**, 307,78 s.
- `sys-48-thinkingcap-mtp`: fallo de infraestructura `server-crash`, sin score.
- `sys-laguna-s-2-1-q2-48gb`: comenzó, pero quedó atascado en el primer prompt y fue cancelado.

Los perfiles posteriores de la cola no se ejecutaron en esa tanda porque se
canceló la serie al detectar el atasco de Laguna. El daemon terminó con:

```text
benchmarkRunning=False
serverRunning=False
serverState=stopped
benchmarkStatus=Cancelado.
```

## Diagnóstico de los fallos

En Laguna y en el intento anterior con Qwen visión se observaron entradas
repetidas en `.llamacode/agent_events.jsonl`:

```text
kind=benchmark_acceptance_probe
score=0
total=20
hardFailed=true
```

Se generaba aproximadamente una entrada por segundo sin completar el turno ni
avanzar de prompt. Esto no es un score de calidad confiable: es un backend que
queda activo sin producir una respuesta final.

En los logs del servidor también aparecieron reinicios/watchdog y procesos que
terminaron con código `62097`. Esos casos se clasifican como infraestructura,
no como “el modelo obtuvo 0/20”.

El arreglo incluido en el commit `7ba1956` mantiene el aislamiento entre
pasadas: detiene y vuelve a cargar el servidor antes de cada pasada repetida, y
reconoce marcadores de reinicio del backend como errores de infraestructura.
La validación del código fue `tests.bat Debug`: **52/52 pruebas aprobadas**.

## Pendientes

- Repetir Qwen3.8-27B Q4_K_M visión y Q5_K_M visión en una tanda aislada.
- Repetir los perfiles que quedaron después de Laguna, preferentemente uno por
  uno para que un crash no cancele la cola completa.
- Investigar por qué ciertos backends dejan el agente en un acceptance probe
  infinito antes de considerar esos resultados comparables.
