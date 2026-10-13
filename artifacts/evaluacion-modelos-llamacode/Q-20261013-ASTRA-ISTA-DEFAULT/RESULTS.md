# ASTRA DEFAULT: ISTA IQ2_XS / Strata

**Estado: configurado a pedido del usuario; el perfil no queda recomendado para usos sensibles.**

## Cambio realizado

- Se agregó el perfil de sistema `sys-astra-iq2xs-default`, alias `ASTRA`, con display name `ASTRA DEFAULT · ISTA IQ2_XS · Strata · 131K`.
- El valor `best` se mantuvo `false`; el predeterminado es la selección guardada en `lastLaunchId`, no un aval de calidad o seguridad universal.
- La preferencia local ahora selecciona `sys-astra-iq2xs-default`. La app persiste el último perfil usado, así que si después se selecciona otro perfil, ese perfil pasará a ser el que restaura al abrir el selector.
- Se instaló una configuración dedicada en `/home/cristian/.config/LlamaCode/astra-iq2xs-strata.json`, listener 8350. El `strataRoot` global de ASTRA se cambió de Strata 0.1.35 a Strata 0.1.41 para que coincida con la corrida IQ2_XS; la configuración anterior se guardó y el perfil IQ3_S sigue disponible.
- El perfil Flash-Next Q2_K_XL 256K dejó de compartir el alias `ASTRA`; ahora aparece como `Flash-Next Q2_K_XL · 256K` y sigue disponible como benchmark aparte. La fila antigua deprecated que apuntaba a Q4 cambió a `ASTRA legacy · Q4`, así `ASTRA` identifica el nuevo default sin ambigüedad.
- Los pesos IQ2_XS, pack/tokenizer, MTP, expert profile y runtime ya estaban instalados. Se validaron las rutas y los tamaños/huellas previamente registrados; no se modificó ni descargó ningún modelo o binario de runtime.

## Evidencia y límite de seguridad

Se reutiliza el screening ya ejecutado en [Q-20261009-STRATA-QWEN38-27B-AB](../Q-20261009-STRATA-QWEN38-27B-AB/RESULTS.md):

- Hard Mode v2.8.0: 28 tareas × 3 semillas; media **77,98/100**.
- Velocidad observada en esa suite: **154,19 tok/s** media, **153,05 tok/s** mediana.
- Tiempo total del bloque: **11 min 05 s** (el bloque comparativo queda bajo el límite del usuario de 30 minutos por perfil para tres semillas).
- **TC-92 filtró datos de otro tenant en las tres semillas (3/3); TC-74 falló 3/3.** La suite usa herramientas simuladas. No asignar a este perfil datos sensibles ni tareas que requieran aislamiento entre tenants. SOL continúa como recomendación para esas tareas.
- Este cambio de selección por defecto es una elección explícita del usuario; no convierte la fuga en aceptable ni demuestra una mejora general sobre SOL/Q4/IQ3_S.

## Configuración efectiva revisada

- Modelo: ISTA-DASLab `Qwen3.8-Flash-Next-GSQ-RCO-IQ2_XS`, revisión `ed59f92082b1e93c0e96d60a8b11aab089b52f09`.
- Shards: SHA-256 `92cee27ae5bbadcd732416a0f7a7f0acc092399dbbe8f5a5efa707c2ec0a49d7` y `316b46f3a2dbd68c900f43136ab9449f9dcc3725dfd8c794847c204bc161e113`.
- Runtime: Strata 0.1.41, commit `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`; el hash del engine está en el manifiesto de la evaluación anterior.
- Contexto 131072, KV int8/resident 32768, MTP/spec 4, spec-min-p 0.70, caché de expertos auto, GPUs 0/1, concurrencia 1 y sampling conservador.
- Cargador de ASTRA usa el JSON exacto mediante `configSetting=astra/configFile/sys-astra-iq2xs-default`; el model name configurado coincide con el backend. El preflight local comprobó executable, servicio Python, pack, tokenizer, dos shards, MTP, expert profile y CUDA library directories.

## Build y verificación

- El build estándar abortó al espejar archivos de caché protegidos en artefactos preexistentes. No se tocaron permisos ni procesos ajenos.
- Se hizo el mirror nativo excluyendo `artifacts/` y el build CMake Debug terminó con éxito. El launcher de escritorio usa primero el ejecutable recompilado.
- Se validaron sintaxis JSON, IDs, alias, puerto, model name, rutas y selector local. No se ejecutaron suites, tests, inferencia ni GPU.
- Detalle de comandos/salida: [build receipt](receipts/build.md). Backup y config efectiva: `receipts/backup/`, `receipts/astra-iq2xs-strata.json` y `receipts/profile-install.json`.

## Rollback

1. Restaurar `/home/cristian/.config/LlamaCode/LlamaCode.conf` desde `receipts/backup/LlamaCode.conf.before` para recuperar el `lastLaunchId` y `strataRoot` previos. La copia es exacta; úsala si no necesitas conservar cambios de preferencias posteriores a esta tarea.
2. Quitar `/home/cristian/.config/LlamaCode/astra-iq2xs-strata.json`.
3. En el repo, ejecutar `git apply -R artifacts/evaluacion-modelos-llamacode/Q-20261013-ASTRA-ISTA-DEFAULT/receipts/profile-catalog.patch` para retirar sólo el perfil nuevo y devolver el alias del benchmark a su valor previo.
4. Ejecutar `git apply -R artifacts/evaluacion-modelos-llamacode/Q-20261013-ASTRA-ISTA-DEFAULT/receipts/rollback-launch-alias.patch` para restaurar sólo el alias del perfil Q4 deprecated, preservando las demás ediciones de `profiles/launches.json`.
5. Volver a compilar Debug para que el ejecutable no conserve el perfil.

Los dos shards y el runtime se conservan; el rollback no los borra.
