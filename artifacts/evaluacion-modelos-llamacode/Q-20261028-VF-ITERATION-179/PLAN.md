# Q179 — Flash-Next NInfer-all dual · Q172 calidad/seguridad

## Pregunta de decisión

¿El perfil dual Q178 A05 con Flash-Next RCO IQ2_XS conserva una calidad conductual suficiente para considerar su uso con herramientas? El Q172 de Q173 pertenece a NInfer preview v0.16.1/GPU1 y no se atribuye al runtime NInfer-all v3. Se mantiene como antecedente visible.

## Prueba preregistrada

- Ejecutar una sola vez Tool-Eval Hard Mode 2.8.0, TC-70..TC-97, seed 42, variant-seed 20261010, una prueba/una concurrencia y reasoning medium.
- La ladder de rendimiento no se repite: Q178 A05 ya midió el perfil dual de 8K a 256K con las dos RTX 3090. Se conserva aparte la fila histórica Q173 preview/GPU1 para que la comparación de perfiles siga visible.
- Pesos IQ2_XS/RCO convertidos a NInfer v3, artefactos y runtime fijados por SHA-256 en el recibo preregistrado.
- Host dual RTX 3090: NInfer-all pipeline, una etapa por GPU, expertos residentes en dispositivo, KV int8 y capacidad 262.144 con 32.768 posiciones residentes y sparse KV en host. No TP; coincide con la capacidad del perfil Q178 A05.
- Sampling: temperature 0,6; top-p 0,95; top-k 20; min-p 0; repeat penalty 1; presence penalty 0; seed 42.
- Servicio loopback aislado en puerto 18480. El ejecutor y sus hijos se colocan en background.slice, sin límites artificiales de memoria; GUI preservada.
- No se inicia si cambia el lock, hay otro inference server/contenedor, el puerto está ocupado, no están visibles ambas RTX 3090, los SHA no coinciden o MemAvailable cae por debajo de 32 GiB.
- Durante la ejecución se revisan lock, servidores ajenos y memoria cada 15 segundos. Cuatro muestras seguidas bajo 32 GiB, error CUDA/OOM, desaparición de GPU, salida del servidor o bloqueo de contexto detienen la corrida. No se detienen procesos ajenos.
- Si Q172 queda completo, se conserva el resultado de la única semilla y no se agregan semillas tras un gate crítico fallido.

## Interpretación

Este screen es de calidad y seguridad, no de velocidad. Un resultado favorable no prueba superioridad general ni habilita promoción automática; un fallo crítico mantiene el perfil fuera de uso con herramientas o datos sensibles. El score no se combina con el 77/100 del preview histórico ni con el Q172 de Strata.

Prerregistro: receipts/prereg-q179-ninfer-all-dual-q172.json. Amendment A02 alinea capacidad con Q178 y fija el SHA final del runner: `receipts/prereg-amendment-02-context-and-runner.json`. Se usará `background.slice` sin límite artificial de memoria; aislamiento validado por A01. Runner: scripts/run_q179_q172.py.
