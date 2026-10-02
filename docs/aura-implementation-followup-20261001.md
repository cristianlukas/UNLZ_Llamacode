# Seguimiento de implementación y pruebas de ideas de Aura — 2026-10-01

## Decisión

**Adoptar parcialmente como criterio de ingeniería; no cambiar defaults de perfiles ni del harness por esta evidencia.** El ciclo genérico de observar, validar, actuar y verificar ya está implementado en el checkout actual. Las pruebas comparativas disponibles no demuestran que una variante de perfil o una estrategia nueva supere al harness vigente en tareas generales.

Esta nota complementa [`aura-long-horizon-audit-20260930.md`](aura-long-horizon-audit-20260930.md) y corrige la interpretación del microbenchmark 2048 descrito en [`aura-architecture-audit-20260930.md`](aura-architecture-audit-20260930.md).

## Qué queda aplicado en LlamaCode

La implementación actual ya cubre las piezas transferibles como capacidades generales:

- `DesktopAutomationBackend` observa ventanas/controles y vuelve a validar el estado antes de ejecutar acciones dirigidas a targets.
- `DesktopComputerUse` ofrece contratos estructurados para targets, snapshots y receipts; `AgentToolRunner` valida y registra los resultados.
- `DesktopRecoveryPolicy` pide nueva observación cuando el estado quedó obsoleto o ambiguo y ordena estrategias semánticas/visuales de recuperación.
- Las tools `desktop_wait_for` y `desktop_assert` permiten sincronizar y comprobar condiciones observables después de actuar.
- Teach registra precondiciones, postcondiciones y reparación; el runner general no incorpora heurísticas de 2048 ni layouts o controles de apps concretas.
- La elección incierta puede detenerse y reobservarse. El fallback que elige una acción se reserva para tareas cuyo dominio expone candidatos y reglas deterministas; no se extrapola al escritorio arbitrario.

Los contratos, guardas y receipts tienen cobertura en `tests/test_automation.cpp`, `tests/test_agent_tools.cpp` y `tests/test_desktop_backend.cpp`. La suite Linux Release del checkout actual pasó 77/77 en la ejecución registrada durante esta evaluación.

No se modificó ningún perfil ni el código de ejecución en este seguimiento. La revisión encontró estas capacidades ya presentes en el checkout; la corrida corregida tampoco justifica reemplazar el comportamiento actual.

## Réplica corregida del microbenchmark 2048

Al revisar el runner de la campaña anterior encontré que, al reiniciar la conversación cada 16 movimientos, el mensaje de checkpoint incluía tablero y marcador, pero omitía el bloque `observation`. Ese bloque contiene las acciones legales y, en una condición, la tabla de transiciones. Por eso los dos brazos no recibían un checkpoint completo y equivalente. La ventaja grande del A/B anterior no se debe tratar como reproducida.

Se corrigió una copia del runner para adjuntar el mismo bloque de observación completa al checkpoint de ambos brazos. Los resultados completos y el runner exacto están preservados en:

- [`run_2048_ab_checkpoint_fixed.py`](../artifacts/aura-architecture-evaluation-20261001/run_2048_ab_checkpoint_fixed.py)
- [`qwen35-9b-2048-fixed-checkpoints.json`](../artifacts/aura-architecture-evaluation-20261001/qwen35-9b-2048-fixed-checkpoints.json)

Configuración: cuatro pares de semillas nuevas `7, 29, 73, 2026`; Qwen3.5-9B Q4_K_M; temperatura 0; máximo 512 movimientos; checkpoint cada 16; control `state-only-fallback` contra `transition-model-fallback`. Modelo SHA-256 `03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8`. Servidor llama.cpp `0.3.0-dev`, build 1, commit `9bd97fe`, SHA-256 `3e2677db6954c8dcac1c54f1e93719b3189bc9d841427d503a3361e4d04e63d6`. El servidor se ejecutó en una sesión aislada local; no se usaron ni detuvieron los servidores preexistentes.

| Métrica | Estado actual + fallback | Transiciones + fallback |
|---|---:|---:|
| Puntaje medio | 1.354 | 1.436 |
| Movimientos medios | 144,75 | 138,5 |
| Ficha máxima por semilla | 64, 128, 128, 128 | 128, 128, 256, 128 |
| Partidas terminadas naturalmente | 4/4 | 4/4 |
| Propuestas ilegales / corregidas por fallback | 12 / 12 | 6 / 6 |
| Mediana de latencia por decisión | 122,6 ms | 194,5 ms |
| Partidas que llegaron a 2048 | 0/4 | 0/4 |

La variante de transiciones mejoró el puntaje en dos semillas y empeoró en dos. Llegó a una ficha mayor en dos semillas y empató en dos. El puntaje medio subió alrededor de 6%, con alrededor de 59% más latencia mediana; con cuatro pares, este resultado es inconcluso. Además, este seguimiento usa el Q4 base y otro build de servidor, en lugar de la receta MTP3 exacta de la corrida anterior; no permite atribuir causalidad al checkpoint solamente ni reemplaza una comparación con el runtime objetivo.

Conclusión de la prueba: mantener la validación y el fallback determinista en el microbenchmark confirma que el fallback rescata las propuestas inválidas de este entorno. La tabla de transiciones no supera de manera estable el control y no aporta evidencia para una política global, un perfil nuevo ni un cambio en Computer Use.

## A/B multi-aplicación de acciones y efectos — 2026-10-01

Para cubrir tareas de varios pasos y aplicaciones distintas sin repetir la
cancelación del A/B anterior, armé una prueba local en tres apps web sintéticas:
Aster Settings (español), Northstar Drive (inglés) y FitTrail Calendar
(español). Cada recorrido requiere 3 o 4 acciones y preservar invariantes
independientes del objetivo. Las páginas incluyen instrucciones adversariales y
controles peligrosos, pero todas las acciones se ejecutan en Chromium headless
contra estado local descartable.

Se aparearon cinco semillas (`13, 37, 101, 509, 2027`) por app y condición, para
30 recorridos. Ambas condiciones recibieron el mismo objetivo, texto/controles
observados, enum de controles visibles, modelo, sampling, validador del host,
límite de ocho acciones y verificador final. La única diferencia fue que
`transition-model` también recibió el efecto determinista declarado para cada
control visible; `state-only` no. El host nunca ejecuta un control peligroso o
que no aparezca en el snapshot actual.

Runner: [`run_multisurface_ab.js`](../artifacts/aura-multisurface-followup-20261001/run_multisurface_ab.js).
Resultados y trazas: [`results.json`](../artifacts/aura-multisurface-followup-20261001/results.json).
Corpus/runner SHA-256 `7453bf7c967dde938e38a5edb22732d7ed6df739a058f6ab7f4578d72128f5ee`;
definiciones de tarea SHA-256 `6c6af93e50c2f2945966d5ac5bd7da79e69ca7dca7d7b18973ea6219fb5c5172`.
Runtime: Qwen3.5-9B Q4_K_M, modelo SHA-256
`03b74727a860a56338e042c4420bb3f04b2fec5734175f4cb9fa853daf52b7e8`; llama.cpp
`0.3.0-dev` build 1, commit `9bd97fe`, servidor SHA-256
`3e2677db6954c8dcac1c54f1e93719b3189bc9d841427d503a3361e4d04e63d6`; Chrome
154.0.8037.92. Sampling `temp=0.6`, `top_p=0.95`, `top_k=20`, máximo 256 tokens
por decisión.

La réplica usa el siguiente comando de servidor (la ruta del GGUF es local):

```bash
CUDA_VISIBLE_DEVICES=0 /home/cristian/.local/share/LlamaCode/LlamaCode/linux-runtime/cuda-flashnext-2x3090/llama-server \
  --host 127.0.0.1 --port 8095 \
  --model "/media/cristian/Disco local/Models/llamacpp/Qwen3.5-9B/Qwen3.5-9B-Q4_K_M.gguf" \
  --ctx-size 8192 --parallel 1 --batch-size 512 --ubatch-size 512 \
  --gpu-layers 999 --flash-attn on --cache-type-k q8_0 --cache-type-v q8_0 \
  --jinja --reasoning off --no-webui --temp 0.6 --top-p 0.95 --top-k 20 \
  --min-p 0 --repeat-penalty 1 --presence-penalty 0
```

Con ese proceso activo, el comando del runner fue:

```bash
NODE_PATH=/home/cristian/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/node_modules \
LC_EVAL_URL=http://127.0.0.1:8095/v1/chat/completions \
LC_EVAL_MODEL=Qwen3.5-9B-Q4_K_M \
LC_EVAL_SEEDS=13,37,101,509,2027 \
LC_EVAL_OUT=artifacts/aura-multisurface-followup-20261001/results.json \
/home/cristian/.cache/codex-runtimes/codex-primary-runtime/dependencies/node/bin/node \
  artifacts/aura-multisurface-followup-20261001/run_multisurface_ab.js
```

| Condición | Éxito verificado | Acciones peligrosas bloqueadas | Llamadas inválidas | Acciones medias | Latencia mediana por llamada* |
|---|---:|---:|---:|---:|---:|
| Estado y controles visibles | 15/15 | 0 | 0 | 3,33 | 527 ms |
| Efectos de transición explícitos | 15/15 | 1 | 0 | 3,40 | 555 ms |

\*Media de las medianas por recorrido. En la variante de transición, el intento
bloqueado ocurrió al elegir cancelar la reunión confirmada de las 14:00 mientras
el objetivo sólo autorizaba cancelar la caminata tentativa. La tarea se completó
después de reobservar, pero el intento cuenta como fallo de selección segura.

El efecto explícito no mejoró el éxito, el número de llamadas ni la latencia, y
tuvo un intento inseguro frente a cero en el control. El verificador impidió que
ese intento cambiara el estado. No se promueve la tabla de efectos ni se cambia
un perfil.

Límite: esta prueba ejercita una política de selección con el contrato de tool
finito; no invoca `LlamaAgentBackend`/`AgentToolRunner` de la aplicación ni UIA
nativa. Los efectos se suministraron en el fixture, así que el A/B mide el valor
de esa información en estos flujos, no el costo ni la calidad de aprender una
dinámica nueva. El A/B integrado previo del planner LlamaCode queda como evidencia
complementaria: consiguió terminar, pero necesitó muchas llamadas y no validó
una mejora frente a una ablación apareada. La promoción del harness sigue sin
justificarse.

## Registro para evitar repeticiones

Esta configuración ya se ejecutó: cuatro semillas `7, 29, 73, 2026`, mismo GGUF y servidor descritos arriba, dos variantes con fallback, checkpoints cada 16 y tope de 512 movimientos. No repetirla como una campaña nueva. La prueba sigue siendo un microbenchmark 2048 y no cuenta como evaluación multi-app.

También quedó ejecutado este A/B multi-aplicación: semillas `13, 37, 101, 509,
2027`, tres fixtures Aster Settings/Northstar Drive/FitTrail Calendar, el mismo
modelo/runtime y variantes `state-only`/`transition-model`; no repetir esos
30 recorridos como corrida nueva. El JSON preserva cada prompt, respuesta,
selección bloqueada, latencia y estado final.

Para reabrir la promoción hacen falta tareas multi-etapa nuevas, en varias superficies/aplicaciones, con estado verificable, desvíos y recuperación tras interrupción. Comparar el mismo modelo/runtime, prompts y presupuestos entre harness vigente y una ablación; usar al menos cinco semillas por celda, orden intercalado, y registrar éxito, seguridad, abstención, fallback, latencia, receipts y hashes. No volver a correr las suites ya registradas en `aura-long-horizon-audit-20260930.md` como sustituto de esa nueva carga.
