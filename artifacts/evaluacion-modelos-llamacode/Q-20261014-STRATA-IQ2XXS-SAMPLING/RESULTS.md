# Resultados — Q-20261014-STRATA-IQ2XXS-SAMPLING

**Estado: screening completo el 2026-10-15; sin mejora de sampling observada.**
Las nueve corridas TaskFlow (tres seeds por temperatura 0,1/0,6/1,0) dieron
0/13, tres reparaciones y la misma repetición de `!`; el smoke local de
codificación también dio 0/6 en los tres brazos. Esto sólo caracteriza a ISTA
IQ2_XS/Strata 0.1.41 con este harness y contexto 1M; no es un resultado de
IQ2_XXS ni una conclusión universal sobre sampling.

## Alcance y primer intento — 2026-10-14

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

## Veredicto provisional de los intentos bloqueados

Esta interpretación correspondía a la evidencia disponible antes de la
reanudación que pidió el usuario; el resultado final aparece al final del
documento.

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

## Reanudación solicitada por el usuario — 2026-10-15

El usuario pidió quitar el corte preventivo de 60 GiB / PSI avg10 <0,1% y
usar la memoria disponible para completar la prueba. El plan quedó actualizado
antes de volver a cargar: RAM, PSI y swap se registran sin cortar por esos
valores; sólo aplica una salida de emergencia si `MemAvailable` cae por debajo
de 4 GiB durante 30 s, PSI `full avg10` llega a 80% durante 30 s, aparece un
OOM del kernel o el host deja de responder. Se mantienen la receta 1M, los
perfiles, suite, HarnessSpec y semillas. El valor mínimo observado fue 54,31
GiB disponibles y PSI avg10 llegó a 39,54%; no hubo OOM ni interrupción de
emergencia. Tras cerrar el servidor, el postflight mostró 105,87 GiB
disponibles, PSI 0, puertos libres y ningún proceso de inferencia.

## Resultado final — 2026-10-15

Se ejecutó el TaskFlow ULTRA preregistrado en un workspace aislado, con el
perfil IQ2_XS/1M sin cambios y el mismo HarnessSpec. LlamaCode registró la
temperatura y seed efectivas esperadas en cada resultado; el backend incluye
la temperatura de la corrida en el payload. Las nueve corridas terminaron
por calidad, no por timeout, transporte o infraestructura.

| Temperatura efectiva | Seeds | TaskFlow final | Reparaciones | Tiempo total mediano | Tool calls / archivos |
|---:|---|---|---|---:|---:|
| 0,1 | 4242, 4243, 4244 | 0/13 en 3/3 | 3 por corrida | 19,275 s | 0 / 0 |
| 0,6 | 4242, 4243, 4244 | 0/13 en 3/3 | 3 por corrida | 19,372 s | 0 / 0 |
| 1,0 | 4242, 4243, 4244 | 0/13 en 3/3 | 3 por corrida | 19,079 s | 0 / 0 |

En las nueve respuestas, Strata registró el mismo token `!` repetido 256 veces
y detuvo la generación; LlamaCode recibió la salida repetida, sin código ni
llamadas a tools. El detector de estancamiento del governor quedó en 0 porque
esta parada ocurrió en la detección de repetición del servidor. Cada brazo
produjo una única respuesta entre sus tres seeds; de hecho, la respuesta fue
idéntica en las nueve corridas. Subir a 0,6 o 1,0 no redujo reparaciones ni
recuperó una tarea.

Como diagnóstico adicional se ejecutó la suite incluida
`llamacode_local_coding_smoke` (3 prompts cortos, seed 4242): T=0,1, 0,6 y 1,0
dieron 0/6 y 3 reparaciones cada una, otra vez con la misma repetición de `!` y
sin tools ni archivos. No había un fixture HE0 dedicado en los assets; este
smoke no se etiqueta como resultado formal de la escalera HE0/HE20/BCB.

La guarda preventiva previa queda retirada para esta evaluación, tal como pidió
el usuario. En la primera carga el monitor registró mínimo 54,31 GiB
disponibles, PSI avg10 máximo 39,54%, incremento de 64.756 páginas de swap-out
(≈253 MiB) y cero eventos OOM. La segunda carga del smoke llegó a 54,44 GiB y
PSI 18,49%, también sin OOM. La memoria se recuperó al parar Strata. La única
salida automática de emergencia preregistrada (<4 GiB disponibles por 30 s,
PSI `full` ≥80% por 30 s u OOM) no se activó.

**Conclusión:** en esta combinación IQ2_XS + Strata + LlamaCode a 1M, cambiar la
temperatura de 0,1 a 0,6 o 1,0 no resolvió el loop reproducible. No promover
ningún cambio de perfil o recomendación. El checkpoint exacto IQ2_XXS del post
sigue sin estar disponible, así que no se prueba ni se refuta ese caso. No hubo
cambio de código productivo, sampling productivo o HarnessSpec. Los recibos de
cada corrida se conservan en `receipts/`; la [observación de Strata](receipts/strata-repeat-observation-20261015.txt)
captura el corte por 256 repeticiones y el [resumen agregado](receipts/sampling-results-20261015.json)
contiene métricas por brazo y telemetría de memoria.
