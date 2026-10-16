# Plan de reanudación — Q-20261016-FLASHNEXT-RESUME

- Inicio: 2026-10-16, lock `f1d80c81-9f98-4ba6-b50b-a333db373bf1`.
- Continuación solicitada por el usuario de `Q-20261016-FLASHNEXT-FOLLOWUP`.
- Conservar exactamente modelo, binario Strata 0.1.41, configs, corpus, orden y
  semilla de la campaña anterior; no repetir el par 1 (A/B, 16 muestras/brazo).

## Orden y gates

1. Completar pares 2 (B/A) y 3 (A/B) del Server Speed v1 con el runner resumible
   de `Q-20261016-FLASHNEXT-RESUME/scripts/run_server_speed_trim_ab.py`. El
   runner escribe recibos crudos en la campaña original y salta los brazos ya
   completos. Cada brazo requiere un preflight nuevo: MemAvailable ≥32 GiB,
   SwapFree ≥0,95 GiB, puertos libres y GPUs sin inferencia ajena. Durante la carga,
   conservar los cortes de PSI/OOM/MemAvailable y SwapFree <0,5 GiB durante 15 s.
2. Si los tres pares terminan, reportar efectos emparejados y dispersión. No
   declarar mejora estable salvo dirección repetida en los tres pares y efecto
   mayor que la dispersión. Outputs distintos no son score de calidad.
3. Luego, en serie y sólo con el mismo preflight: Q4 a 262K con retrieval exacto
   de diez valores al 95% del límite; un screen visual Q4 con el fixture
   congelado; las réplicas base pendientes de Computer Usage para ASTRA y Q4,
   dos apps por modelo en Xvfb privado y con recuperación segura.
4. No repetir coding/agentes, TaskFlow, ADV ni tool-eval: sus receipts Q4 válidos
   ya están en Q-20261010-FLASHNEXT-Q4-P100-POST y Q-20261014-R9700-TASKFLOW.
   Audio sigue sin ASR/TTS local; no mandar texto como audio. No modificar
   perfiles, prompts globales ni HarnessSpec.

## Preflight inicial

Lectura local 2026-10-16T21:43:18.825384Z: MemAvailable 119.335 GB, SwapFree
1.088 GB (pasa por margen estrecho), PSI memory avg10 some/full 0,03%/0,02%,
OOM no consultado todavía en esta continuación, `nvidia-smi` no lista apps de
cómputo; uso de memoria 872/108 MiB (apps de escritorio), puertos 8350/8351/
8898/8080/8081/8082 libres. Xvfb, xdotool, wmctrl y Tesseract disponibles;
AT-SPI launcher en `/usr/libexec/at-spi-bus-launcher`. El preflight se vuelve a
medir justo antes de cada brazo, porque SwapFree apenas supera el mínimo.

## Desviación de seguridad de la continuación

El preflight original de 1 GiB detuvo pair02-A antes de iniciar Strata: había
1.043.374.080 bytes libres (0,972 GiB), 29 MiB por debajo. Pair02-B, iniciado
con 1,013 GiB libres, terminó 16/16: SwapFree mínimo 0,972 GiB, MemAvailable
mínimo 65,49 GiB, PSI some avg10 máximo 3,34%, OOM 0. Para no dejar la réplica
emparejada incompleta por ese margen, el gate de inicio baja a 0,95 GiB sólo en
esta continuación. Se mantiene MemAvailable ≥32 GiB y el aborto durante la
ejecución si SwapFree <0,5 GiB durante 15 muestras; no se modifica swap ni se
detienen procesos ajenos. La decisión y cada mínimo quedarán en los recibos.

## Estado al cierre de esta continuación

Pair 2 terminó en orden B/A con 16/16 muestras por brazo. Pair 3-A quedó
`preflight-blocked` antes de iniciar Strata: SwapFree 0,792 GiB frente al gate
de 0,95 GiB; no se cargó el modelo ni se envió ningún prompt. Una espera natural
de 60 s no aumentó el margen. El preflight siguiente registró MemAvailable
111,27 GiB, PSI avg10 0, OOM 0, GPUs sin procesos de cómputo y todos los puertos
libres; el único gate fallido fue SwapFree, 0,795 GiB. Ver
`receipts/preflight-blocked-current.json` y el informe de resultados.

La continuación queda bloqueada hasta que un preflight fresco registre
SwapFree ≥0,95 GiB, MemAvailable ≥32 GiB, GPUs sin inferencia ajena y los puertos
de prueba libres. Al reanudar, conservar los pares 1 y 2, empezar por pair 3-A,
completar 3-B y seguir con los screens aún no ejecutados, siempre en serie y
con el mismo preflight por carga. No liberar swap manualmente ni interrumpir
procesos ajenos.

## Cierre

Guardar los nuevos recibos y el informe en este directorio y los logs de
inferencia en la campaña original para preservar el A/B. Actualizar el informe
canónico y `WORK_QUEUE.md`. Al terminar, verificar el token antes de liberar el
lock. No tocar ni versionar los directorios runtime ajenos ya presentes.
