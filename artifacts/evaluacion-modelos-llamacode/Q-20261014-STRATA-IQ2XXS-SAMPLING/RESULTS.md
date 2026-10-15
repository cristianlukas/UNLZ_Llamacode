# Resultados — Q-20261014-STRATA-IQ2XXS-SAMPLING

**Estado: bloqueada antes de inferencia por presión de memoria durante la carga.**
No hay score ni conclusión sobre loops o sampling.

## Alcance y ejecución

El plan preregistrado comparaba la temperatura efectiva 0,1 (control) con 0,6
y 1,0 en ISTA Flash-Next IQ2_XS, Strata 0.1.41 y el TaskFlow ULTRA fijado por
hash. El checkpoint exacto IQ2_XXS citado en el post no existe en el inventario
local, por lo que incluso un resultado válido habría sido sólo evidencia para
IQ2_XS.

El primer preflight quedó abortado porque observó una página de `pswpin` en
8 segundos. Se conservó el recibo y se repitió el mismo guard 15 segundos
después; el segundo pasó: 111,0 GiB disponibles, PSI `some/full` 0, swap sin
actividad durante la ventana, puertos candidatos libres y ningún proceso de
inferencia detectado. Sus recibos son `preflight-before-load.json` y
`preflight-before-load-retry.json`.

Se inició únicamente el servidor propio de esta tarea en el puerto 8352, con
el config aislado de contexto 1.048.576/YaRN ×4. Durante la carga, Strata
indicó que iba a leer los pesos y cargar unos 39 GB de expertos en RAM. La
medición posterior mostró 82,8 GiB disponibles, `memory PSI avg10=22,30%`
(`some` y `full`), GPU0 6.616 MiB y GPU1 4.790 MiB. Se interrumpió esa misma
sesión con Ctrl-C antes de que el endpoint quedara listo o se enviara cualquier
prompt. Después, el proceso propio ya no figuraba, el puerto 8352 estaba libre,
MemAvailable volvió a 111,5 GiB y las GPU quedaron en 775/108 MiB.

El log del engine preservado (`receipts/strata-engine.log`) confirma el split
automático entre las dos 3090, el contexto 1.048.576/YaRN ×4 y 6,19 GiB de KV
en RAM fijada; termina durante el arranque, sin prueba de endpoint listo.

No se lanzó LlamaCode, HE0 ni TaskFlow; corridas y tiempo de inferencia por
brazo: **0**. El PSI elevado que quedó en la ventana móvil inmediatamente
después de parar es el arrastre de la carga recién interrumpida, no una medida
de recuperación estable. El recibo `receipts/runtime-load-abort.json` guarda
las observaciones y la razón de detención.

## Veredicto

- La comparación 0,1/0,6/1,0 no se ejecutó; no se puede atribuir ni refutar el
  loop a la temperatura, al quant ni al harness.
- No se cambia ningún perfil, sampling productivo, harness ni recomendación.
- No se puede extrapolar a IQ2_XXS, cuyo checkpoint exacto sigue sin estar
  identificado/localizado.
- Para reanudar, adquirir un lock nuevo para el mismo ID, repetir el preflight
  y contar con una receta de carga que mantenga la presión de memoria debajo
  del umbral durante la carga completa. Si la carga de este contexto vuelve a
  elevar el PSI, detenerla sin abrir el cliente y ajustar primero la estrategia
  de carga; no bajar el contexto ni cambiar el modelo silenciosamente, porque
  eso alteraría el fingerprint preregistrado.

No hubo cambio de producción. Se construyó un binario aislado de evaluación,
descrito en `PLAN.md` y en `receipts/runtime-sha256.txt`; el checkout y el
ejecutable Windows Debug del usuario no se modificaron.

## Reanudación 2026-10-15

Con el lock nuevo `b6ed46b6-0f79-4e2a-912c-3bdb0cd95321`, repetí el preflight
antes de iniciar cualquier servidor. Abortó de forma segura: `MemAvailable`
63.871.774.720 bytes (59,5 GiB) frente al mínimo de 60 GiB; GPU0 tenía
23.879/24.576 MiB y GPU1 22.406/24.576 MiB usados, con 29%/23% de utilización.
El puerto 8350 ya tenía un listener y se detectaron procesos LlamaCode (PID
484347) y Strata (PID 484773). PSI avg10 fue 0% y no hubo delta de swap en los
8 segundos, pero las GPU no estaban libres. No inicié nuestro servidor ni el
daemon de evaluación, no envié prompts y no me conecté al proceso existente;
no detuve ni modifiqué esos procesos. El recibo completo es
`receipts/preflight-20261015.json`.

La tarea vuelve a quedar bloqueada antes de carga. Puede reanudarse cuando
LlamaCode/Strata externos hayan terminado, el puerto 8350 esté libre, ambas
RTX 3090 tengan VRAM para la receta y `MemAvailable` sea al menos 60 GiB. El
intento del 14-10 y este preflight se conservan por separado; ninguno aporta
un resultado de calidad o sampling.

## Reintento de carga 2026-10-15

El preflight no invasivo pasó a las 12:47:24Z: `MemAvailable` 110,35 GiB,
PSI avg10 0%, sin cambio de swap durante 8 s, puertos candidatos libres y sin
procesos LlamaCode/Strata. Las dos RTX 3090 tenían 937/108 MiB ocupados; la
lista de procesos mostraba uso gráfico del escritorio, sin procesos compute.
Los dos shards IQ2_XS se volvieron a verificar contra SHA-256 y ambos dieron
`OK`.

Se inició únicamente el servidor aislado de la tarea con la misma configuración
(Strata 0.1.41, IQ2_XS, 1.048.576 tokens/YaRN ×4, puerto 8352). El engine
registró 33,02 GiB de arena de expertos cargados, caché de expertos de 16,91
GiB en VRAM y 1.717 MiB libres al terminar la reserva. La guarda observó a las
12:49:58Z PSI avg10 de 17,94% y `MemAvailable` 59,75 GiB, por debajo del mínimo
de 60 GiB. Envié SIGINT sólo al proceso propio (PID 566742). En la carrera de
cierre el wrapper llegó a imprimir que el endpoint estaba listo; no abrí el
endpoint, no conecté cliente, no envié prompts ni ejecuté inferencia. El
proceso terminó y el puerto 8352 quedó libre. Después de parar, la VRAM volvió
a 991/108 MiB; PSI avg10 todavía marcaba 9,84% en la ventana móvil, así que no
se infiere recuperación a partir de esa muestra inmediata.

Esto es un bloqueo de infraestructura/estrategia de carga, no un resultado de
calidad. La hipótesis de que la temperatura reduzca loops sigue sin evaluar y
no se cambia sampling, perfil ni HarnessSpec. No repetir la misma receta de
carga hasta preregistrar una estrategia que mantenga PSI debajo de 0,1% y
`MemAvailable` por encima de 60 GiB durante la carga; cualquier cambio de
configuración efectiva debe recibir una huella nueva. Recibos: [preflight](receipts/preflight-20261015-124630.json), [guarda](receipts/load-monitor-20261015-1248.json), [resultado de carga](receipts/runtime-load-abort-20261015.json), [log del engine](receipts/strata-engine-20261015.log).
