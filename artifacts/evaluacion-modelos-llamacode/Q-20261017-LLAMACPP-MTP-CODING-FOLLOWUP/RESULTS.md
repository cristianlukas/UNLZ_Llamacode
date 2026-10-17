# Resultados — Q-20261017-LLAMACPP-MTP-CODING-FOLLOWUP

**Estado: bloqueada por la guarda de swap; evaluación incompleta.** La corrida
BCB8 MTP-off alcanzó a iniciar su primer prompt y luego se canceló de forma
segura. No hay un score nuevo ni un resultado 0/8. TaskFlow ULTRA MTP-off y
MTP-on no se ejecutaron.

## Qué quedó verificado

- Los cuatro shards Q4 base suman 111.334.654.784 bytes y sus SHA-256 coinciden
  con los recibos históricos. El runtime fue llama.cpp commit
  `836d57176dc699a726c55418e4f96b8ca628e1bf`, binario SHA-256
  `ab7828696af2694981037b7114d834d310c1c5f24b39ab24267898748334cbb4`.
- El draft MTP Q8_0 se bajó de la revisión fijada
  `efc50b7c3195a10eebd8d3e32f83b27b2aeb239d`; tamaño 4.137.429.120 bytes,
  SHA-256 `58a47d6a216307e9b97172d5bfdc3436a8994b632f5e436b9bb6edf8951da8d1`.
  Quedó en `/media/cristian/Disco local/Modelos-eval/Q-20261017-LLAMACPP-MTP-CODING-FOLLOWUP/`
  y sólo se apuntó a él desde el catálogo aislado; no se recreó la ruta eliminada.
- La compuerta de BCB8 comprobó el fingerprint MTP-off
  `7f84727070a2fb93d008a42c90391f3904d800f7d7c2e67f173813ab0435ff89` y los
  requisitos HE0 1/1 y HE20 20/20, que ya tenían resultados válidos. No se
  repitieron esos casos ni el BCB8 MTP-on histórico 3/8.
- El app y runtime usados son los identificados en
  `receipts/runtime-and-suites.json`; las suites y hashes quedan en el mismo
  recibo. No se modificaron perfiles de producción.

## Corrida BCB8 MTP-off

El preflight del 15:16:07Z observó 117.076.168.704 bytes disponibles, swap usado
5.737.586.688 bytes, presión de memoria avg10 0, GPU compute vacía y puertos de
modelo cerrados. La suite BigCodeBench-Hard de 8 ítems inició el 15:18:02Z con
el agente Máximo y el fingerprint correcto. Empezó `BigCodeBench/928` (prompt
1/8).

A las 15:18:32Z, el swap usado llegó a 8.092.295.168 bytes: 2.354.708.480 bytes
por encima de la base, más que el máximo preregistrado de +1 GiB. Quedaban
497.635.328 bytes de swap libre. El monitor llamó con éxito a `cancelBenchmark`
y `stopServer`; el benchmark reportó `Cancelado.`. El primer prompt alcanzó a
generar tokens, pero no se ejecutó su evaluación de aceptación. No se creó una
fila de resultado para la corrida. La etapa BCB sigue pendiente/incompleta en
el catálogo y esto **no** cuenta como 0/8, fallo del modelo ni score parcial.

## Screens que quedaron sin correr

- **TaskFlow ULTRA MTP-off:** no iniciado.
- **TaskFlow ULTRA MTP-on:** no iniciado. El archivo draft está disponible sólo
  en el disco secundario bajo el manifiesto, pero no se cargó para inferencia.
- **Hard Mode, velocidad, HE0/HE20 y BCB8 MTP-on:** no repetidos; sus resultados
  anteriores siguen siendo la evidencia vigente.

La guarda se mantuvo sin cambios. El postflight del 15:20:58Z confirmó
MemAvailable de 120.381.493.248 bytes, swap libre de 751.906.816 bytes, OOM 0,
lista de procesos compute vacía y puertos 18111, 18112, 8877, 8898 y 18119
cerrados. El servidor de modelo y el daemon aislado quedaron detenidos. Aunque
la RAM disponible es alta, el swap libre continúa por debajo de 1 GiB, así que
no se inició otra inferencia ni se alteró el umbral.

## Cambios y cobertura

No hubo cambios en código de producto, perfiles, build o configuración. No se
corrieron `tests.bat Debug` ni `scripts/tests-linux.sh Release`: esta campaña
fue una evaluación de modelos y no modificó C++, QML ni el harness. La campaña
no completó todas las pruebas planeadas; el bloqueo y la evidencia están en
`receipts/resource-monitor.jsonl`, `receipts/bcb8-mtp-off.events.jsonl` y
`receipts/postflight.json`.

Para reanudar, hacer un preflight nuevo que permita tolerar la guarda registrada
de +1 GiB de swap, con MemAvailable ≥40 GiB, GPU y puertos libres, y cargas del
host estables. No cambiar swap ni terminar procesos ajenos como parte de este
screen.
