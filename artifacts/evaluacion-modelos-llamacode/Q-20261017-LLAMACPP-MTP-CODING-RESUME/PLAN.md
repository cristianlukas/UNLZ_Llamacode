# Plan de reanudación — Q-20261017-LLAMACPP-MTP-CODING-RESUME

Inicio: 2026-10-17T19:23:41Z. Lock: `1d8308e8-9fa1-4666-8c7b-24cd344498c2`.
Pedido del usuario: completar las pruebas pendientes del A/B llama.cpp MTP.

## Alcance

1. Reintentar BCB8 control MTP-off con el fingerprint histórico; conservar la
   evidencia previa, pero no duplicar HE0 1/1, HE20 20/20 ni BCB8 MTP-on 3/8.
2. Ejecutar un screening TaskFlow ULTRA por brazo MTP-off y MTP-on, en serie,
   sólo si perfil, sidecar, suite y fingerprints efectivos pasan el preflight.
3. No repetir velocidad, Hard Mode ni otros scores históricos. No cambiar
   perfiles productivos, harness, sampling o swap.

## Revisión de la guarda previa

El primer follow-up abortó BCB8 cuando el swap usado creció 2.354.708.480 bytes,
pero MemAvailable seguía en 110,7 GiB, PSI memory avg10 era 0,87 y OOM era 0.
La corrida posterior quedó con más de 110 GiB disponibles, sin proceso de
cómputo propio ni presión sostenida. En la campaña
`Q-20261016-FLASHNEXT-RESUME2`, la RTX 3090 completó cargas con 52–55 GiB de
MemAvailable, SwapFree de 12 KiB–26 MiB y OOM 0. Esa evidencia muestra que el
uso de swap del host por sí solo no describe presión inmediata de RAM. Antes de
esta reanudación se retira únicamente el corte por aumento de swap y se conserva
como telemetría. La política queda explícita antes de iniciar inferencia.

## Guardas activas

- Inicio: MemAvailable ≥40 GiB; ambas GPUs sin procesos de cómputo ajenos;
  puertos aislados de modelo y API libres; suites, perfiles y hashes verificados.
- Runtime: detener esta corrida si MemAvailable <20 GiB durante 15 muestras
  consecutivas, PSI `some avg10` ≥80 o `full avg10` ≥60 durante 15 muestras,
  aumenta `oom_kill`, aparece otro proceso CUDA, o falla/cambia el fingerprint.
- Registrar SwapFree y swap usado cada 15 s. No borrar/alterar swap ni terminar
  procesos ajenos. Detener sólo el benchmark y servidor aislados del task.
- Revisar preflight antes de cada perfil; correr BCB8, TaskFlow MTP-off y luego
  TaskFlow MTP-on sin paralelismo. Un aborto técnico no es score cero.

## Evidencia fijada

- Modelo base: cuatro shards Qwen3.8-Flash-Next UD-Q4_K_XL, revisión
  `38bb39ee97821de2c9009abb7e93950eec396e66`; hashes detallados en el recibo del
  follow-up anterior.
- Runtime llama.cpp commit `836d57176dc699a726c55418e4f96b8ca628e1bf`.
- Sidecar MTP Q8_0: revisión `efc50b7c3195a10eebd8d3e32f83b27b2aeb239d`, SHA-256
  `58a47d6a216307e9b97172d5bfdc3436a8994b632f5e436b9bb6edf8951da8d1`, sólo
  en `/media/cristian/Disco local/Modelos-eval/Q-20261017-LLAMACPP-MTP-CODING-FOLLOWUP/`
  y el catálogo aislado.
- Fingerprint MTP-off
  `7f84727070a2fb93d008a42c90391f3904d800f7d7c2e67f173813ab0435ff89`;
  MTP-on histórico `69aacf099a61a10b4370ec10d0fec4d7fa83c93135b6cf57ada8302b664d32b8`.
  El API reportó para MTP-on el fingerprint actual
  `47f42e9a8b822681c1e30f4f476247c963437f62ed93a646db7fd8f4d05bb3a3`. La
  comparación de perfiles efectivos confirma que la diferencia relevante es la
  ruta absoluta pasada en `--spec-draft-model`; el sidecar descargado tiene los
  mismos bytes/hashes fijados. Se admite el TaskFlow MTP-on como screen con la
  ruta aislada y el nuevo fingerprint registrado, sin presentarlo como la misma
  huella ni compararlo como repetición directa del BCB8 histórico 3/8.
  TaskFlow MTP-off/on reciben sus fingerprints efectivos propios por usar
  `--predict 8192`; no había fingerprints históricos de TaskFlow para estos
  brazos.
- BCB8 ID `05c28394-11d0-41fe-a55f-b3cb69db9c15`, ocho ítems, SHA-256
  `42771136b447b7b5619e04a1ea211f663222cd6752ca38d995083b5a4d207574`.
- TaskFlow ULTRA ID `qwen38_taskflow_ultra_ast_vs_sol_20261006`, un ítem,
  SHA-256 `f04febb440208d5bf74c01e84d78f5127e57c164fabece2acbfb346215dc0c17`.
- HarnessSpec `cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`.

## Estado

Preregistro escrito antes de cualquier nueva inferencia. El preflight fresco,
resultados y postflight se guardan en `receipts/` y se resumen en `RESULTS.md`.

## Cierre de ejecución — 2026-10-17

Se hicieron los intentos preregistrados, pero el screening quedó parcial: BCB8
MTP-off se canceló al quedarse el prompt 4/8 activo por más de 15 minutos;
TaskFlow MTP-off se canceló tras un probe parcial 3/10 y una búsqueda `find /`
fuera del workspace; TaskFlow MTP-on finalizó 0/13 tras las tres reparaciones.
No se generó un score BCB8 MTP-off ni un score final de TaskFlow MTP-off. El
TaskFlow MTP-on sí es un fallo válido de calidad y no de infraestructura. El
detalle por corrida y la decisión están en [RESULTS.md](RESULTS.md).

Los monitores no registraron ninguna guarda disparada: OOM 0, MemAvailable por
encima de 109 GB y sin presión PSI sostenida. Al cerrar, agente, benchmark,
servidores y daemon aislado quedaron detenidos; puertos 18111/18112/18119
cerrados. No se alteró swap, código fuente, HarnessSpec ni perfiles productivos.
