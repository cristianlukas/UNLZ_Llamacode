# Q187 — Archivo reversible del Q180 sin uso activo en PeritoSoft

**Estado: completado.** Se liberó espacio del NVMe conservando el modelo en el HDD. No se ejecutó benchmark, build, inferencia ni GPU.

## Evidencia de uso

La base de datos activa de PeritoSoft (la que mantiene abierta su proceso `server.js`) configura llama.cpp con Qwen3.5-9B y Gemma 4 12B VLM. `PERITOSOFT_LLAMACPP_MODEL_ROOT` apunta a `/media/cristian/Disco local/Models/llamacpp`. El Q180 estaba en `Modelos-eval`, fuera de esa raíz, no figuraba en las rutas de modelo configuradas y no tenía handle abierto. No había `llama-server` activo durante la revisión. La interfaz de PeritoSoft permaneció abierta.

## Archivo

- Modelo: Qwen3.6-35B-A3B Unsloth UD-Q4_K_XL. Q180 ya había terminado: Q172 **0/100 en tres semillas**; los 28 casos por semilla agotaron 16.384 tokens de razonamiento sin respuesta/herramienta. Safety gate PASS.
- Tamaño: 22.853.663.008 B; SHA-256: `55983c5a75a1ab969824077b3bb3de4146e82a9234072b48ad4e8f92ad3fe9f1`.
- Original: `/media/cristian/Disco local/Modelos-eval/Q-20261028-VF-ITERATION-180/models/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf`.
- Archivo verificado: `/media/cristian/HDD extra/Modelos-eval/archived-unused/Q-20261028-VF-ITERATION-180/models/Qwen3.6-35B-A3B-UD-Q4_K_XL.gguf`. Se compararon tamaño y SHA-256 antes de retirar el original.
- No se eliminó el archivo archivado; ASTRA/SOL/Flash-Next y los modelos configurados para PeritoSoft permanecieron intactos.

## Espacio y efecto sobre pruebas pendientes

D NVMe aumentó de 145.357.176.832 a 168,210,841,600 B libres. El HDD conserva 7,980,912,640 B libres. Los dos NVMe suman **290,122,383,360 B libres**, todavía **9,877,616,640 B por debajo** del gate de 300.000.000.000 B de Q182. Además, Xolotl dual no tiene corrección/calificación demostrada; Q182 sigue bloqueado antes de descargar, compilar o inferir.

Se actualizó `Inventario de modelos` fila 19, `Modelos locales por peso` fila 81, `IA local` fila 77 y `Accionables` fila 49 en la planilla. Readback confirmó rutas/estado y formato Arial 10, WRAP/TOP. `data/actionables.json`, `data/inbox.json` y Q182 RESULTS contienen la nueva medición; las copias previas están en `receipts/prewrite-snapshot/`.

Receipt técnico: `receipts/archive.json`.
