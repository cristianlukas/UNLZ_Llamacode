# Iteración 4 — VF-20261019-01

**Estado de esta iteración: bloqueada en las siguientes pruebas de modelo por condiciones externas; no equivale a que la cola completa esté terminada.** Lock `121263e9-8fdf-4971-a2ce-d3673b5b97f0`. No se descargaron pesos, no se inició un servidor de inferencia y no se usó GPU.

## Avances verificables

- **Swift 1.5 (#51):** la ficha y el manifiesto oficiales enumeran un GGUF estándar IQ2_XS de 8.422.841.632 bytes (SHA-256 `714c509c…a9de8`) además del archivo MTP de 8.771.311.616 bytes (SHA-256 `4414bc39…cab85`). Manifest y HEAD del GGUF estándar respondieron HTTP 200; eso sólo verifica disponibilidad de metadatos/endpoint, no descarga ni autorización de uso. Strata 0.1.41 no tiene una ruta verificada para el GGUF MTP de Swift. Una comparación sin MTP sería un experimento distinto y necesitaría un ASTRA IQ2_XS sin MTP emparejado en el mismo runtime. La licencia Swift Open License v1.0 condiciona el uso comercial a ingresos brutos consolidados menores a US$1M en el último ejercicio fiscal; el cálculo suma entidades bajo control común y por encima del umbral se requiere licencia empresarial escrita. La elegibilidad de Vector Fields no consta aquí, así que no se descargó el candidato. Se pidió confirmación al usuario.
- **OpenJet (#54):** revisión del código fijado resolvió que 65 no es una errata aislada: el megakernel define `NL=64`, `NLA=65`, comenta 64 bloques base más un bloque MTP y rechaza `qwen35.block_count != 65`. El Qwen3.8-27B Q4_K_M local tiene 64 bloques y no contiene MTP. Cambiar sólo la comprobación permitiría pasar el loader, pero no aportaría los pesos/estado MTP que usa el kernel; no se parcheó ni se inició una inferencia candidata. Reabrir con un artefacto Qwen3.8 GGUF con MTP compatible y quant admitida, o soporte explícito upstream de modo sin MTP.
- **S36:** consulta actual del Reel y de oEmbed volvió a fallar por throttling; sigue faltando caption, transcripción, captura legible o mirror atribuible. No se inventó el fixture.
- **S23:** la nueva lectura de cgroups sigue mostrando `io` sin delegar en `user.slice` (`cpu memory pids` solamente). Los intentos anteriores del mismo loader ya abortaron por PSI; no se repitió la carga.
- **UD-IQ4_XS:** no se repitió BCB8. El EVAL preservado muestra que la salida del modelo devolvió un `MagicMock` donde la tarea exige un string; el replay determinista previo ya probó que ese fixture pasa 5/5. Las campañas completas agotaron 1.800 s y 7.200 s. Una nueva corrida con el mismo runner no está justificada; haría falta una variante con aislamiento y límite por tarea, grader con dependencias fijadas y fingerprint nuevo antes de cualquier score válido.
- **Preflight del host:** no se detectó servidor de inferencia ni listener en los puertos de evaluación consultados. `nvidia-smi` reportó ArtCraft GUI usando 207 MiB; se dejó intacto y no se reservó GPU porque no se ejecutó inferencia. El servidor de Codex/GUI no se interpretó como servidor de modelos.

## Qué falta para continuar

1. Confirmación del usuario de que el uso comercial queda dentro del umbral Swift o de que existe licencia empresarial; además, acceso autorizado a los pesos. Entonces preregistrar aparte la comparación no-MTP y validar si existe un control ASTRA no-MTP realmente equivalente y seguro.
2. S36 sólo ante evidencia primaria recuperable; S23 sólo ante estrategia de lectura segura distinta ya validada en seco; OpenJet sólo ante un checkpoint/kernel realmente compatible; UD-IQ4_XS sólo con un runner/grader corregidos, acotados por tarea y una huella nueva.
3. Harness² calidad sigue necesitando un workflow y holdout sintético concreto, y una estrategia de carga que no reproduzca el aborto por PSI.

La cola canónica permanece con 58/58 materiales clasificados; la evaluación y ejecución completa de cada prueba justificada **no está terminada** mientras queden estos accionables condicionados.
