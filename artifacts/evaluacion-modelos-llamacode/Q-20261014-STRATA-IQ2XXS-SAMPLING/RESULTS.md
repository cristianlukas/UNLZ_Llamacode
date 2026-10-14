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
