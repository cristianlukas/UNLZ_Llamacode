# Auditoría PCIe y bifurcación x8/x8 — 2026-09-18

## Resultado

La recomendación externa de usar bifurcación PCIe x8/x8 no aporta una mejora
clara a este equipo. Las dos RTX 3090 ya están conectadas a puertos raíz de la
CPU y el enlace entre ellas aparece como `PHB` en `nvidia-smi topo -m`.

Topología observada:

| GPU | Bus | Enlace observado | Máximo reportado | Ruta |
|---|---|---:|---:|---|
| GPU0 | `01:00.0` | Gen4 x8 en reposo | Gen4 x16 | Root port CPU `00:01.1` |
| GPU1 | `03:00.0` | Gen2 x8 en reposo | Gen4 x16 | Root port CPU `00:01.3` |

La diferencia Gen4/Gen2 observada es dinámica por estado de energía en reposo;
no demuestra que la segunda GPU esté conectada al chipset. Ambos dispositivos
están bajo el complejo PCIe de CPU y `nvidia-smi topo -m` reporta `PHB`.

## Relación con las pruebas anteriores

- P2P GPU0↔GPU1: lectura **OK**.
- P2P GPU0↔GPU1: escritura **OK**.
- NVLink: no disponible.
- Reparto por capas con P2P: **60,75 tok/s**.
- Reparto por capas sin P2P: **60,61 tok/s**.
- Mejora medida: **~0,2%**, dentro del ruido.
- Tensor split: no inició; fallo del runtime en `SPLIT_MODE_TENSOR`/NCCL.

Por lo tanto, una bifurcación física no corrige el cuello observado: los
perfiles estables usan `split-mode layer`, y en ese modo el tráfico P2P no fue
el límite dominante. Tampoco convierte automáticamente el runtime tensor-split
en un modo funcional.

## Decisión

No cambiar la placa madre, no comprar un adaptador de bifurcación y no alterar
los perfiles de LlamaCode. La bifurcación sólo sería razonable si una futura
placa dejara una GPU detrás del chipset, limitara el enlace a x1/x4 o se
adoptara un runtime tensor-parallel validado; ninguna de esas condiciones se
cumple ahora.

El hallazgo útil del post queda registrado como regla de diagnóstico: antes de
invertir en hardware hay que verificar `nvidia-smi topo -m`, la ruta de los
root ports, el ancho de enlace bajo carga y P2P real. En esta máquina esos
controles ya son favorables.
