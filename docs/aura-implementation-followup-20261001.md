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

## Registro para evitar repeticiones

Esta configuración ya se ejecutó: cuatro semillas `7, 29, 73, 2026`, mismo GGUF y servidor descritos arriba, dos variantes con fallback, checkpoints cada 16 y tope de 512 movimientos. No repetirla como una campaña nueva. La prueba sigue siendo un microbenchmark 2048 y no cuenta como evaluación multi-app.

Para reabrir la promoción hacen falta tareas multi-etapa nuevas, en varias superficies/aplicaciones, con estado verificable, desvíos y recuperación tras interrupción. Comparar el mismo modelo/runtime, prompts y presupuestos entre harness vigente y una ablación; usar al menos cinco semillas por celda, orden intercalado, y registrar éxito, seguridad, abstención, fallback, latencia, receipts y hashes. No volver a correr las suites ya registradas en `aura-long-horizon-audit-20260930.md` como sustituto de esa nueva carga.
