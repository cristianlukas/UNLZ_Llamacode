# Q127 · traza de memoria/PSI real de SOL en dual 3090

## Pregunta y alcance

Q34 ya completó 30/30 solicitudes de velocidad en el perfil SOL, pero no guardó PSI continua. Esta prueba añade telemetría a **una sola** solicitud de prompt-copy de ~24K tokens en el mismo perfil SOL TP=2, sin comparar velocidades ni reabrir calidad/adopción. El punto es separar RAM del host, cgroup, PSI y VRAM durante una ejecución real.

No se cambia SOL, ASTRA, Flash-Next, PeritoSoft, pesos, firmware, RAM ni swap. No se crea presión artificial. Se levanta un único contenedor de evaluación Q127 en loopback; cleanup sólo puede retirar ese proyecto/contenedor.

## Perfil congelado

- SOL productivo de Q34: Qwen3.8-27B Frozenlock AutoRound INT4/W4A8, vLLM `v0.27.1`, TP=2 en ambas RTX 3090, `MAX_MODEL_LEN=262144`, `GPU_MEMORY_UTILIZATION=0.90`, `MAX_NUM_SEQS=8`, `MAX_NUM_BATCHED_TOKENS=8192`, `SPEC_N=4`, `W4A8=1`, `ENABLE_THINKING=true` y sampling server-side ya fijado.
- Un request determinista prompt-copy 24K derivado de Q34, respuesta máxima 256 tokens; aceptar sólo `20.000 <= prompt_tokens <= 30.000`. No guardar el texto de respuesta.
- Contenedor de evaluación separado, puerto `18117`, memoria cgroup `96g`, swap cgroup `97g`, misma compose base/override de Q34. No reutiliza ni detiene el servicio productivo.

## Preflight y monitor

Antes de levantar el contenedor: lock Q127 propio; Q121 valida hash del runner y AMD05 antes de `Popen`; no debe existir otro proceso/contenedor/listener de inferencia; MemAvailable ≥80 GiB; SwapFree ≥1 GiB; ambas RTX 3090 visibles y <80 °C; Docker con ≥8 GiB libres; hashes de compose y siete shards SOL iguales a Q34. Cualquier gate falla = no iniciar y registrar bloqueo, sin retry.

Monitor a 1 Hz desde antes de iniciar el contenedor: MemAvailable, SwapFree, PSI global `some/full avg10`, OOM global, RSS del árbol/cgroup, `memory.current/events/swap.current` y uso/temperatura/VRAM por GPU. AMD05: no detener por RSS alto aislado; parada inmediata ante `MemAvailable<32 GiB` u OOM del worker/global; PSI global `full>=60% OR some>=80%` **más** `MemAvailable<48 GiB` por 15 muestras consecutivas; parada ante OOM/swap cgroup nuevo. Warning PSI moderado queda sólo registrado.

La app gráfica u otros procesos CUDA no se matan; sólo se comprueba la ausencia de inference servers. Si aparece un servidor ajeno, no se inicia la prueba.

## Criterio de decisión y límites

PASS operacional: Q121 PASS, request HTTP 200 dentro del rango de tokens, trace completa, guard sin abortar, cero OOM/swap nuevo y cleanup Q127 limpio. Reportar por separado RSS, MemAvailable, PSI y VRAM; una corrida no valida calidad ni predice todos los cierres de Codex. Si RAM queda holgada o PSI=0, eso confirma que esta carga concreta no sometió el stop crítico a prueba real.

## Resultado

Completado: request SOL PASS y 157 muestras de telemetría; no hubo hard-stop, OOM ni swap. Min MemAvailable 99,973 GiB; PSI global avg10 máxima 0,9%; RSS árbol 12,421 GiB; pico cgroup 15,577 GiB; VRAM 24.080/23.972 MiB; 63 °C máximo. El resumen del primer runner marcó fallo sólo por dos sockets TIME_WAIT, no por un listener: A02 cambió el chequeo a socket LISTEN y A03 corrigió el loader del test CPU. Regresión del puerto PASS, cleanup final reconciliado y no se repitió inferencia. AMD05 sigue candidate-only; Q127 no alcanzó presión crítica y no prueba sensibilidad real del hard-stop. Ver `RESULTS.md` y `receipts/result-analysis.json`.
