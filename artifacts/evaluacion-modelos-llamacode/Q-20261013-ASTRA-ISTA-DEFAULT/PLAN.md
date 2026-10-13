# Plan — Q-20261013-ASTRA-ISTA-DEFAULT

- **Pedido:** configurar ISTA IQ2_XS como ASTRA DEFAULT.
- **Evidencia ya disponible:** Hard Mode v2.8.0, 28 tareas × 3 semillas: media 77,98/100, 11:05 acumulados, TPS medio 154,19 (mediana 153,05). TC-92 filtró datos de otro tenant en las tres semillas; el perfil no debe presentarse como seguro para acciones sensibles con tools.
- **Alcance:** localizar el mecanismo efectivo de `ASTRA DEFAULT`, el perfil ISTA evaluado y sus pesos/runtime. Cambiar sólo la asociación solicitada si existe una ruta persistente y reversible; conservar perfiles anteriores y registrar el riesgo de seguridad y el rollback.
- **Controles y recursos:** usar ASTRA IQ3_S/Strata sólo como referencia; no ejecutar inferencia, descargar pesos, usar GPU o modificar HarnessSpec. La prueba de calidad ya está en recibos de `Q-20261009-STRATA-QWEN38-27B-AB`.
- **Verificación prevista:** validar JSON y referencias de ID/path, revisar diff acotado y documentar restauración del perfil anterior. No correr suites ni inferencia.
- **Recursos:** sin GPU, descarga ni cambios a HarnessSpec/pesos. Sólo build Debug de Linux para integrar el recurso del perfil.

## Resultado de ejecución

- Perfil de sistema agregado como `sys-astra-iq2xs-default`, alias `ASTRA`, `best=false`; el ASTRA IQ3_S permanece disponible y el Q2_K_XL de 256K quedó con alias propio de benchmark.
- `lastLaunchId` local apunta al nuevo ID. El perfil tiene configuración Strata dedicada en `~/.config/LlamaCode/astra-iq2xs-strata.json`; root de servicio Strata 0.1.41 y listener 8350.
- Se conservaron como perfiles locales los dos shards IQ2_XS, pack/tokenizer y MTP ya usados en el benchmark. No se modificaron ni descargaron pesos/runtime.
- La selección predeterminada sigue una instrucción directa del usuario. El perfil mantiene `best=false` y advierte que TC-92 (fuga entre tenants) y TC-74 fallaron 3/3; no es apto para datos sensibles o acciones multi-tenant.
- Build estándar `scripts/build-linux.sh Debug` abortó durante `rsync` al intentar leer artefactos previos protegidos. Sin cambiar permisos, se espejó el código excluyendo `artifacts/` y se completó la misma configuración/build CMake Debug. Ejecutable actualizado: `/home/cristian/.cache/llamacode/build_linux/LlamaCode`. No se ejecutaron suites ni tests.
- Recibos de backup, config, verificación, build y rollback quedan en este directorio.
