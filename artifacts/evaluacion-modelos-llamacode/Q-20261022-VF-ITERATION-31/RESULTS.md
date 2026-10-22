# Q31 — Flash-Next · resultado BCB/765 con shim `python` · 2026-10-22

## Resultado

El único intento puntuable terminó con un grade válido, pero falló la aceptación de `BigCodeBench/765`: la solución produjo **0 archivos copiados**, donde el grader esperaba **2**, **1** y **2** en sus tres subpruebas. El shim aislado `python`→`/usr/bin/python3` pasó el smoke previo, por lo que Q30 ya no queda bloqueado por la ausencia del ejecutable. El caso no expiró: `timedOut=false`, `elapsedSec=803.276`, frente al límite de 1.800 s.

El agente tardó `668.548 s` en su primer intento; hizo 20 llamadas a herramientas, de las que 17/20 se marcaron exitosas, pero no entregó una solución aceptada. Las dos muestras de salida registraron 20 y 110 tokens, `avgTps=20.63` y `avgTtftMs=17,884`. Estos valores describen esta reparación fallida y **no** son una comparación de velocidad ni TPS de generación comparable. GPU0 llegó a 23.874/24.576 MiB usados; el scope no registró `oom`, `oom_kill` ni `max`.

## Decisión

- **No adoptar ni promover Flash-Next** con esta evidencia. El resultado rechaza este caso bajo este perfil/fixture, pero no demuestra superioridad o inferioridad general frente a ASTRA/SOL: no hubo control emparejado y sólo se puntuó una tarea.
- **No abrir BCB8**: el prerregistro habilitaba ese paso sólo si BCB/765 pasaba. No repetir este mismo caso ni el mismo protocolo.
- Mantener intactos los perfiles y pesos productivos de ASTRA, SOL y Flash-Next, además de cualquier uso de PeritoSoft.
- Avanzar el orden de cola a P2. Q29 de Qwen3.8-27B ya está cerrado sin adopción; OpenJet sigue bloqueado por incompatibilidad 64/65 bloques y ausencia de MTP en el GGUF local; P2.1 requiere implementar gates de seguridad antes de cualquier nuevo piloto; RCO ya falló su gate, Swift sigue bloqueado por acceso/licencia/compatibilidad, y los screens Strata cerrados no tienen claim nuevo. **No queda otra inferencia priorizada que esté desbloqueada y pueda cambiar una decisión**; reabrir sólo ante artefacto, runtime, control o protocolo materialmente nuevo.

## Reproducibilidad y limpieza

- Diseño y límites: [`PLAN.md`](PLAN.md); prerregistro: [`attempts/flashnext-bcb2-python-alias-03/receipts/preregistration.json`](attempts/flashnext-bcb2-python-alias-03/receipts/preregistration.json).
- Resultado del harness: [`benchmark-final.json`](attempts/flashnext-bcb2-python-alias-03/receipts/benchmark-final.json); invocación/seguimiento: `attempts/flashnext-bcb2-python-alias-03/receipts/benchmark-invocation.json` y `benchmark-poll.jsonl`.
- Candidato producido y grader: `attempts/flashnext-bcb2-python-alias-03/work/isolated-runtime/data/LlamaCode/LlamaCode/benchmark-runs/VF_FlashNext_repair-shell_compatibility__20261022_043241/EVAL_UD-IQ4_XS_Strata_0_1_41_HE0__ws/solution_BigCodeBench_765.py`; se preserva sólo como evidencia de este intento.
- Limpieza: [`owned-process-cleanup.json`](attempts/flashnext-bcb2-python-alias-03/receipts/owned-process-cleanup.json) confirma cierre de los procesos propios; [`postflight.json`](attempts/flashnext-bcb2-python-alias-03/receipts/postflight.json) confirma cero procesos/listeners de inferencia, 115.48 GiB disponibles y cero residuos de servidor.

El test se ejecutó en serie con GPU0. No se descargaron modelos, no se compiló el proyecto y no se cambiaron perfiles, runtime productivo ni código C++/QML.
