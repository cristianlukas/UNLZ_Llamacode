# Plan — Q-20261018-LLAMACPP-MTP-REMAINING

Inicio: 2026-10-18T13:16:47Z. Token de cola: `9a8ab269-7135-48d2-aea7-01cd04aa5b70`.

## Objetivo

Revisar y completar, si es seguro y metodológicamente válido, las pruebas de
coding/agentes que quedaron incompletas en los screens de Q4 llama.cpp MTP.
No repetir Hard Mode, velocidad, HE0/HE20 ni resultados válidos ya registrados.

## Candidatos, controles y huellas ya ejecutadas

- Base Qwen3.8-Flash-Next UD-Q4_K_XL, revisión
  `38bb39ee97821de2c9009abb7e93950eec396e66`; shards y hashes completos en
  [base-model-hashes.json](../Q-20261017-LLAMACPP-MTP-CODING-RESUME/receipts/base-model-hashes.json).
- Control MTP-off: llama.cpp commit
  `836d57176dc699a726c55418e4f96b8ca628e1bf`, fingerprint BCB8
  `7f84727070a2fb93d008a42c90391f3904d800f7d7c2e67f173813ab0435ff89` y
  TaskFlow R8192 `e9c5c527e30744049cff955f0489c36cd08a8777b9bf87422f0f768c3d42cf23`.
- Candidato MTP-on: mismo modelo base y sidecar Q8_0 SHA-256
  `58a47d6a216307e9b97172d5bfdc3436a8994b632f5e436b9bb6edf8951da8d1`;
  TaskFlow fingerprint histórico
  `b39dcfa4f912aee2ae973d28f25ac04f81e5ba1c0dbaaa2e0a7e5641e38d3d27`.
- HarnessSpec `cca4645b28930b079288b139a2bf473b7a2b6719980445811bd3a731168832ef`;
  BCB8 suite SHA-256
  `42771136b447b7b5619e04a1ea211f663222cd6752ca38d995083b5a4d207574`;
  TaskFlow ULTRA SHA-256
  `f04febb440208d5bf74c01e84d78f5127e57c164fabece2acbfb346215dc0c17`.
- Los fingerprints de TaskFlow son R8192, seed 4242 y temperatura efectiva
  0,1. El preflight actual no obtuvo mediciones de perfil, runtime binario ni
  carga porque no se inició el servidor. Los recibos completos de la corrida
  previa están bajo el directorio enlazado arriba.

## Pruebas que siguen sin resultado completo

- BCB8 control MTP-off: la corrida del 2026-10-17 aceptó 4/8 ítems, pero se
  canceló el prompt 4 tras más de 15 minutos sin progreso. No hay score final.
- TaskFlow ULTRA MTP-off: la corrida se canceló tras un probe 3/10 y una
  búsqueda fuera del workspace; no hay score final.
- TaskFlow ULTRA MTP-on: 0/13 tras tres reparaciones; es un fallo válido de
  calidad, no una corrida incompleta.

No se repetirán esas huellas idénticas sólo para duplicar los resultados.
Para un retest útil primero se necesita una estrategia que impida búsquedas
fuera del workspace y permita terminar BCB8; una modificación de prompt,
HarnessSpec o runner debe quedar fijada y generar un fingerprint nuevo, aplicado
igual a ambos brazos si se hace A/B. Una mejora estable requiere tres corridas
válidas emparejadas por brazo. La decisión vigente no promueve MTP.

## Preflight y criterio de inicio

Antes de inferencia: ambas RTX 3090 sin procesos ajenos, puertos de prueba
libres, MemAvailable ≥40 GiB, PSI estable y artefactos/configuración verificados.
No detener servicios ajenos. Si alguna GPU está ocupada, no iniciar el modelo.

Resultado del preflight de 2026-10-18: las dos GPUs alojaban servidores
Qwen3.5-9B de PeritoSoft en puertos 8033 y 8081 (PIDs 8459 y 15451); uso
reportado 6,4/7,1 GiB y utilización 0/20%. Se detuvo aquí antes de reservar GPU
o cargar el modelo. [Recibo](receipts/preflight.json).

## Pruebas previstas al reanudar

1. Inspeccionar/fijar el cambio de estrategia de workspace y calcular el nuevo
   fingerprint antes de cualquier llamada al modelo.
2. Ejecutar BCB8 MTP-off hasta las ocho aceptaciones o registrar una condición
   válida de cancelación; una salida parcial no es score.
3. Ejecutar TaskFlow ULTRA con el mismo flujo corregido en MTP-off y MTP-on,
   en serie, con desglose 10 archivos + `py_compile` + `unittest` + `--self-test`,
   score inicial y después de cada una de hasta tres reparaciones.
4. Hacer al menos tres pares válidos si se pretende afirmar mejora estable.
