# Q-20261025-VF-ITERATION-121 · fijar el guard antes del runner · 2026-10-25

**Estado:** Cerrada · 8/8 regresiones CPU PASS; CLI verify-only PASS · lock `85657a21-b8a1-43eb-acee-86093877447c`

## Pregunta

¿Puede el siguiente runner de evaluaciones verificar por hash y cargar el guard AMD05 aprobado antes de que se inicie cualquier proceso de servidor, y rechazar el guard histórico Q97/Q100 o archivos alterados?

## Motivo

Q117/Q118 validaron AMD05 con ASTRA DEFAULT 1M y la traza real; Q120 dejó pendiente fijar la selección del guard del runner futuro. Repetir la carga 1M o los fixtures de presión no aportaría evidencia nueva. Un wrapper previo al arranque sí evita que una nueva campaña use por accidente el helper histórico con rachas PSI por métrica.

## Prerregistro

- **Alcance:** herramienta de evaluación fuera del producto, `tools/evaluation_guard_preflight.py`, y regresiones Python CPU-only.
- **Guard permitido:** `q117_pressure_guard_attempt05.py`, SHA-256 `b4d42302e7d405abd5c59df5aa86bb7de6ef3bb91aef487b49acbebd1d24270e`.
- **Runner de referencia:** `run_context_holdout_attempt05.py`, SHA-256 `24435c412cc791d47687199fb7ab765c7a52aed6b189ac4598eea8dd9d8822b1`.
- **Checks:** runner y guard coinciden con sus hashes; el runner importa el módulo exacto; `Monitor.start()` precede a `subprocess.Popen`; el módulo se importa desde la ruta aprobada antes del lanzamiento. Alteración de hash, helper histórico, falta de import o orden incorrecto bloquean el lanzamiento.
- **Criterio de aprobación:** todas las pruebas CPU pasan y una selección inválida no llama a `subprocess.run`.
- **Límites:** esto valida el wrapper de futuros runners de evaluación; no integra AMD05 en Q97/Q100 históricos ni en Codex/LlamaCode producto, y no explica cierres de Codex. ASTRA, SOL, Flash-Next, PeritoSoft, RAM, swap y perfiles no se modifican.
- **Recursos:** sólo CPU y archivos de prueba temporales. Sin inference server, modelo, GPU, build, red o asignación artificial de RAM.

## Enmienda 01 · camino feliz del despacho

El primer pase preregistrado fue 7/7. Antes de cerrar, agrego un caso que comprueba que una selección válida sí despacha exactamente el runner fijado con el intérprete actual, argumentos preservados y `cwd` del runner. `subprocess.run` queda mockeado; no se ejecuta el runner ni un servidor/modelo. Se volverá a ejecutar la suite completa de ocho casos. La enmienda se sincroniza en `Evaluaciones LlamaCode!A342:J342` antes del segundo pase.

## Resultado final

El intento 01 pasó 7/7. Tras preregistrar la enmienda 01 y verificarla de vuelta en el Sheet, el intento 02 pasó **8/8** en 0,015 s, incluidos aceptación y despacho mockeado del runner exacto, rechazo del guard Q97, hashes incorrectos, import faltante y orden incorrecto. El smoke CLI `--verify-only` pasó e importó AMD05 desde la ruta fijada; `git diff --check` pasó.

No se lanzó ningún proceso hijo real, modelo, inference server, GPU o build. No se aplicaron límites de RAM/swap ni se cambió ningún perfil. El wrapper se puede usar en nuevas evaluaciones, pero todavía debe invocarse explícitamente por la próxima corrida elegible; no se integró al producto ni se reescribió Q97/Q100 histórico. El cierre de Codex sigue sin atribución.
