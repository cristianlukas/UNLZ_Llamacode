# Resultados Q130 — reconciliación Flash-Next RESUME

**Estado: auditoría offline aprobada con un hueco de preregistro confirmado.**
No hubo descarga, build, inferencia, servidor ni uso de GPU. La validación
independiente está en `receipts/offline-reconciliation.json` y el comprobador
reproducible en `scripts/verify_flashnext_resume_receipts.py`.

## A/B `--trim-stage-weights`

El par 3 ya estaba ejecutado en la campaña original: pair01, pair02 y pair03
tienen seis brazos completos, 16 muestras cada uno (96 en total), hashes de
respuesta/configuración válidos y los dos dispositivos aparecen como RTX 3090
en comando y telemetría. Los seis servidores reportaron puerto libre al cerrar.
La validación existente 96/96 concuerda con la revisión independiente.

El efecto no justifica adoptar el flag: el par 1 favoreció A y los pares 2 y 3
favorecieron B; las direcciones de decode, prefill y latencia no fueron
consistentes en los tres pares. `Q-20261016-FLASHNEXT-RESUME` queda supersedida
por la campaña completa y `RESUME2`; no repetir pair03.

## Contexto Q4 a 262K: prueba anterior no alcanzó el criterio preregistrado

El intento05 sí completó una solicitud con 258.046 tokens de contenido,
contexto 262.144 y recuperación exacta de `LC-95P-7D3A9C`. Sin embargo, tanto el
script `probe_q4_262k.py` como el recibo sólo contienen **una clave**. El plan
de Q-20261016-FLASHNEXT-FOLLOWUP pide **diez valores en posiciones distintas**.
Por eso el intento05 prueba capacidad de una recuperación a 95% del contexto,
pero no cumple el screen de diez valores que justificaba esa rama. El umbral
de swap cambió a telemetría por evidencia de headroom/PSI/OOM; no se limpiará
swap.

Se abre Q131 para una solicitud a 262K con diez claves distintas, fixture y
hashes congelados antes de inferir, respuesta exacta de diez campos y setup
dual RTX 3090 + 128 GiB. Si el preflight del host o cualquiera de los artefactos
falla, se bloquea antes de iniciar servidor. No usar una sola GPU.

## Visión y Computer Usage ya ejecutados

El response Q4 de visión estaba cercado en Markdown, por eso el parser guardado
dejó `parsed=null`. El regrade offline del bloque JSON crudo obtuvo **9/11
campos exactos** (formas 4/4, colores 5/7). No se repitió el modelo y no se
promueve visión Q4.

La revisión manual de capturas CU confirma ASTRA IQ3_S 3/3 y Q4 1/3. Q4 añadió
texto en vez de reemplazarlo en el editor. El postflight registrado mostró
puertos libres, cero OOM y ninguna inferencia CUDA activa.

## Alcance restante

- Q131: screen exacto de diez valores en Q4 262K, sólo en dual RTX 3090.
- Audio continúa no aplicable mientras no exista endpoint local ASR/TTS
  verificado; no se prueba texto como audio.
- Los demás brazos de Q-20261016-FLASHNEXT-RESUME2 están ejecutados y no se
  repiten con la misma huella.

## Sincronización del registro

Se corrigieron las filas históricas 39–41 de `Evaluaciones LlamaCode`: FOLLOWUP
queda completo con los tres pares, el estado `2 de 3` de RESUME se marca
supersedido y RESUME2 indica explícitamente que el screen preregistrado de diez
valores sigue pendiente. Q130 ocupa la fila 351. La lectura de vuelta confirmó
los valores exactos y `WRAP` conservado; recibo `receipts/sheet-readback.json`.
No se cambió el accionable existente del detector: ya distingue ASTRA 1M con
RSS alta pero headroom suficiente, SOL en ambas GPU y el hueco de PSI alternada
en el guard histórico.

## Archivos

- Campaign original: `../Q-20261016-FLASHNEXT-FOLLOWUP/receipts/server-speed/`.
- Evidencia y recibos: `../Q-20261016-FLASHNEXT-RESUME2/`.
- Reconciliación reproducible: `scripts/verify_flashnext_resume_receipts.py`.
- Google Sheets: filas 39–41 reconciliadas; registro Q130 en fila 351; fila 352
  reservará la preregistración Q131 antes del preflight.
