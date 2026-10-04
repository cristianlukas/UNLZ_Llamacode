# Strata-DualGPU: validación LC-H1 en LlamaCode

Fecha: 2026-10-04
Estado: **gates de calidad aprobados; perfil sin promover**.

## Decisión

El fork completó HE0, HE20, BCB8 y adversarial desde el benchmark administrado de LlamaCode. Cada suite terminó sin timeout ni error de infraestructura; sus resultados finales fueron 1/1, 20/20, 8/8 y 10/10. El primer intento de HE0 tuvo 0/1 y pasó con una reparación. El fingerprint del HarnessSpec fue idéntico en las cuatro suites y `thinkingEnabled=true`, igual que en la referencia elegida.

No promoví ni edité perfiles de producción. La referencia Strata 0.1.35 con el mismo IQ3_S también pasó HE20 (20/20), mientras el fork tardó más en HE20 y en adversarial en estas corridas. BCB8 mejoró de 7/8 final (referencia incompleta/fallida) a 8/8. La evidencia confirma que el fork funciona y pasa los gates funcionales, pero no respalda promoverlo como mejora general de rendimiento: el microbenchmark de velocidad previo y el harness de coding miden cargas distintas, el fingerprint de perfil difiere entre motores y no repetí la comparación emparejada. Mantenerlo experimental hasta una comparación repetida con fingerprint y protocolo controlados.

## Configuración

- Fork `Hardin22/Strata-DualGPU`, commit `73bbf3861b48e258cfd076ba7970c078373b8e1a`, Strata 0.1.38.
- LlamaCode `ASTRA · Strata IQ3_S · Qwen3.8 Flash Next` (`sys-astra-strata-iq3s`), mediante su benchmark agent administrado, target `agent`, perfil `agent-maximo` / Máximo.
- Modelo Qwen3.8-Flash-Next-GSQ-RCO IQ3_S, los mismos dos shards, pack, tokenizer, MTP4 y expert profile del ensayo previo; 2× RTX 3090.
- Configuración del fork: contexto 131072; KV int8; 32768 celdas residentes; `--spec 4`; `--spec-min-p 0.5`; dos GPU con layer split automático; prompt cache apagado.
- Thinking activado. `harnessSpecHash=sha256:cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef` en las cuatro etapas. `profileConfigFingerprint=96d34ceb688ca8de83efccd1f26e1b52d8fdc1ce20fb5dd2622b510ba9d41da0` en las cuatro etapas.
- El archivo de configuración específico de la corrida es `artifacts/strata-dualgpu-lch1-20261004/strata-dualgpu-iq3s.json`. Los perfiles y valores de producción no se cambiaron. Se usó la instancia de prueba `.qttest` de LlamaCode y se restauraron sus ajustes temporales ASTRA al terminar.

## Resultados

| Etapa | Primer intento | Final | Reparaciones | Tiempo | TPS medio | Resultado |
|---|---:|---:|---:|---:|---:|---|
| HE0 | 0/1 | 1/1 | 1 | 16,1 s | 118,6 | Pasa, sin timeout |
| HE20 | 19/20 | 20/20 | 1 | 779,6 s | 108,3 | Pasa, sin timeout |
| BCB8 | 2/8 | 8/8 | 1 | 967,2 s | 99,6 | Pasa, sin timeout |
| Adversarial | 7/10 | 10/10 | 1 | 702,2 s | 100,0 | Pasa, sin timeout |

IDs nuevos de LlamaCode: HE0 `f63b9395-6118-47a3-aae5-49d25bda7dc1`; HE20 `68e79445-0033-49aa-90a9-5aa8a03d0582`; BCB8 `abb04a3c-35ea-4e44-96ae-701697237a0a`; adversarial `8febe0e6-d604-4a85-8bc8-b4f11e8aadea`. Los JSON guardados incluyen los resultados completos y las aceptaciones por tarea.

### Referencia Strata 0.1.35

Los artefactos de referencia registran `thinkingEnabled=true` y el mismo hash de HarnessSpec. Su HE20 fue 20/20 en 272,4 s con 128,2 TPS medios. El fork tardó 779,6 s y midió 108,3 TPS medios en esta ejecución (aprox. 2,86× el tiempo y 15,5% menos TPS). Adversarial fue 10/10 en ambos; la referencia tardó 534,9 s a 106,1 TPS medios, y el fork 702,2 s a 100,0 TPS medios. La referencia BCB8 acabó 7/8 después de dos reparaciones y quedó marcada como fallida; el fork terminó 8/8 después de una.

Esta comparación es orientativa, no un A/B causal: los fingerprints de perfil son distintos (`2a78d3e735d420b858728e1c0a7f76153d40fbfc03aef9272f7dd37addece5ad` en la referencia y `96d34ceb...` en el fork), como corresponde a motores/configuraciones distintos; además, sólo hay una corrida por variante. El resultado anterior del microbenchmark, que mostró +15,2% en código y paridad en prosa, no sustituye el tiempo end-to-end del harness.

## Incidencia descartada

Una invocación inicial no arrancó el servidor porque el puente de control de la instancia `.qttest` escribió ajustes ASTRA como valores nulos. LlamaCode registró 0/0 en 0,02 s, sin generación; esa fila no es un resultado de HE0 y se conserva en `artifacts/strata-dualgpu-lch1-20261004/discarded/he0_server-start-failed.json`. Se corrigió la configuración temporal, se verificó el arranque del fork por la ruta ASTRA/Strata de LlamaCode y la corrida válida de HE0 pasó. Ningún servidor quedó activo al finalizar.

## Archivos y decisión operativa

- Resultados válidos: `artifacts/strata-dualgpu-lch1-20261004/he0.json`, `he20.json`, `bcb8.json`, `adversarial.json`.
- Configuración efectiva usada: `artifacts/strata-dualgpu-lch1-20261004/strata-dualgpu-iq3s.json`.
- El detalle de la evaluación de velocidad previa y sus límites sigue en `docs/strata-dualgpu-audit-20261003.md`.
- No se modificaron `assets/system_profiles.json`, `profiles/launches.json`, `profiles/runtimes.json`, ASTRA ni SOL; no hubo promoción.
