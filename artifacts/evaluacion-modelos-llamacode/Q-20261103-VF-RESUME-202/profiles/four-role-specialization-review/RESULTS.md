# Revisión de asignación ASTRA / SOL / TERRA / LUNA

**Estado:** recomendación provisional registrada el 2026-11-17. No se ejecutó ningún benchmark ni inferencia en esta revisión.

| Perfil | Candidato recomendado | Evidencia relevante | Especialidad sugerida y límite |
|---|---|---|---|
| ASTRA | DeepSeek Maya-XS IQ1_S, Project Maya Q189, PNY-first `DS4_SPLIT=39,1`; conservar DSX T16 como alternativa | Maya DS4 (Q206): Q172 89,33/100 (n=3), P514,86/D19,57, LHA-1 76. DSX T16: Q172 86,33/100 (n=3, Q190), P429,14/D25,33 y LHA-1 79,2. Maya DS4 aventaja al DSX Q190 por 3 puntos observados en Q172 con semillas 42–44. Es una diferencia descriptiva con n=3, no una conclusión estadística; no alcanza el umbral preregistrado de borrado (≥5 puntos de déficit más menor velocidad). La Maya original de Q190 (84,67) es otro perfil y no se hereda a DS4. | Maya DS4 es la opción provisional para priorizar Q172; DSX conserva decode y LHA superiores. No hay un ganador único en todas las dimensiones. Ambos perfiles fallan TC-92 en todas las semillas Q172: sin autonomía ni datos multi-tenant.
| SOL | Qwen3.8 Flash-Next RCO IQ2_XS · NInfer-all v3 · Q206 build fc12 | Q172 81,67/100 (n=3); Q173 P=2154,41/D=86,72 como medias equiponderadas de cinco contextos; LHA-1 60,8/100 (n=5). | Equilibrio y uso general. El resultado de contexto 1M con YaRN×4 pertenece al perfil Strata y no se hereda a NInfer. Q172 falló TC-74/82/92.
| TERRA | Ternary Bonsai 2 27B · NInfer-all v3 | Q172 83,33/100 (n=3); Q173 P=1513,90/D=157,44; LHA-1 60/100. | Alternativa para generación/output-heavy: decode mayor y prefill menor que SOL. No domina SOL en todas las métricas. Falló TC-74 y TC-92 en las tres semillas Q172.
| LUNA | Qwen3.6-35B-A3B · NInfer-all v3 · MTP3 (Q190) | Q172 74/100 (n=3; 73/70/79); Q173 P=5155,87/D=230,02, media equiponderada de cinco contextos; LHA-1 100/100 (n=5). | Mejor candidato rápido con ladder y calidad multi-semilla medidos. Apto sólo para respuestas de bajo riesgo sin herramientas mientras siga TC-91 en Q172. MTP4 queda fuera del rol: Q253 P=4600,61/D=214,04 y 6,95% menos decode que MTP3; Q172 79/100 es n=1 y falló TC-82/91.

## Candidatos que no cambian la asignación

- Qwen3.6 DFlash K=5: Q172 77/100, una semilla, y Q173 sólo 8K (P=6467,12/D=217,40); falló TC-71/74 y no superó la compuerta preregistrada de decode. No desplaza MTP3.
- DFlash K=1–4/DFlash2 K=2 no tienen Q172 del perfil exacto y sus pantallas 8K no superaron el gate de decode; no asignarles LUNA ni inferir calidad.
- ASTRA Qwen3.8 Flash-Next RCO IQ3_S tiene mediciones de más de un runtime pero Q172/LHA N/D; queda sin clasificar.
- KVARK Sparkle Q204 se detuvo ante un fallo crítico y no tiene Q172 válido; no asignar un rol hasta reparar o cerrar ese gate.

## Interpretación y próximo paso

Q172 es Tool-Eval, no una medida universal de inteligencia. Prefill, decode, Q172 y LHA usan cohortes y tamaños de muestra distintos. Los puntajes no permiten construir una escala lineal perfecta: TERRA aventaja a SOL por 1,66 puntos Q172 y tiene mayor decode, mientras SOL tiene mayor prefill; esa diferencia pequeña es descriptiva y no establece superioridad general. ASTRA también cruza métricas: Maya DS4 tiene mayor Q172 reciente, mientras DSX tiene mayor decode y LHA-1. La comparación Q172 DSX Q190 vs Maya DS4 Q206 comparte Tool-Eval 2.8.0, 131072 tokens, semillas 42–44 y esfuerzo medium/budget 75; deltas pareados Maya−DSX = −1/+5/+5, media +3 con n=3, descriptivo. El umbral preregistrado de 5 puntos era parte de la decisión de borrado, no una prueba estadística de superioridad. MTP3 queda como LUNA por su ladder, Q172 multi-semilla y LHA-1; MTP4 no lo desplaza. Los cuatro candidatos recomendados tienen al menos un fallo crítico de seguridad; la clasificación sólo establece el perfil técnico preferido y no autoriza herramientas, acciones externas ni datos sensibles.

No hace falta repetir ahora el Q172 de ASTRA: ya existe la comparación DSX Q190 vs Maya DS4 Q206 bajo el mismo protocolo y semillas, y no supera el umbral de desempate. La fila Qwen3.8 Flash-Next RCO IQ3_S sigue como candidata sin Q172/LHA comparables; sólo tendría sentido probarla si una decisión entre los perfiles Flash-Next puede cambiar el rol SOL/ASTRA. KVARK Sparkle y las variantes DFlash sin Q172 multi-semilla no reciben un rol. Para LUNA, no repetir Q172 ni LHA con el modelo intacto: primero hace falta corregir y validar TC-91, pues el LHA alto no anula ese fallo de autorización. El siguiente avance de campaña es elegir una prueba de alto valor de la cola, no reabrir comparaciones cerradas sin cambio de perfil.

## Sheet

La última lectura de la hoja viva fue 2026-11-17 18:09 UTC. En ese corte, las etiquetas `Perfil` quedaron así: `Modelos locales por peso!B8` = LUNA (Qwen3.6-35B-A3B MTP3); `B12` = evaluación MTP4 sin rol; `B16` = TERRA (Ternary Bonsai 2 NInfer-all v3); `B69` = SOL (Flash-Next IQ2_XS NInfer-all v3 Q206 fc12); `B80` = ASTRA · ALTERNATIVA (DSX T16); `B114` = ASTRA · PRINCIPAL (Maya DS4). La tabla está viva y las filas pueden cambiar de número; usar los nombres completos de perfil como identidad principal.

`Accionables!139` registra los cuatro roles y sus límites. `Modelos locales por peso!AA80/AA114` documenta el desempate Q172 DSX/Maya; `AA81` y `AA83` contienen notas propias de sus perfiles Qwen, sin trasladarles evidencia de DeepSeek. El readback posterior a las correcciones está en `receipts/sheet-readback-20261117T1809Z.json`.

## Revisión correctiva 2026-11-17

La lectura de la tabla viva mostró que LUNA estaba asignada a MTP4 pese a que Q253 confirma que su ladder queda 6,95% por debajo del control MTP3 en decode (214,04 frente a 230,02 tok/s) y también por debajo en prefill (4600,61 frente a 5155,87). MTP3 además tiene Q172 74/100 n=3 y LHA-1 100/100 n=5; TC-91 sigue siendo un bloqueo para tools/acciones. Se movió la etiqueta LUNA a la fila MTP3 (14) y se retiró de MTP4 (fila 2); no se alteraron métricas ni se ejecutó prueba nueva.

Las referencias de fila de ese registro describen el orden de la hoja a las 17:36 UTC. En una revisión posterior la hoja cambió de orden; los perfiles se buscaron por nombre y se actualizaron en las filas actuales indicadas arriba.

## Corrección comparativa ASTRA — 2026-11-17

La nota anterior decía que faltaba emparejar Q172 de DSX con Maya DS4. Ese pendiente era incorrecto: Q206 ya midió el perfil Maya `DS4_SPLIT=39,1` en Q172 2.8.0, 131072 tokens, semillas 42–44, sampling conservador y reasoning medium (budget efectivo 75). Al contrastarlo con DSX T16 Q190 en el mismo conjunto de escenarios y semillas, DSX obtuvo 89/84/86 (media 86,33) y Maya DS4 88/89/91 (media 89,33); diferencias pareadas −1/+5/+5, media +3 con n=3. Es una observación descriptiva, no una conclusión estadística. El umbral preregistrado de 5 puntos corresponde al gate de borrado (junto con la condición de menor velocidad), no a una prueba de superioridad. No hay ganador concluyente ni motivo para repetir Q172. Esto no reutiliza el score 84,67 de la Maya original de Q190, que es un perfil distinto. Ambos DSX y Maya DS4 fallaron TC-92 en 3/3 semillas. A efectos de los cuatro roles, se prefiere Maya DS4 como ASTRA provisional por el mayor Q172 observado; DSX queda como alternativa cuando primen decode y LHA. No se declara dominancia ni se autoriza autonomía.
