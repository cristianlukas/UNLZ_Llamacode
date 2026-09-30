# Aura: auditoría de ideas para LlamaCode — 2026-09-30

## Decisión

No cambiar perfiles, sampling, harness, Computer Use ni Ingi Charla a partir del
post. La demostración de 2048 y los resultados descritos son un reporte del autor;
no aportan un protocolo público apareado contra nuestros perfiles, semillas,
hardware, fallos y métricas. El código/documentación públicos de Aura sí son
útiles para inspirar una futura prueba de autonomía prolongada con ablaciones.

La idea de que parte del trabajo cognitivo viva en software ya está reflejada en
LlamaCode: `MemoryStore` y `GraphStore`, `KnowledgePacket`, checkpoints de
contexto, `AgentProgressGovernor`, historial de corridas y herramientas de
control del escritorio con evidencia y permisos. No se justifica duplicar esos
mecanismos ni añadir un planificador universal de estados del escritorio sin un
A/B que pruebe una mejora transversal.

## Qué se revisó

- Post y demo mencionados por el usuario: [publicación de Aura en r/vibecoding](https://www.reddit.com/r/vibecoding/). La cifra de 28:41, el resultado 2048
  y el comportamiento descrito se tratan como afirmaciones del autor, no como
  resultados reproducidos por LlamaCode.
- Código/documentación: [repositorio público de Aura](https://github.com/youngbryan97/aura), en particular
  [`HOW_IT_WORKS.md`](https://raw.githubusercontent.com/youngbryan97/aura/main/HOW_IT_WORKS.md)
  y [`EVALUATE_AURA.md`](https://raw.githubusercontent.com/youngbryan97/aura/main/EVALUATE_AURA.md).
  La guía de evaluación propone pruebas que puedan fallar y menciona ablaciones
  de módulos como MCTS, memoria, actualización de estado y gates de autoridad.
  Su explicación de límites también distingue mecanismos implementados,
  simulaciones y afirmaciones que no considera probadas. La lectura del repo no
  valida independientemente las afirmaciones de la demo.
- Evidencia local, sin repetir corridas equivalentes:
  - [`computer-use-sandwich.md`](computer-use-sandwich.md): A/B de tres órdenes
    de prompt en Qwen3.5-9B y otros controles, incluyendo un corpus adversarial.
  - [`swift-genesis-qwen38-evaluation-20260929.md`](swift-genesis-qwen38-evaluation-20260929.md)
    y sus JSON: suite de Computer Use de 48 tareas, 720 requests intercalados,
    exactitud/validez/seguridad/transporte de 100% para las tres variantes;
    el sandwich queda 21,5% más lento en mediana que state-first en esa corrida.
    El contrato de tools tuvo 5/5 pasadas. El candidato falló BCB8 con 2/8 en
    LC-H1 y no se promovió. Sus GGUF ya se borraron.
  - [`harness.md`](harness.md), [`agent-efficiency.md`](agent-efficiency.md),
    [`managed-agent-runs.md`](managed-agent-runs.md) y las pruebas de
    `AgentProgressGovernor` y `MemoryStore` describen controles que ya cubren
    progreso medible, replanteo/corte por estancamiento, memoria por scope,
    checkpoints y corridas durables.
  - [`ingicharla-local-voice-audit-20260918.md`](ingicharla-local-voice-audit-20260918.md):
    Charla ya separa STT, LLM y TTS; la falta de una comparación acústica
    reproducible impide cambiar sus motores.

## Evaluación por idea

| Idea de Aura | Estado en LlamaCode | Decisión |
|---|---|---|
| El software alrededor del LLM aporta razonamiento persistente | Memoria, grafo, paquete de conocimiento, tools, checkpoints y verificación ya cumplen partes concretas de esa función. | Conservar la arquitectura actual; evaluar mecanismos por ablación, no por cantidad de módulos. |
| Mantener el objetivo durante una tarea larga y replanificar | Governor, objetivos de corrida, checkpoints y resume están implementados y probados. La suite de Computer Use actual elige una acción por estado y no mide una sesión autónoma de 29 minutos. | La brecha es una evaluación de larga duración, no un cambio inmediato al perfil. |
| Aprender dinámicas y buscar sobre estados futuros, por ejemplo en 2048 | No existe evidencia local de que un modelo/world-model específico gane a reglas de transición verificables para un dominio acotado. La automatización general requiere funcionar entre apps, resoluciones, idiomas y layouts. | No añadir heurísticas de 2048 ni un planificador específico al motor general. Crear primero un benchmark de investigación aislado. |
| Dar al modelo sólo acciones válidas y abstenerse si no puede justificar una | Las tools tienen schemas, validación de argumentos, permisos, guardias semánticas y aprobación. La suite de Computer Use verifica selección correcta en estados discretos, pero no cubre aún una acción inválida ni el abstenerse cuando no hay acción segura. | Candidato de prueba para una suite futura; no cambiar defaults ni quitar guardias. |
| Memoria durable y consolidación | Hay memoria personal/proyecto con scopes, ranking, stale/decay, evidencia y verificación; hay compactación y checkpoints. | No migrar al esquema de Aura sin una ablation que mida recuperación correcta, fuga entre tareas y carga de contexto. |
| Ingi Charla con procesos auxiliares | STT, LLM y TTS local ya están desacoplados, con streaming, VAD, interrupción y métricas. | No aporta una mejora de perfil de voz demostrada. |

## Pruebas realizadas en esta auditoría

El gate Linux obligatorio se ejecutó como build Release + CTest completo, con
checkout NTFS espejado y una ruta de build explícitamente nativa:

```bash
XDG_CACHE_HOME=/tmp/llamacode-aura-eval \
LC_TEST_BUILD_DIR=/tmp/llamacode-aura-eval/build_tests_clean_20260930 \
LC_QTDIR=/home/cristian/Documents/Codex/2026-09-06/fijate-que-yo-tengo-el-proyecto-6/work/qt/6.8.3/gcc_64 \
./scripts/tests-linux.sh Release
```

Resultado: **77/77 tests aprobados**, incluyendo perfiles, memoria/grafo,
checkpoints y corridas, governor, Computer Use/automatización, herramientas,
seguridad, harness y workflows. No se tocó código C++/QML, por lo que no hubo un
cambio de comportamiento que requiera promoción de perfil.

El primer intento usó `/home/cristian/.cache/llamacode`, que en esta notebook
resuelve al volumen NTFS; CTest quedó bloqueado por I/O. La segunda ejecución
usó el directorio nativo `/tmp` y es el resultado válido. No ejecutar CTest
contra la ruta antigua hasta corregir esa redirección local. No había `llama-server`
ni endpoint de inferencia activo, así que no se ejecutó otro A/B vivo contra un
perfil de modelo en esta auditoría.

## Registro para no repetir

- No repetir la suite `computer_use_prompt_order_v1 + hard_v1` de 48 tareas,
  7 pasadas, 2 seeds / 504 requests por las tres variantes: ya consta en
  `docs/computer-use-sandwich.md`.
- No repetir la corrida Genesis de 48 tareas / 720 requests del 2026-09-29 ni
  descargar de nuevo ese GGUF: resultados y artefactos están en
  `artifacts/swift-genesis-evaluation-20260929/`; la campaña concluyó sin
  promoción por BCB8 2/8.
- Para probar lo que queda de la idea, crear una campaña **nueva y nombrada** de
  autonomía de larga duración con al menos dos tareas multi-paso y un control
  de Computer Use de otra clase de aplicación. Congelar modelo/runtime/perfil,
  tareas, seeds y criterios; intercalar orden base/variante; separar frío de
  memoria caliente; probar reinicio/reanudación; incluir una interrupción y un
  estado sin acción segura. Puntuar éxito final verificable, objetivo retenido,
  acciones inválidas/destructivas, replanteos, abstenciones, tool calls,
  latencia y crecimiento de contexto. Para atribuir mejoras a módulos, ejecutar
  ablaciones de una variable por vez y mantener evidencia/capturas o estado
  reproducible. Una tarea de juego sirve de caso concreto, no de heurística del
  controlador general.
- No elevar modelo ni cambiar perfil/harness hasta que la variante gane en
  éxito y seguridad, preserve reanudación/abstención, y el costo de tiempo y
  contexto quede dentro del gate fijado antes de la prueba.

