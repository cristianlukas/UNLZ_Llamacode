# Plan — Q-20261014-STRATA-IQ2XXS-SAMPLING

**Estado al preregistro:** plan fijado; no se ejecutó inferencia ni se reservó GPU.

## Objetivo y alcance

Evaluar si la temperatura greedy/near-greedy explica loops agentic en la
integración local Strata + LlamaCode y si subirla mejora TaskFlow ULTRA sin
perder calidad o tiempo. El post no identifica el modelo exacto de IQ2_XXS ni
aporta checkpoint, revisión, prompts o logs reproducibles. La búsqueda local
por nombre exacto no encontró IQ2_XXS. El candidato disponible que sí coincide
con el comentario del usuario de IQ2_XS y con ASTRA DEFAULT es ISTA-DASLab
Qwen3.8-Flash-Next GSQ-RCO IQ2_XS; cualquier resultado se limita a ese GGUF,
Strata y LlamaCode.

## Hipótesis e interpretación inicial

- Strata 0.1.41 documenta `sampling` como defaults para campos omitidos; los
  valores de la petición tienen precedencia. Una petición sin temperatura cae
  en el default greedy de su engine, mientras `temperature=0` no se reenvía al
  engine y también deja el camino greedy.
- El benchmark de agentes LlamaCode registra `agentTemperature=0.1`: su código
  limita la temperatura de benchmark a `min(temp, 0.1)` y fija seed 4242. Por
  eso cambiar sólo el JSON de Strata no prueba el cambio de sampling del agente;
  el plan usa un binario de evaluación aislado que permite parametrizar ambos
  campos por variables de entorno, sin cambiar el código de producción.
- Para la integración LlamaCode, el control será temperatura efectiva 0.1,
  no “Strata sin parámetro”. Se medirán 0.6 (valor conservador actual del
  servidor/configuración local) y 1.0 (referencia oficial de thinking de
  Qwen3.8-27B, no recomendación confirmada para Flash-Next).

## Candidatos y controles

| Brazo | Temperatura por petición | Resto de sampling |
|---|---:|---|
| Control actual del benchmark LlamaCode | 0.1 | top-p 0.95, top-k 20, min-p 0, repetición 1.0, presencia 0 |
| Candidato conservador | 0.6 | Igual al control |
| Referencia de thinking Qwen | 1.0 | Igual al control |

Se usan el mismo checkpoint, Strata 0.1.41, dos RTX 3090, MTP4,
`spec-min-p=0.70`, KV int8/resident 32768, contexto 1.048.576 (YaRN ×4 desde
262.144), `pcie-frac=0.00`, caché de expertos auto, concurrencia 1, plantilla,
agente, thinking medio, presupuesto 8192, permisos, reparaciones y suite. Se
ejecutan en serie y en workspace limpio por corrida. No se descargan pesos ni
se editan perfiles productivos.

## Pruebas preregistradas

1. Preflight de pesos/hashes, binario y revisión Strata, GPU/VRAM/RAM/swap,
   presión de memoria, procesos/listeners y puertos. Abortar antes de cargar si
   la reserva no es segura.
2. HE0, una tarea por brazo, como smoke de transporte/calidad; no extender a
   HE20/BCB8 en esta campaña si el costo proyectado impide tres seeds por
   brazo dentro del límite de tiempo.
3. TaskFlow ULTRA exacto, hash de suite
   `f04febb440208d5bf74c01e84d78f5127e57c164fabece2acbfb346215dc0c17`,
   HarnessSpec `cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`.
   Tres corridas pareadas por brazo con seeds 4242, 4243 y 4244; hasta tres
   reparaciones por corrida; límite individual 1800 s y límite acumulado de
   30 min por brazo. Si un brazo llega al límite, detener sólo ese brazo y
   clasificar seeds restantes como no ejecutadas/incompletas.

Registrar por corrida: temperatura/seed efectivos, score inicial/final,
reparaciones, verificadores de archivos/compilación/tests/self-test, tool calls,
tokens y tiempos por generación, tiempo total, first tool/write, eventos de
estancamiento del governor y cualquier output repetitivo que quede preservado
en los recibos. Los eventos de estancamiento son una señal de no progreso del
harness; no equivalen por sí solos a un detector de repetición token a token.

## Criterio previo de decisión

Una mejora exploratoria requiere que 0.6 o 1.0 reduzca al menos 50% la suma de
eventos de estancamiento o evite al menos una reparación en dos o más de las
tres parejas, con TaskFlow final 13/13 en las tres seeds, sin transporte ni
infraestructura fallidos y con mediana de tiempo total no superior en más de
10% al control. Se reportan todas las corridas. Aun si cumple, una sola suite
no basta para promoción general: harían falta HE20/BCB8 y validación de otros
usos, conservando TC-92/TC-74 visibles.

No se infiere mejora para IQ2_XXS, otras cuantizaciones/modelos, Computer Usage,
Ingi-Charla, visión o contexto. Los TPS del post y comentarios no son
comparables con esta configuración local.
