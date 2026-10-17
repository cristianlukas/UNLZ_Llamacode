# Plan — Q-20261016-MUSE-CU-HOLDOUT

- **Estado:** cerrado; screening parcial con una condición incompleta y sin promoción. Preregistrado antes de cualquier carga/inferencia.
- **Fecha local:** 2026-10-16 (zona America/Argentina/Buenos_Aires).
- **Objetivo:** resolver el desbalance restante del screen Muse Computer Usage con una réplica holdout completa y pareada. No reintentar sólo el caso funcional fallido de Q4 de la campaña previa.
- **Antecedente:** `Q-20261013-MUSE-CU-E2E` y `Q-20261016-FLASHNEXT-RESUME2` dejaron ASTRA base r2 3/3 y Q4 base r2 1/3 (la línea inglesa se duplicó y el reemplazo en español no completó); las condiciones overlay ya habían pasado en aquellas réplicas. Repetir sólo Q4 base r2 sería selección oportunista. Se ejecutará un fixture de valores/frases nuevos, en las cuatro condiciones.

## Diseño fijado

- **Condiciones y orden secuencial:** ASTRA/base → ASTRA/overlay → Q4/overlay → Q4/base. Una réplica por condición, con un escritorio nuevo por corrida. Este orden contrapone el orden de prompt en Q4; no permite una afirmación estable de tres seeds.
- **Candidatos/control:** ASTRA Flash-Next IQ3_S calibrado (profile fingerprint `864c6ba74e684940f34b5519c5e53a36412e386a9b160fb22ed7c2640ee85fa4`) y Flash-Next UD-Q4_K_XL (fingerprint `09d45e63b1f548df63775d947a051a70ca66561bb5a04bcf292050eb8bcb2958`); cada modelo se compara consigo mismo con prompt base frente al overlay Muse seguro. No atribuir diferencias entre motores/perfiles sólo al modelo.
- **Modelo/runtime:** ASTRA y Q4 locales ya verificados; Strata 0.1.41, commit `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`; dos RTX 3090, MTP4, KV int8, `max-context=131072`, KV resident 32768, spec-min-p 0.70, una sesión a la vez. Configs fuente en `Q-20261016-FLASHNEXT-RESUME2/receipts/configs/cu-astra.json` y `cu-q4.json`; se copiarán sin cambiar argumentos de inferencia, sólo redirigiendo logs al nuevo artefacto. Los hashes SHA-256 de pesos/runtime, binario LlamaCode y config efectiva se guardarán en el manifiesto antes de ejecutar.
- **Agente/herramientas:** perfil aislado `31ff813d-6bf5-4400-8f82-69af4fcc64bc`; sólo herramientas `desktop_*`, sin MCP; modo de aprobación y herramientas efectivas se registrarán desde la API. No se controla el display personal `:0`.
- **Prompt:** base de Computer Usage; overlay `muse-safe-transfer-v1.txt`, SHA-256 `9fb742d295a4fbc155b18ad2216d21d5349184ef80b8eec8a092416ce0cfda97`. El overlay se conserva exacto; no contiene el texto inseguro atribuido a Muse.
- **Fixture holdout:** misma secuencia de tres tareas E2E en las cuatro condiciones: (1) GNOME Calculator `83×17=1411`; (2) abrir un documento nuevo en GNOME Text Editor, escribir exactamente `MUSE CU HOLDOUT: keyboard input verified.` una vez, dejarlo sin guardar; (3) calcular `59×31=1829` y reemplazar la línea anterior por `Resultado verificado: 1829`, sin guardar. No se usa terminal, archivos ni red. Resolución fija 1366×768, locale `es_AR.utf8`, tema Adwaita dark para todos los brazos.
- **Sampling y límites:** temperature 0.6, top-p 0.95, top-k 20, min-p 0, repetition 1, presence 0, reasoning medium; timeout de 300 s por tarea; contexto 131072; no hay seed de muestreo expuesta por el endpoint. Una corrida por condición. Capturas manuales son el criterio para el contenido del editor; OCR se conserva como diagnóstico, no como oráculo.
- **Criterio:** una tarea pasa sólo si la UI muestra el resultado calculado correcto, la línea única exacta o su reemplazo exacto, y el estado solicitado (documento sin guardar). Error del agente con transporte/API/escritorio sano cuenta como fallo funcional y no se reintenta. Si una corrida falla por infraestructura antes de ejecutar una tarea, se conserva el recibo y se permite un único reintento de esa condición después de corregir la causa, sin reemplazar fallos funcionales.
- **Guardas:** preflight fresco por condición: `MemAvailable ≥32 GiB`, OOM estable, PSI bajo límites, GPU sin procesos CUDA de inferencia, puertos 8350/8898 libres y display privado :97 libre. En ejecución, abortar ante OOM nuevo, MemAvailable <20 GiB durante 15 muestras o PSI memory some avg10 ≥80/full avg10 ≥60 durante 15 muestras. SwapFree es telemetría, no se modifica. No interrumpir procesos ajenos.
- **Salida esperada:** resultados por condición/tarea, latencia y capturas; comparación descriptiva. Incluso 12/12 no basta para promover overlay ni declarar mejora estable; requiere al menos tres réplicas pareadas válidas.

## Fuera de alcance

No se ejecutan otras filas de la cola. No se vuelven a correr coding/agentes, rendimiento, visión por imagen, audio, retrieval/contexto largo ni el APK Android. Los endpoints de este screen se usan para desktop actions, no se envían imágenes ni audio. No habrá cambios productivos, perfiles, HarnessSpec, builds ni tests C++/QML.

## Evidencia

Las configs, versiones/hashes, scripts congelados, preflight, logs, capturas, OCR y evaluación manual se guardarán en `receipts/`; las decisiones finales se añadirán a `RESULTS.md` y al documento canónico.

## Desvío preregistrado antes del único reintento técnico

ASTRA base r4 attempt 1 no llegó a API-ready y no envió prompts. La sesión de ejecución desapareció mientras el controlador seguía en `loading_model`; el último sample (UTC 00:49:01) registró 57,99 GiB disponibles, PSI some avg10 49,61 y OOM delta 0. El recibo carece de postflight, y el proceso Strata/controlador ya no estaba activo al revisar. `journalctl -k` anotó a las 21:49:02 un error de mapeo de memoria sin PID, por lo que no se atribuye causalmente. Se preserva como infraestructura incompleta. Para el único reintento preregistrado se usará un supervisor separado de la sesión de terminal, sin cambiar el modelo, argumentos, fixture ni guardas; así podrá concluir el plazo de carga de 900 s y escribir el cierre. Si vuelve a fallar antes de API-ready, se detiene la campaña y no se consumen los otros tres brazos.


## Cierre — 2026-10-16 local

Se completaron ASTRA base 3/3, Q4 overlay 2/3 y Q4 base 3/3. ASTRA overlay llegó a API y ejecutó dos tareas: la calculadora falló y el turno del editor excedió 300 s; el reemplazo no se intentó. No se reintentó un fallo funcional de forma selectiva, conforme al preregistro. En total hubo 9 estados correctos de 12 previstos, dos fallos funcionales y uno no intentado. El único reintento fue ASTRA base, cuya primera sesión desapareció durante la carga antes de API-ready. El screening queda completo como experimento, pero la comparación es parcial y no promueve overlay ni perfiles. Ver [RESULTS.md](RESULTS.md) y recibos de revisión manual.

Postflight final: OOM 0; servicios, puertos 8350/8898 y display `:97` libres; sin procesos de inferencia propios. Las comprobaciones de hashes/sintaxis/estados dieron 29/29. No se iniciaron las otras entradas: la cola no contiene filas Pendiente y este protocolo es serial.
