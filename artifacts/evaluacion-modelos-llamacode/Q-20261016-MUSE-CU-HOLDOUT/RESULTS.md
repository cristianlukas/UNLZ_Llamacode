# Resultados — Q-20261016-MUSE-CU-HOLDOUT

**Estado:** screening de Computer Usage cerrado, comparativa parcial, sin promoción.

**Fecha local:** 2026-10-16 (America/Argentina/Buenos_Aires).
**Preregistro:** [PLAN.md](PLAN.md).

## Diseño y ejecución

Se ejecutó un holdout GUI nuevo en Xvfb privado `:97`, 1366×768, `es_AR.utf8` y tema oscuro. Las cuatro condiciones del diseño corrieron secuencialmente con una réplica (r4) por condición: ASTRA IQ3_S calibrado y Flash-Next UD-Q4_K_XL, cada uno con prompt base y overlay Muse seguro. Se mantuvieron Strata 0.1.41, las configuraciones preregistradas, el mismo fixture de tres tareas y las guardas. El overlay SHA-256 fue `9fb742d295a4fbc155b18ad2216d21d5349184ef80b8eec8a092416ce0cfda97`.

| Condición | Resultado manual | Observación |
|---|---:|---|
| ASTRA base | **3/3** | Calculadora 1411; línea inglesa exacta; cálculo 1829 y reemplazo exacto en español. |
| ASTRA + overlay | **1 estado alcanzado de 3** | Calculadora no obtuvo 1411 (mostró `817`/`817817`); el estado de la línea inglesa sí quedó correcto, pero el turno superó 300 s; tarea de reemplazo no iniciada. |
| Q4 + overlay | **2/3** | Cálculo 1411 y línea inglesa correctos; en el tercer paso calculó 1829, pero agregó el texto español a la línea inglesa en vez de reemplazarla. |
| Q4 base | **3/3** | Los tres estados y el documento sin guardar se verificaron visualmente. |
| **Total** | **9 estados correctos de 12 previstos** | Dos fallos funcionales y un estado no intentado. |

La puntuación corresponde a inspección manual de capturas; OCR sólo fue diagnóstico y reconoció 2/3 tareas en cada corrida completa. Las capturas y hashes están en `receipts/manual-review-*.json`. ASTRA base requirió el único reintento de infraestructura preregistrado: su primer controlador desapareció durante la carga antes de estar lista la API y no envió tareas. La primera invocación del brazo ASTRA overlay también tuvo un error de CLI del harness antes de iniciar inferencia; el recibo se conserva. La corrida válida de ASTRA overlay terminó después del timeout en una sesión con API/escritorio sanos, por lo que el fallo funcional no se volvió a intentar selectivamente.

## Recursos y limpieza

Las cuatro corridas válidas finalizaron con OOM delta 0. En cada brazo el supervisor informó servidor apagado, puertos 8350/8898 y display `:97` libres. El postflight final registró 117,95 GB de memoria disponible, OOM 0, ningún proceso del runner/servidor ni proceso CUDA de inferencia, puertos libres y sin Xvfb privado persistente. Véanse `receipts/cu-*-controller.json` y `receipts/postflight-final.json`.

Las 29 comprobaciones de integridad y cierre pasaron: sintaxis de los dos runners, estados de los controladores, limpieza de recursos, OOM y hashes de capturas (`receipts/verification-checks.json`). No hubo cambios en código de producto, perfiles, HarnessSpec ni build; por eso no correspondía correr el gate C++/QML de `scripts/tests-linux.sh`.

## Decisión

No se promueve el overlay ni se cambia el perfil recomendado. Es una sola réplica holdout por condición, con un brazo overlay ASTRA incompleto y dos fallos en overlay; no da una comparación equilibrada ni una estimación estable. Se conserva como una nueva ronda, separada de la ronda histórica 10/12. El A/B textual previo sigue sin mejora de calidad y con penalización de latencia mediana de +6,83% (ASTRA) y +9,87% (Q4), por encima del gate de +5%.

Para una afirmación estable hacen falta al menos dos réplicas pareadas adicionales del mismo diseño, ejecutando las cuatro condiciones y sin reintentar sólo una celda fallida. No se requiere repetir el holdout para cerrar este screening.

## Cobertura no medida por esta ronda

- **Android Agent:** no hubo instalación del APK; este host no tiene `adb` ni `emulator` (`receipts/modality-platform-check.json`).
- **Audio/Ingi-Charla:** no se envió audio; el seguimiento previo encontró que Flash-Next no expone ASR/TTS en el endpoint. No se infiere calidad acústica desde texto.
- **Visión:** aunque el manifiesto del endpoint anuncia entrada de imagen, estos requests fueron de texto y control de escritorio; no se envió imagen. Los resultados visuales existentes siguen siendo evidencia independiente.
- **Coding/agentes, contexto y rendimiento:** no se repitieron en esta tarea; se conservan los screens con sus hashes y límites en el documento canónico.

## Recibos principales

- [Plan preregistrado](PLAN.md)
- [Manifiesto de perfiles y runtime](receipts/profile-manifest.json)
- [Verificaciones de artefactos y cierre](receipts/verification-checks.json)
- [Postflight](receipts/postflight-final.json)
- [Revisión manual Q4 base](receipts/manual-review-q4-base-r4.json)
- [Revisión manual ASTRA overlay](receipts/manual-review-astra-overlay-r4.json)
- [Revisión manual Q4 overlay](receipts/manual-review-q4-overlay-r4.json)
- [Revisión manual ASTRA base](receipts/manual-review-astra-base-r4.json)
