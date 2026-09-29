# Auditoría: retraining PCIe en splitter x8/x8 — 2026-09-28

## Decisión

El post aporta un procedimiento de diagnóstico útil **si aparece una falla PCIe
real**, pero no mejora los perfiles, el harness, Computer Use ni INGI-CHARLA de
esta instalación. No se cambia ningún perfil ni se fijan bits PCIe al arranque.
La topología medida no coincide con la del autor: las dos RTX 3090 están en
puertos raíz CPU independientes (`00:01.1` y `00:01.3`), con ruta `PHB`, y no se
observa un riser pasivo x8/x8 en la ruta.

El hilo de Reddit también incluye cifras de dos Radeon R9700 con vLLM-Radiance
(prefill, decode agregado, concurrencia y TTFT), pero usa otras GPU, runtime y
carga. No son una comparación de perfiles GGUF/vLLM de LlamaCode ni justifican
crear un perfil de modelo.

## Qué afirma el artículo

El autor atribuye bloqueos de carga de vLLM, timeouts y errores GPU a
renegociación repetida del enlace en un riser pasivo conectado a una ranura
bifurcada x8/x8. Muestreó el registro `LnkSta` del puerto raíz bajo tráfico y
encontró el bit de entrenamiento activo. Desactivó el cambio autónomo de
velocidad y ancho en ambos extremos, fijó el objetivo en Gen3 y comprobó copias
host↔GPU de 6,72/6,76 GB/s por placa, también en simultáneo. El arreglo requiere
escrituras `setpci` privilegiadas y persistencia de arranque mediante systemd.

La observación transferible es metodológica: una lectura de velocidad en reposo
no basta; hay que correlacionar el estado del puerto raíz y el endpoint bajo
carga, y buscar errores/timeout. No se debe inferir que cualquier enlace x8 o
una generación dinámica en reposo sea una falla.

## Evidencia local existente

La [auditoría de bifurcación x8/x8](dual-3090-pcie-bifurcation-audit-20260918.md)
ya registró dos 3090 en root ports CPU, P2P de lectura y escritura funcional,
`split-mode layer` con 60,75 tok/s y sin P2P con 60,61 tok/s. Tensor split no
inició con el runtime probado. La auditoría concluyó que la bifurcación no
mejoraba el cuello de botella medido.

La [comparación de allreduce](dual-3090-llama-cpp-allreduce-post-audit-20260918.md)
ya aisló P2P/NCCL: el A/B por capas varió aproximadamente 0,2%, mientras que
tensor split siguió sin iniciar. El baseline de SOL continúa siendo el perfil
validado para agente; estas pruebas no señalan al enlace PCIe como cuello actual.

## Comprobaciones nuevas de esta revisión

Todas las comprobaciones fueron de lectura. No se escribieron registros PCIe,
no se alteraron relojes/BIOS, no se inició una carga adicional y no se reinició
ningún servicio.

| Comprobación | Resultado |
|---|---|
| `nvidia-smi topo -m` | GPU0↔GPU1 = `PHB` |
| `nvidia-smi topo -p2p r` / `w` | `OK` en ambas direcciones |
| Puertos raíz | GPU0 `00:01.1`; GPU1 `00:01.3` |
| Ancho máximo / observado | Ambas: x16 máximo, x8 observado |
| Generación observada por sysfs | GPU0 Gen4; GPU1 Gen2 en la muestra ociosa |
| `CAP_EXP+12.w`, 12 muestras a 1 s | GPU0: puerto `3084`, GPU `1084`; GPU1: puerto `3082`, GPU `1082`; valores estables en las 12 muestras |
| Procesos CUDA al revisar | Un `llama-server` ya usaba ambas GPU; no se lo interrumpió |
| Log del kernel disponible | Sin líneas Xid/AER observadas desde el arranque actual; esto no es historial completo ni prueba bajo stress |

La diferencia Gen4/Gen2 de esa muestra es coherente con estados de energía en
reposo y no muestra retraining: el bit de entrenamiento no apareció en las
lecturas. La muestra fue breve y no se tomó durante una copia host↔GPU; por lo
tanto sirve sólo como control sin carga significativa. El diario empieza con
este arranque; no hay evidencia para afirmar que nunca hubo errores históricos.

El C++ de `HardwareDiagnostics` ya recoge generación/ancho publicados por
`nvidia-smi`, topología y estado P2P; la política existente recomienda `layer`
cuando el enlace es débil o desconocido. No falta una capacidad general que
justifique una modificación de código para este post.

## Registro para no repetir la misma prueba

- **Ya cubierto:** `nvidia-smi topo -m`, P2P read/write, inspección de root
  ports, capacidad/ancho PCIe, A/B por capas con y sin P2P, intento de tensor
  split y muestreo de `LnkSta` en reposo en ambos extremos (12 × 1 s).
- **No repetir sin un síntoma nuevo:** la matriz de P2P y el benchmark de
  `split-mode layer` anterior; no responden a una hipótesis distinta y ya están
  registrados en las auditorías enlazadas.
- **No realizado aquí:** test de copia pinned-memory host↔GPU, stress simultáneo,
  locks Gen3/Gen4, deshabilitar cambios autónomos, ni prueba de overnight. No
  corresponden sin indicios de retraining y requieren actividad/cambios del
  dispositivo. El artículo no aporta motivo para escribir esos registros en
  esta máquina.
- **Condición para reabrir:** un timeout/Xid/reset nuevo, una carga que se
  cuelgue al inicializar o evidencia de retraining bajo una carga normal. En ese
  caso se registra primero hora, BDF/root port y estado simultáneo de ambos
  extremos durante la falla; luego se corre una copia host↔GPU controlada y se
  compara throughput/log antes de probar un cambio reversible, uno a la vez.

## Fuentes

- [Artículo sobre retraining PCIe en splitter x8/x8](https://doug.sh/posts/pcie-splitter-rtx-3090/)
- [Auditoría local de bifurcación PCIe y P2P](dual-3090-pcie-bifurcation-audit-20260918.md)
- [Auditoría local de allreduce y NCCL](dual-3090-llama-cpp-allreduce-post-audit-20260918.md)
