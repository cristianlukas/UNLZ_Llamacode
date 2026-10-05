# Strata UD-Q4_K_XL, 38 GiB RAM vs SOL — LC-H1

Fecha: 2026-10-04; suplemento v0.1.39 agregado el 2026-10-05. Perfil experimental aislado; no promovido automáticamente.

## Resultado

| Etapa | Strata UD-Q4_K_XL | SOL comparable | Decisión |
|---|---:|---:|---|
| HE0 | 1/1, 34.1 s | 1/1 prerequisite | Aprobado para iniciar HE20 |
| HE20 | 19/20 aceptadas antes del corte; timeout a 1801.2 s, sin archivo para HumanEval/19 | 19/20 → 20/20, 272.4 s | **Gate fallido**; score LC-H1 inválido y BCB8 bloqueado |
| Adversarial v1 | 8/10 primera pasada → **10/10** tras 2 reparaciones; 2051.8 s, 58 llamadas | 7/10 → **10/10** tras reparaciones; 534.9 s, 52 llamadas | Empate final; Strata tardó 3.84× |
| BCB8 | No ejecutado | 3/8 → 7/8 | No se inicia sin HE20 válido |

HE20 dejó evidencia precisa: las pruebas automáticas de `HumanEval/0` a
`HumanEval/18` pasaron; `HumanEval/19` no tuvo archivo porque venció el límite.
LlamaCode marcó la corrida como timeout y su score de calidad es `0/0`, por lo
que **no** se presenta como HE20 aprobado ni como 19/20 final. El checkpoint
del run fue conservado. Reanudarlo o repetir HE20 requiere otra ventana de
prueba y no altera este recibo fallido.

La suite adversarial sí terminó. El candidato mejoró de 8/10 a 10/10 con las
dos reparaciones permitidas y no tuvo llamadas de herramienta fallidas. SOL
acabó también en 10/10 en la comparación LC-H1 del 2026-10-03. La calidad
final empata; esta configuración Q4 tardó 2051.8 s frente a 534.9 s de SOL
(3.84×) y usó 58 llamadas frente a 52. Por tanto, adversarial no compensa el
fallo/latencia de HE20 ni justifica reemplazar SOL.

## Condiciones y procedencia

- Runtime Strata 0.1.35; modelo Unsloth UD-Q4_K_XL, cuatro shards cuya
  integridad SHA-256 se verificó antes de cargar. Perfil aislado
  `test-strata-unsloth-udq4-38ram`, 38 GiB de caché residente RAM, contexto
  131072, KV int8 con 32768 tokens residentes, MTP4, `spec 4`, `spec-min-p`
  0.5, expert-cache y prefill automáticos.
- GPU 1 sostuvo aproximadamente 23.9 GiB de 24 GiB durante inferencia; GPU 0
  quedó casi libre. La ruta probada es principalmente una GPU para los pesos,
  no una medición del fork dual-GPU.
- LlamaCode Debug, `--agent-daemon`, ControlApi y el mismo `AppController`
  que usa la aplicación. Suite por suite, el runner aislado fijó y verificó
  `agentThinkingEnabled=true`; `agent-maximo`, temperatura 0.1, seed 4242,
  baseline y hasta dos reparaciones. El hash HarnessSpec fue
  `sha256:cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`.
- Los hashes de HE20 (`ed91a742…ffc3d7`), BCB8 (`42771136…207574`) y
  Adversarial v1 (`2f0f30c8…f36ee87`) coinciden con el manifiesto de la
  comparación SOL/Swift del 2026-10-03. La comparación SOL usó el mismo agente,
  thinking, semilla, temperatura, HarnessSpec, suites y dos reparaciones.
  SOL fue Qwen3.8-27B AutoRound INT4 servido con vLLM; Strata fue UD-Q4_K_XL.
  El diseño compara los candidatos en el harness local, pero no hace idéntico
  el runtime ni la cuantización.
- Las suites HumanEval/0, HE20 y BCB8 se copiaron desde las definiciones locales
  guardadas a un `XDG_DATA_HOME` nuevo y aislado. No se reutilizaron scores
  antiguos. Los resultados nuevos llevan el mismo fingerprint de configuración
  y el mismo HarnessSpec.

## Recibos

- [HE0 nuevo](../artifacts/strata-post-evaluation-20261003/udq4_38ram_he0.json)
- [HE20 nuevo, incompleto por timeout](../artifacts/strata-post-evaluation-20261003/udq4_38ram_he20.json)
- [Adversarial v1 nuevo](../artifacts/strata-post-evaluation-20261003/udq4_38ram_adversarial.json)
- [Protocolo y comparación LC-H1 de SOL/Swift/IQ3_S](strata-swift-vs-sol-lch1-20261003.md)

El informe anterior de Q4 (`udq4_he0.json`, `udq4_he20.json` y `udq4_bcb8.json`)
no se combina con estos resultados: usó thinking apagado, y el archivo BCB8
antiguo quedó contaminado por una suite previa. El fingerprint corregido ahora
incluye `agentThinkingEnabled` y una prueba de regresión asegura que una
política de thinking distinta invalide la equivalencia de configuración.

## Reevaluación Strata v0.1.39 y presupuesto de RAM

La corrida a 38 GiB de arriba **no demuestra una limitación de calidad del
checkpoint**: agotó el tiempo de HE20 con una sola tarea pendiente y dejó BCB8
bloqueado. Se repitió el mismo checkpoint y el mismo harness con Strata v0.1.39,
cambiando únicamente el presupuesto residente de 38 a 70 GiB. El binario fue
compilado para CUDA 12.0/sm_86 con ggml `3cf03257`; se usó la GPU 1, contexto
131072, KV int8/32768 residentes, MTP/spec 4, caché de expertos y prefill
automáticos, `spec-min-p 0.5`, thinking activado, `agent-maximo`, temperatura
0.1, seed 4242 y hasta dos reparaciones. El HarnessSpec conservó el hash
`cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`.

| Suite | Resultado v0.1.39, presupuesto 70 GiB | Tiempo | Lectura |
|---|---:|---:|---|
| HE0 | 1/1 en primer intento | 21.072 s | Gate válido |
| HE20 | 20/20 en primer intento | 1708.655 s | Gate válido; sin timeout |
| BCB8 | 2/8 → **8/8**, 2 reparaciones | 1770.028 s | Gate válido |
| Adversarial v1 | 8/10 → **10/10**, 2 reparaciones | 1866.052 s | Gate válido |

La corrida completa suma **39/39 aceptaciones finales**. La misma configuración
v0.1.39 con presupuesto 38 GiB había terminado HE0 1/1 en 33.117 s, pero HE20
agotó 1800.435 s después de 19 aceptaciones y su score no era válido. En el log
de la corrida de 70 GiB, Strata reportó 56.15 GiB de expertos residentes en RAM;
el presupuesto configurado es un techo, no una orden de ocupar cada GiB libre.
La evidencia sí confirma que la RAM adicional disponible era el recurso que
faltaba para terminar el gate en este equipo.

**Decisión revisada:** conservar UD-Q4_K_XL; retirar la recomendación previa de
borrarlo por el timeout. El modelo ya completó los gates con la receta y el
presupuesto adecuados. Esto no basta para promoverlo como perfil predeterminado:
las suites largas siguen costando 28–31 minutos cada una y falta una repetición
independiente antes de afirmar estabilidad o ventaja de rendimiento.

### Recibos v0.1.39

Los JSON compactos están en el slot aislado
`/home/cristian/.codex/visualizations/2026/10/02/01a0fdac-e702-72e3-94fd-585859906215/lch1-data-q139/results/`:
`q4-v139-baseline-he0.json`, `q4-v139-baseline-he20.json` (38 GiB) y
`q4-v139-ram70-{he0,he20,bcb8,adv}.json` (70 GiB). Las configs aisladas están
en `/home/cristian/.cache/strata-0.1.39-q001/eval-q139/q4-v139-{base,ram70}.json`;
el log de la prueba de 70 GiB está en
`/home/cristian/.cache/strata-0.1.39-q001/eval-q139/logs/q4-v139-ram70.log`.

## Implementación y verificación de LlamaCode

La gestión del servidor ASTRA/Strata desde LlamaCode ya inicia, observa y para
el motor mediante el perfil de lanzamiento. En esta tarea se corrigió el
fingerprint LC-H1 para incorporar el estado de thinking y se agregó su
regresión en `tests/test_appcontroller.cpp`; `docs/benchmark-manual.md`
documenta la condición. El build Debug de Linux compiló y el gate completo con
directorio de usuario aislado pasó **77/77 tests**. La evaluación anterior de
Q4 a 38 GiB queda superada para decidir si el modelo puede pasar HE20: la corrida
v0.1.39 a 70 GiB completó HE0, HE20, BCB8 y ADV. El candidato se conserva; la
promoción operativa queda pendiente de repetición y comparación de latencia.
