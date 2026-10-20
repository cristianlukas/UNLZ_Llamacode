# Resultados — Q-20261019-STRATA-UDIQ4XS-REMAINING

**Estado: screening parcial cerrado; sin promoción.** Se ejecutó HE20 y se intentaron BCB8, ADV v1 y TaskFlow ULTRA bajo la autorización explícita de usar GPU0. BCB8 agotó dos timeouts; ADV quedó incompleto y TaskFlow se canceló tras superar el corte operativo. Ningún fallo de esas tres corridas incompletas debe interpretarse como score de calidad.

## Configuración fijada

- Modelo: Qwen3.8-Flash-Next Unsloth UD-IQ4_XS; Strata 0.1.41, HDD dedicado, RTX 3090 GPU0, contexto 32.768, KV INT8, MTP spec4.
- Perfil `q14-udiq4xs-he0`; fingerprint efectivo `185d554a488e661980a6500e64b2752fc86a863c5d666eb570a2d7c0db0bdc47`.
- HarnessSpec `sha256:cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`; motor legacy v1.
- Agente `agent-maximo`, seed 4242, temperatura 0.1. GPU1 se dejó a los monitores (108 MiB observados); no se ejecutó inferencia en GPU1.
- Los hashes de los tres shards y del pack MTP están en el [preflight fijado](../Q-20261010-STRATA-UDIQ4XS-POST/receipts/continuation-20261018/preflight.json). No se modificaron perfiles ni código de producto.

## Resultados

| Suite | Resultado verificable | Clasificación |
|---|---|---|
| HumanEval/20 (`20261019_182855`) | 20/20 final, 20/20 primera pasada, 0 reparaciones; 4.705,197 s; 22,86 tok/s promedio, TTFT promedio 49,95 s. `failed=false`, `timedOut=false`; fingerprint `185d554a…0bdc47`. | **Válido.** Única suite de calidad de esta continuación que cerró con score válido. |
| BigCodeBench-Hard/8, intento 1 (`20261019_194930`) | Timeout 1.800 s con probe parcial 3/8; sin cierre de ocho ítems. | **Incompleto/timeout; sin score.** |
| BigCodeBench-Hard/8, intento 2 (`20261019_202119`) | Timeout duro a 7.200 s (7.226,41 s medidos) durante el cuarto ítem. El JSON final está marcado `invalid=true`, `timedOut=true`, `finalScore=0/0`; un probe parcial 3/8 no es score reportable. | **Inválido por timeout; sin score.** No repetir la misma huella en esta campaña. |
| ADV v1, 10 tareas (`20261019_222826`) | Se atascó en `ttl_cache_clock`, primer caso de 10. La comprobación del reloj falso repetía una aserción con el reloj movido hacia atrás; el workspace conserva dos archivos parciales. Se canceló por estancamiento a los 989,237 s. No existe JSON EVAL final. Suite SHA-256 `e5888f337ac279a0b3bf9de569054781b043d6c3086f5446dbaefbf1f1b285d5`. | **Incompleto/cancelado; sin score.** |
| TaskFlow ULTRA, una tarea/13 criterios (`20261019_224509`) | En el primer pase la aceptación encontró 6/10 archivos requeridos; cuatro seguían ausentes (`reports.py`, `cli.py`, `main.py`, `tests/test_taskflow_ultra.py`). `py_compile` falló al faltar `reports.py`; `unittest` no encontró pruebas. La reparación 1/2 no añadió artefactos aceptados; cancelada a los 2.117,136 s (35 min 17 s) por exceder el corte operativo de 30 min. No existe JSON EVAL final ni score final. Suite SHA-256 `f04febb440208d5bf74c01e84d78f5127e57c164fabece2acbfb346215dc0c17`. | **Incompleto/cancelado; el 6/10 es sólo el probe de existencia de archivos, no un score final de 13 criterios.** |

HE20 precede a los intentos BCB8 con la misma configuración efectiva, por lo que pasó la compuerta de configuración. Los dos intentos BCB8 no dieron un cierre válido; no se declaró aprobado el gate BCB8 ni se atribuyó una tasa de calidad. ADV y TaskFlow son pruebas complementarias, no sustituyen ese gate.

## Cola y cierre

`WORK_QUEUE.md` es una cola manual y no despacha tareas automáticamente. Durante este trabajo, las suites se iniciaron de forma serial. Tras cancelar TaskFlow la API local indicó `benchmarkRunning=false`, `benchmarkStatus=Cancelado` y `agentQueuedCount=0`; el agente no dejó tareas pendientes de esa corrida. El servidor Strata y el daemon aislado pertenecían a esta campaña y se detuvieron al cerrar; no se tocaron procesos ajenos ni GPU1.

El resultado global sigue siendo exploratorio: **no promover UD-IQ4_XS ni cambiar perfiles productivos**. Para reabrir coding, primero corregir el problema de progreso/escritura del harness y su límite de pared; luego preregistrar un nuevo fingerprint si cambia el protocolo. No repetir los dos timeouts de BCB8 con la misma huella.

## Recibos

Los resultados y logs capturados están en [recibos por corrida](receipts/runs/), con `SHA256SUMS`. El workspace original completo permanece en el runtime aislado de [Q-20261010-STRATA-UDIQ4XS-POST](../Q-20261010-STRATA-UDIQ4XS-POST/receipts/continuation-20261018/llamacode-runtime/data/LlamaCode/LlamaCode/benchmark-runs/). La corrida TaskFlow no produjo un archivo EVAL final; su evento de cancelación y el probe de aceptación se preservan en los recibos.
