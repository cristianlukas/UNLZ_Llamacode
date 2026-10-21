# Prerregistro — Q20 · S23 PLE FP8 A/B con expertos file-backed

**Estado:** preregistrado antes de editar las configuraciones de prueba o iniciar inferencia.  
**Lock:** Q-20261021-VF-ITERATION-20 · token `50d8dfb3-511a-48b2-a253-2cd6197cee17`.

## Pregunta

¿La ruta Strata `--mmap-experts` permite completar de forma segura el A/B original de S23 para PLE FP8 E4M3 en ASTRA Qwen3.8 Flash-Next IQ3_S, y mantiene una señal de calidad/latencia que justifique más evaluación?

Q19 validó el mismo engine Strata con `--mmap-experts` en otro quant (IQ3_XXS) y contexto 700K. Esto prueba que la opción existe y puede reducir la reserva inicial de expertos; no garantiza que cargue IQ3_S con su PLE FP8 de 51,2 GB. Los intentos S23 previos con la ruta residente se abortaron por PSI sostenida antes de READY.

## Diseño

- A: ASTRA IQ3_S con su PLE stock. B: mismos pesos y configuración, sustituyendo únicamente el sidecar PLE por FP8 E4M3.
- En ambos brazos se agrega solamente `--mmap-experts` a la configuración del intento anterior. YaRN/contexto (131.072), pack/tokenizer, sampling, prompt, scorer, Strata 0.1.41 y dos RTX 3090 se mantienen fijos.
- Tres pares emparejados, semillas nuevas 23003/23004/23005; 8 tareas BCB-Hard bilingües por solicitud. Orden: stock→FP8, FP8→stock, stock→FP8. Se ejecuta un solo servidor a la vez.
- Los archivos de pesos y el sidecar se usan en sus ubicaciones; no se copian, mueven, descargan, borran ni editan. No cambia ningún perfil productivo. ArtCraft y cualquier otra GUI quedan intactas.
- El launcher reutiliza el runner S23 existente; sólo redirige sus artefactos a Q20, usa el puerto 8355 y los JSON de configuración aislados de este plan.

## Gate de decisión

El screen FP8 es positivo únicamente si, agregado sobre las 24 tareas, B obtiene al menos dos aceptaciones más que A, la diferencia de calidad favorece a B en al menos dos de los tres pares, no aparece una regresión de seguridad/tool-call y la mediana decode de B no supera A en más del 5%. Si falta transporte válido en una tarea, ese brazo no obtiene score completo. Un screen positivo sólo habilita planear una evaluación mayor; no promueve un modelo ni cambia producción.

## Guardas de recursos y parada

Antes de cada brazo: confirmar lock propio; cero procesos/servidores de inferencia y puerto 8355 libre; modelo/sidecar/pack/fixture con fingerprints fijados; MemAvailable ≥90 GiB, PSI full avg10 <0,5%, OOM counter 0; GPUs <85 °C. La presencia de ArtCraft u otra GUI no bloquea ni se termina. No se matan procesos no relacionados.

Cada brazo corre en un transient systemd scope exclusivo con MemoryHigh=64 GiB y MemoryMax=72 GiB. Watchdog cada 5 s; termina sólo su scope si MemoryAvailable cae bajo 48 GiB, swap libre cae ≥1 GiB, cambia OOM, scope memory pasa 68 GiB, some PSI avg10 supera 40%, full PSI supera 25% durante cuatro muestras, GPU llega a 85 °C o pasan 2.700 s. Si el guard detiene un brazo, se conserva su log y no se repite esa misma combinación.

Se usa `ionice -c3` para dar prioridad idle al I/O de carga. No hay `io.max` delegado; mmap + el límite de memoria/PSI son la ruta nueva evaluada. Si la ruta no pasa el preflight o el dry-run CPU, no se inicia GPU.

## Validaciones antes de inferencia

1. Copiar sin cambios ambos JSON originales a Q20 y añadir `--mmap-experts` a ambos; comparar el diff para confirmar que no cambia ningún otro argumento.
2. CPU tests del adapter: lock, config mapping, naming sin overwrite y salida dry-run; py_compile.
3. Verificar fingerprint del engine, shards ASTRA, sidecar FP8, pack/tokenizer, fixture BCB-Hard y scorer; confirmar que todas las rutas existen.
4. Fresh preflight de inference servers/listeners, puertos, PSI/RAM/OOM/swap/GPU y scope. Preregistrar resultado antes de cada brazo.

## Artefactos

- Configuraciones aisladas: `work/source23/configs/stock.json` y `work/source23/configs/fp8.json`.
- Adapter: `work/run_source23_mmap_arm.py`; tests: `work/test_source23_mmap_adapter.py`.
- Outputs y receipts sólo debajo de Q20. Fuente original/prereg S23: `Q-20261020-VF-20261019-01/receipts/source-23-review.json`.

## Amendment 1 — corrección del sandbox del scorer

**Registrado antes de continuar inferencias.** El brazo stock Q20, seed 23003,
completó con seguridad y produjo ocho respuestas, pero el scorer fijo no pudo
ejecutar ninguna prueba: `bwrap` oculta `/home` y luego intenta ejecutar el Python
del venv bajo `/home/cristian/.cache/.../.venv/bin/python`. Sus ocho puntajes son
inválidos; se conservan respuestas y recibos. El resultado stock S23 previo también
falló antes de evaluar porque no extraía bloques fenced, así que su 0/8 no sirve como
baseline válido.

Se corregirán sólo copias aisladas del controlador y scorer dentro de Q20. El venv
pinneado del grader se montará en sólo lectura dentro del sandbox; modelo, sampling,
prompts, fixture, pruebas ocultas y semántica de evaluación permanecen iguales. Se
ejecutarán regresiones CPU del sandbox y se volverán a calificar las ocho respuestas
stock Q20 de seed 23003 ya guardadas, sin enviar solicitudes nuevas al modelo. Es una
reparación del scorer, no otro intento de inferencia; el JSON crudo no se modifica.
Los pares preregistrados siguen sólo si el grader pasa las pruebas CPU. Se guardarán
hashes de las copias locales y recibo de re-calificación. Sin cambios a producto,
perfiles, modelos ni artefactos de la tarea anterior.

La primera prueba del sandbox corrigió el intérprete, pero reveló que las respuestas
truncadas que abren un bloque ```python sin cerrarlo seguían entrando con los
marcadores de fence. El primer regrade provisional quedó en 1/8 y se conserva; no se
usará como resultado final. Se agregó una extracción acotada de fence incompleto y
el regrade final volverá a procesar `rawContent` original. El parser no repara ni
ejecuta de otro modo el código generado; los tokens repetidos o el código truncado
siguen siendo fallas del modelo. El segundo regrade se escribirá en otro archivo y
el CPU test cubre fences completos e incompletos.

## Resultado final de Q20

Los tres pares terminaron en empate: stock 1/8 y FP8 1/8 para seeds 23003, 23004 y
23005; agregado 3/24 por brazo y cero pares favorables a FP8. Los 48 requests tuvieron
transporte válido. Las medianas de medianas por seed fueron 126,75 tok/s decode stock
y 125,90 tok/s FP8 (−0,7%), dentro del margen del 5%; no se afirma mejora de velocidad.
FP8 no pasa el gate de calidad y no se promueve. Las mediciones de huella RAM están
confundidas por caché fría/caliente y no se interpretan como ventaja de formato.

El scorer final pasó 14/14 pruebas CPU y se re-calificó el stock 23003 a partir del
JSON de respuestas preservado, sin llamadas adicionales; su resultado final fue 1/8.
Los otros cinco brazos se ejecutaron ya con el scorer Q20 reparado. Todos llegaron a
READY, completaron 8/8 y terminaron sin guard abort, OOM ni proceso/listener residual.
Q20 queda cerrado. No repetir este A/B; conservar el perfil actual. La campaña VF-
20261019-01 permanece incompleta por las condiciones externas listadas en `RESULTS.md`.
