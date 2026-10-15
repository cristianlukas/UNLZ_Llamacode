# Plan — Q-20261015-SOL-TASKFLOW-SAMPLING

## Pregunta

Comprobar si el perfil local SOL reproduce o evita el fallo observado en
ISTA IQ2_XS con el mismo TaskFlow ULTRA y el mismo coding smoke, usando la
misma matriz de sampling: temperatura 0,1/0,6/1,0; seeds 4242/4243/4244 para
TaskFlow y seed 4242 para coding smoke.

## Perfil y límites

- Launch profile: 177_SOL · Qwen3.8 27B · vLLM TP2 P2P MTP4.
- Modelo local Frozenlock Qwen3.8-27B AutoRound INT4, 7 shards, ~18 GB.
- Runtime: imagen vllm/vllm-openai:v0.27.1; W4A8, TP2, MTP4, dual RTX 3090.
- Contexto máximo configurado: 262144 tokens. El screen IQ2_XS usó 1048576
  tokens. Se conserva el techo SOL; no se edita el perfil productivo ni se
  fuerza a SOL por encima de su límite.
- Se usa la misma suite TaskFlow ULTRA (SHA-256
  f04febb440208d5bf74c01e84d78f5127e57c164fabece2acbfb346215dc0c17) y el
  mismo coding smoke (SHA-256
  a4c58e2a8f58ad28bc8abe4d294eb0f746c5867e34af49ba9e82a6884c48df61).
- Perfil de sampling del servidor: thinking habilitado, top-p 0,95, top-k 20,
  min-p 0, presencia 0; penalty de repetición 1,0 (default). Temperature y
  seed se pasan y se verifican en cada corrida por LlamaCode.
- El servicio se ejecuta como contenedor con nombre/proyecto exclusivos y
  bind de loopback. La copia local del perfil LlamaCode apunta al endpoint y
  omite el supervisor de contenedor; archivos de usuario quedan intactos.
- Se conserva el reasoning budget nativo de SOL (4096); suite, agente
  agent-maximo, permisos, reparaciones y comandos de evaluación son los mismos.

## Protocolo

1. Verificar pesos, imagen, procesos, puertos, RAM/PSI y GPUs; RAM/PSI/swap son
   observacionales y no bloquean por sí solos, según la instrucción del usuario.
2. Levantar SOL con su configuración local actual, esperar la API y conservar
   telemetría de memoria/GPU.
3. Ejecutar nueve corridas TaskFlow, en serie, hasta 1800 s por corrida.
   Parar la matriz sólo ante error de transporte/infraestructura, timeout
   acumulado o salida de emergencia del host; conservar todos los resultados.
4. Si TaskFlow termina sin caída de infraestructura, ejecutar tres coding
   smoke cortos, uno por temperatura y seed 4242.
5. Apagar sólo el contenedor y los daemons creados por esta tarea; revisar
   puertos, GPU y presión de memoria después de la descarga.

La salida de emergencia sólo detiene el contenedor propio si MemAvailable se
mantiene bajo 4 GiB durante 30 s, PSI full avg10 llega a 80% durante 30 s o el
contador oom_kill del kernel aumenta. No hay corte preventivo de 60 GiB ni de
PSI bajo.

## Interpretación

Se informan score inicial/final, reparaciones, herramientas, archivos, errores,
tiempo, salida repetitiva, temperatura y seed efectivos. El resultado es
comparable en tareas, suite y harness, pero la configuración de contexto y el
engine son distintos: SOL/vLLM/262K frente a IQ2_XS/Strata/1M. No atribuye por
separado diferencias a la cuantización.
