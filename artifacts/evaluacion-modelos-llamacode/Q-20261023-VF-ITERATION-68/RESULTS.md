# Q68 — Resultados

Estado final: completo. Q56 se ejecutó y cerró con 6/6 requests; la captura se dejó a cargo del usuario tras su instrucción. No se administró LinuxGameHub después de esa instrucción.

- Reinicio posterior al update completado; NVIDIA 615.71.09 alineado con NVML; Codex 26.1016.61520 desde ejecutable vigente.
- La ventana de la captura es LinuxGameHub Flatpak. El sandbox no tenía NVML porque sólo estaba instalada la extensión NVIDIA 610.57.04; se instaló la extensión 615.71.09 y se verificó visibilidad de `libnvidia-ml.so.1` dentro del sandbox. No se volvió a abrir ni modificar LinuxGameHub tras la indicación del usuario.
- Preflight externo de Q56 pasa recursos, proceso/listener, memoria, PSI, disco y GPU. La auditoría CPU halló defectos en el runner A1, por lo que se creó A2 antes de cargar modelo.
- Pendiente: prueba CPU, sincronización/readback Google Sheets, canario durable, preflight interno y seis requests seriales si todo pasa.


## Readback Sheet A2 · 2026-10-23T21:27:33.085233+00:00

Leídas de vuelta las tres filas de Q56 en `Evaluaciones LlamaCode`, `Accionables` e `Inventario de modelos`. El texto incluye estado activo, A2, 4/4 CPU, límites de uso de producción y ruta siguiente; no hay resultado de inferencia. Recibo: Q56 `receipts/google-sheet-sync-amendment-A2.json`.


## Canario cgroup Q56 · 2026-10-23T21:28:14.196192+00:00

Pasa; propiedades y límites efectivos coinciden con la preregistración. Sin modelo, GPU o solicitudes. El servicio se detuvo y recolectó. Recibo Q56: `receipts/q56-service-canary.json`.


## Preflight y Sheet antes del servicio · 2026-10-23T21:29:20.134580+00:00

Preflight Q56 pasó 17/17; readback actualizado en Evaluaciones, Accionables e Inventario. Receipts Q56: `google-sheet-sync-preflight-A2.json`, `service-launch.json`. Sin servidor ni requests.


## Q56 intento de lanzamiento 1 · 2026-10-23T21:30:24.728332+00:00

Abortó antes de `Popen` por guard de configuración: ruta de log relativa frente a destino Q56 absoluto. Sin inferencia/modelo/request; servicio quedó `failed` y ya no está activo. A3 preregistrada para ruta de log y hashes únicamente. Recibo: Q56 `service-launch-attempt-01.json`; preregistro A3: Q56 `amendment-A3.json`.


## A3 validada y sincronizada · 2026-10-23T21:31:47.610843+00:00

7/7 checks CPU, preflight fresco 17/17 y readback A3 completados. Se preserva el fallo previo a modelo como intento 1. Intento 2 se puede iniciar con los límites systemd previamente comprobados. Receipt de Sheet Q56: `google-sheet-sync-amendment-A3.json`.


## Unit anterior recolectado · 2026-10-23T21:32:19.571660+00:00

`systemctl start` no encontró el unit previamente fallido; ningún proceso se inició. El intento 2 queda ajustado a recrear un transient service con systemd-run y los mismos límites ya verificados. Recibo Q56: `service-launch-attempt-02-adjustment.json`.


## Q56 intento 2 durable activo · 2026-10-23T21:33:32.243007+00:00

Systemd confirma el servicio aislado en background.slice y los límites preregistrados; el runner reporta `loading`, 0 requests. Sheets actualizado y leído de vuelta.


## Q56 intento 2 · READY, sin prompt benchmark · 2026-10-23T21:34:35.399667+00:00

Carga del modelo correcta (READY en 40.936 s); abortó por helper inexistente en el objeto equivocado antes del primer prompt. El runner detuvo el servidor; no hay proceso/listener. OOM=0 y el pico cgroup reportado por systemd fue 72.9 GiB, bajo 96 GiB. A4 registrada para corregir el binding.


## A4 Sheet readback · 2026-10-23T21:35:46.864889+00:00

El Sheet documenta intento 2 sin resultado de calidad y 0/6 prompts; A4 CPU 8/8 y preflight 17/17 pasan. Intento 3 está preregistrado sin alterar el diseño. Recibos en Q56: `google-sheet-sync-amendment-A4.json`, `service-launch-attempt-03-preregistration.json`.


## Q56 intento 3 · guard de no sobrescritura · 2026-10-23T21:36:57.780302+00:00

El runner rechazó la salida canónica ya ocupada, sin modelo ni GPU. A5 conserva el resultado previo y preregistra archivos de salida únicos para el cuarto lanzamiento.


## Python del wrapper · 2026-10-23T21:38:15.658994+00:00

Se detectó `regex` ausente bajo el Python del sistema. El venv del runtime sí lo trae; verificación CPU pasó para hashes y conteos de tokens. A6 cambia el intérprete del wrapper y preserva el entorno del host.


## A6 Sheet readback · 2026-10-23T21:39:13.775596+00:00

Evaluaciones, Accionables e Inventario reflejan intento 3 sin carga, A5/A6 y preflight; el readback está guardado en Q56 `google-sheet-sync-amendment-A6.json`. No cambió ninguna métrica histórica ni producción.


## Q56 intento 4 · guard log pre-Popen · 2026-10-23T21:40:17.781702+00:00

Falló el guard antes del server porque el literal de log no siguió la ruta exclusiva A5. No usó GPU ni cargó modelo. Se preregistró A7 y un nuevo audit pre-server.


## A7 readback y guards · 2026-10-23T21:41:29.939590+00:00

Sheet refleja intento 4 pre-model, A7, audit 15/15, preflight 17/17 y próximo intento 5. No cambió producción ni métricas S55.


## Cierre de Q68 · 2026-10-23T22:13Z

Q56 se completó bajo este lock tras el preflight, Sheet/readback, canario durable y seis solicitudes seriales. El gate candidato pasó: response_format fue JSON crudo exacto 3/3. En el control plain, un response llevaba cerca Markdown; normalizada esa única cerca, las cinco facts son exactas, por lo que ambos modos recuperan 15/15. La diferencia es parseabilidad estricta observada en 3 prompts sintéticos reutilizados; no ventaja de calidad. Recomendación acotada: respuesta estructurada sólo con validación del cliente, o quitar una cerca externa bien formada y validar. Sin cambio en producción/default/contexto, ASTRA, SOL, PeritoSoft ni pesos fuente.

La unidad terminó limpia: return 0, forcedKill false, puerto 8352 libre, cero procesos/listeners residuales; MemAvailable 124009934848 B, swap 0, OOM 0, PSI 0. No se tocó LinuxGameHub tras el usuario indicar que lo gestiona. No queda una siguiente prueba de inferencia local habilitada por este resultado: los siguientes candidatos dependen de acceso Windows nativo, cambio de runtime/modelo/harness, o confirmación externa de licencia/elegibilidad Swift. Las acciones deben reabrirse con esa condición concreta, no repitiendo esta matriz.

Trazabilidad Q56: `../Q-20261023-VF-ITERATION-56/receipts/final-result.json`, `posthoc-json-fence-audit.json`, y `700k-json-schema-ab-attempt-04.json`. Sheet final: recibo Q56 `receipts/google-sheet-sync-attempt-05-final.json`; el readback final confirmó Evaluaciones, Accionables e Inventario.
