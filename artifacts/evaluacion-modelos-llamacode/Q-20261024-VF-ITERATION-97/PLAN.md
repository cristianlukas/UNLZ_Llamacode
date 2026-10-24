# Q97 · Swift 1.5 vs ASTRA Flash-Next · BCB-Hard-8

**Task:** Q-20261024-VF-ITERATION-97
**Lock:** vf97-swift-astra-bcb8-apparmor-chatgpt-20261024-191553
**Estado:** preregistrada; pendiente validación CPU-only, huellas actuales y preflight fresco.

## Pregunta

¿Swift 1.5 Qwen3.8-27B IQ2_XS sin MTP supera el gate de calidad del perfil productivo ASTRA Flash-Next IQ2_XS para coding/agentes en el holdout local BCB-Hard-8?

## Diseño preregistrado

- Mismos ocho casos congelados, seed 4242, contexto 8192, razonamiento activado con presupuesto 2048 y límite de salida 6144.
- ASTRA corre primero con Strata/MTP4; después se detiene y verifica limpieza antes de Swift 1.5 por llama.cpp sin MTP.
- Cada brazo usa las dos RTX 3090 y los 128 GB RAM disponibles, en serie. No existe brazo single-GPU ni límite artificial de RAM.
- Se comparan perfiles completos; runtime, MTP/especulación y template difieren. El resultado no aísla la calidad de los pesos.
- La guarda Q95 se conserva: PSI moderado (full ≥20% o some ≥70% durante 30 muestras) sólo avisa; PSI severo (full ≥60% o some ≥80% por 15 muestras) detiene. MemAvailable <32 GiB u OOM detienen siempre. PSI cgroup sólo se registra.
- El servicio transient usa RuntimeMaxSec=10800, KillMode=control-group, Nice10, CPUWeight20, IOWeight25, best-effort I/O prioridad 7; límites MemoryMax/High/SwapMax en infinity. AppArmorProfile=chatgpt permite user namespaces del grader sin cambiar políticas persistentes.
- No retries ni concurrencia. Fallo de grader, sandbox, transporte, modelo, GPU o limpieza deja resultado N/D y detiene el screen.
- Gate para iniciar un estudio repetido: Swift ≥3/8, al menos dos pases más que ASTRA, transporte 8/8 y cero sandboxErrors. El screen de una seed no permite declarar superioridad ni adoptar un default.
- Speed claim: ninguno en Q97; una comparación posterior requiere al menos tres semillas balanceadas y calidad no inferior, además de una mejora ≥10% en E2E correcto.

## Assets y ejecución

La fixture, runner Q89, runtimes, configuración ASTRA, shards/pack/MTP y GGUF Swift conservan las huellas fijadas por Q89/Q95. El supervisor Q97 vuelve a comprobar el fixture/config/runtimes y hashea assets de modelo antes de iniciar los servidores. Las corridas de Q95 quedan preservadas y no se sobrescriben; su ASTRA score continúa N/D porque el grader no corrió.

## Orden de trabajo

1. Validar sintaxis/pruebas CPU-only y leer fingerprints pequeños.
2. Sincronizar y leer de vuelta el registro en Google Sheets.
3. Revisar procesos/puertos/GPU/RAM/PSI/OOM del host inmediatamente antes del inicio.
4. Iniciar únicamente el servicio transient Q97 con AppArmorProfile=chatgpt; el supervisor verificará huellas y guardas antes de levantar ASTRA.
5. Ejecutar ASTRA, cleanup, luego Swift; cada arm es serial y dual-GPU.
6. Guardar resultados, limpieza y Sheet readback. No modificar ASTRA, SOL, perfiles productivos, pesos, drivers, swap, THP, NUMA, GUI ni Linux Game Hub.
