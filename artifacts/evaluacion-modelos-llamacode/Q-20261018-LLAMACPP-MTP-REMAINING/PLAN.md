# Plan — Q-20261018-LLAMACPP-MTP-REMAINING

Inicio: 2026-10-18T13:16:47Z. Lock inicial
`9a8ab269-7135-48d2-aea7-01cd04aa5b70`; reanudado tras liberación del usuario
a las 2026-10-18T13:25:23Z bajo el lock actual
`e9c6f3ab-0643-4417-ad21-6b86a35be9c2`.

## Objetivo

Cerrar sólo las pruebas de coding/agentes que quedaron incompletas en la
campaña Q4 llama.cpp MTP. No repetir resultados válidos ni medir variabilidad.
La campaña sigue siendo un screening: una corrida por huella no permite afirmar
mejora estable ni promover MTP.

## Candidatos, controles y huellas fijadas

- Modelo base: Qwen3.8-Flash-Next UD-Q4_K_XL, revisión
  `38bb39ee97821de2c9009abb7e93950eec396e66`; cuatro shards y SHA-256
  verificados en [recibo de hashes](../Q-20261017-LLAMACPP-MTP-CODING-RESUME/receipts/base-model-hashes.json).
- Runtime: llama.cpp Spark CUDA, commit
  `836d57176dc699a726c55418e4f96b8ca628e1bf`; binario
  `/media/cristian/Disco local/LlamaCode-cache/llama.cpp-spark-native-20261003/build-cuda/bin/llama-server`,
  SHA-256 `ab7828696af2694981037b7114d834d310c1c5f24b39ab24267898748334cbb4`.
- Servidor LlamaCode aislado Debug, SHA-256
  `38d2b916c7c2b08061a2a59eb9b0b120247b19768aed454f4a6992e53ed48959`.
- Control MTP-off BCB8 fingerprint
  `7f84727070a2fb93d008a42c90391f3904d800f7d7c2e67f173813ab0435ff89`.
- TaskFlow ULTRA: MTP-off fingerprint
  `e9c5c527e30744049cff955f0489c36cd08a8777b9bf87422f0f768c3d42cf23`;
  MTP-on histórico
  `b39dcfa4f912aee2ae973d28f25ac04f81e5ba1c0dbaaa2e0a7e5641e38d3d27`.
- MTP Q8_0 sidecar SHA-256
  `58a47d6a216307e9b97172d5bfdc3436a8994b632f5e436b9bb6edf8951da8d1`.
- HarnessSpec fingerprint
  `cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`.
- BCB8 suite `05c28394-11d0-41fe-a55f-b3cb69db9c15`, ocho tareas, SHA-256
  `42771136b447b7b5619e04a1ea211f663222cd6752ca38d995083b5a4d207574`.
- TaskFlow ULTRA suite `qwen38_taskflow_ultra_ast_vs_sol_20261006`, un prompt,
  SHA-256 `f04febb440208d5bf74c01e84d78f5127e57c164fabece2acbfb346215dc0c17`;
  seed 4242, contexto 8192 y temperatura efectiva 0,1. Incluye diez checks de
  archivo y tres comandos de aceptación, con hasta tres reparaciones.

## Por qué se reintentan huellas idénticas

- BCB8 MTP-off llegó a 4/8 antes de cancelarse tras más de 15 minutos sin avance
  en un ítem. No generó un score válido de ocho tareas.
- TaskFlow MTP-off terminó interrumpido tras un probe de 3/10; tampoco generó
  un resultado final. El registro previo muestra búsquedas de sólo lectura fuera
  del workspace que completaron en segundos; no se modificaron archivos ajenos.
- TaskFlow MTP-on sí completó normalmente: 0/13 tras tres reparaciones. Es un
  fallo de calidad válido y no se repetirá en esta continuación.

Se autoriza una sola ejecución de finalización por cada caso incompleto, sin
cambiar prompt, HarnessSpec, perfil, sampling, seed, suite, modelo ni runtime.
La repetición es necesaria para obtener un resultado final ausente; no se usará
como muestra de variabilidad. Los intentos anteriores y sus recibos siguen
enlazados desde [Q-20261017 RESUME](../Q-20261017-LLAMACPP-MTP-CODING-RESUME/RESULTS.md).

## Orden y límites preregistrados

1. BCB8 MTP-off; reutilizar HE0 1/1 y HE20 20/20 ya válidos bajo la huella
   exacta. Ejecutar una pasada, timeout total 1800 s; un corte o cancelación
   antes de ocho ítems sigue siendo incompleto y no es 0/8.
2. TaskFlow ULTRA MTP-off, una pasada, timeout total 1800 s; guardar score
   inicial, reparaciones, diez archivos, los tres comandos, tool calls, duración
   y estado del workspace. El 0/13 MTP-on histórico no se cuenta como una prueba
   pendiente ni se repite.
3. GPU en serie. Preflight antes de cada perfil: ambas RTX 3090 sin procesos de
   cómputo ajenos, puertos 8033/8081/8350/8877/8898/18111/18112/18119 libres,
   MemAvailable ≥40 GiB, PSI estable y `oom_kill` sin aumento.
4. Guardas durante la ejecución: cancelar sólo el benchmark/servidor aislados si
   MemAvailable <20 GiB durante 15 muestras, PSI `some avg10` ≥80 o `full
   avg10` ≥60 durante 15 muestras, aumenta `oom_kill`, aparece otra carga CUDA,
   cambia el fingerprint o vence el timeout. Swap se registra y no es por sí
   solo condición de cancelación. No detener procesos ajenos.

## Infraestructura

Los perfiles, catálogo, datos y daemon se copian a
`runtime/lch/`; sólo se usan los puertos aislados 18111/18112/18119. Los pesos
permanecen en sus ubicaciones originales y se abren en lectura. Los runners API
validan perfil, suite y fingerprint antes de cargar el modelo; BCB8 también exige
HE0/HE20 válidos y BCB pendiente bajo esa huella.
El primer intento de esta tarea quedó bloqueado por los servidores PeritoSoft
Qwen3.5 en 8033/8081; el usuario informó que ya los liberó. El preflight nuevo y
las mediciones de cada ejecución quedan en `receipts/`.

No se modifica código de producción, perfil activo, HarnessSpec ni swap. No se
corren tests C++/QML porque esta continuación sólo ejecuta benchmarks y no cambia
código. Los resultados se clasifican por separado como calidad válida,
infraestructura inválida o incompleta.

## Resultado observado

- BCB8 MTP-off se canceló a 1/8 tras tres reparaciones con fallo duro. Cobertura
  BCB sigue pendiente y no hay score final.
- TaskFlow MTP-off completó 0/13 tras dos reparaciones, con fallo de calidad. El
  agente no escribió los diez archivos requeridos ni ejecutó correctamente los
  tres checks; hizo 18 llamadas de shell desviadas a MTP/llama.cpp. No se repite
  el mismo fingerprint hasta corregir y validar el flujo de tarea/workspace.
- Sin fallos de infraestructura ni presión de recursos. TaskFlow MTP-on 0/13
  continúa como resultado válido histórico y no se repitió.
- Sin cambios de producto ni promoción de MTP. Evidencia detallada en
  [RESULTS.md](RESULTS.md).
