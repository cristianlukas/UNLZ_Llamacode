# Resultados — Q-20261014-R9700-TASKFLOW

## Resultado

El screening TaskFlow ULTRA del perfil local Unsloth UD-Q4_K_XL terminó con
**13/13 criterios**. La primera pasada obtuvo 11/13; LlamaCode reparó dos veces y
el intento 2 pasó. No se ejecutó una segunda réplica independiente y no se
promueve el perfil.

| Medida | Resultado |
|---|---:|
| Criterios TaskFlow | 11/13 inicial → **13/13 final** |
| Reparaciones | 2 |
| Compilación de los módulos | OK |
| `unittest` generado por la tarea | **30/30 OK** |
| Self-test | `SELF_TEST_OK`, exit 0 |
| Tiempo del run | 581,957 s |
| Primera llamada / escritura | 241,884 / 241,925 s |
| Decode medio registrado por el harness | 64,69 tok/s |
| TTFT medio registrado por el harness | 119,5 ms |
| Tool calls del agente | 21 invocaciones aceptadas, success rate 100%; métrica auxiliar: 2 inválidas y 1 redundante (la suite no definía llamadas esperadas) |

Los criterios son diez comprobaciones de existencia de archivos y tres comandos
de aceptación. El código y sus 30 tests fueron generados por el propio modelo;
el harness ejecutó las comprobaciones, pero no constituye una suite independiente
de calidad del código.

## Configuración reproducible

- Perfil: `q4-udq4kxl-taskflow-20261010`, R8192, `agent-maximo`.
- Fingerprint efectivo del perfil TaskFlow: `2bbc5b4c7c4e34c044814f565879b61cab3d799b0557355e5662b584b053d9fa`.
- HarnessSpec: `cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`.
- Suite `qwen38_taskflow_ultra_ast_vs_sol_20261006`, SHA-256
  `f04febb440208d5bf74c01e84d78f5127e57c164fabece2acbfb346215dc0c17`.
- Seed 4242, thinking habilitado, temperatura del agente 0,1 según el recibo;
  configuración Strata: T=0,6, top-p=0,95, top-k=20, min-p=0, repeat=1,
  presence=0.
- Strata 0.1.41, commit
  `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`, contexto 131072, KV int8,
  expertos residentes, dos RTX 3090, split de capas 18.
- Config usada por la corrida SHA-256
  `a35a4d5edf1e7f012737e952ca170c5459fc0dc6cc68a00ec20442429dd71dd7`, copiada
  en `receipts/strata-launch-config-original.json`. La configuración de replay
  del task cambia sólo el destino del log para mantenerlo dentro de este
  artefacto; su SHA-256 es `be22dfd24640547a946dc235eeb432bc298e73fab1a5fdbdfeef77d9fc9b7229`.
- Log del motor de esta corrida: `receipts/strata-engine.log`, SHA-256
  `19be6b44225b1d57d17af078f70d615da3636c197194acb0f6019a6b0b0bfc62`. El
  config usado inicialmente apuntó al log histórico del screening Q4 anterior;
  copié aquí las 152 líneas añadidas por esta corrida y restauré aquel archivo
  byte por byte a su contenido previo.
- El Q4 y su manifiesto de cuatro shards se reutilizaron del screening anterior.
  En este turno los SHA-256 de los shards 1 y 2 volvieron a coincidir con el
  manifiesto; los cuatro tamaños y rutas también coinciden. No se volvió a leer
  byte a byte el total de 111 GB.
- Workspace de benchmark aislado bajo `runtime/xdg-data/LlamaCode/LlamaCode/benchmark-runs/`;
  la raíz del checkout no fue el workspace de la tarea.

## Alcance y lectura

Esto completa la cobertura TaskFlow que faltaba para el candidato local Q4. La
suite lleva un nombre histórico de comparación ASTRA/SOL, pero esta corrida fue
un screen individual de Q4 y no un A/B. El resultado no valida el quant AtomicChat
Q4_K_M ni replica el equipo R9700 del post. Junto con HE0/HE20/BCB8 y ADV del
screening Q4 previo, aporta una señal exploratoria de coding/agentes; una sola
corrida y tests autorreportados no justifican una mejora estable o promoción.

No se cambiaron perfiles productivos, harness ni pesos. El registro crudo de
Control API y el snapshot de benchmark están en `receipts/taskflow-q4.json`; el
run aislado completo está bajo `runtime/xdg-data/LlamaCode/LlamaCode/benchmark-runs/`.
