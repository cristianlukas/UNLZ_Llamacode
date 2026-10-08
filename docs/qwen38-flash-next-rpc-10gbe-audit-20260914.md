# Auditoría: Flash-Next distribuido por RPC sobre 10GbE — 2026-09-14

## Resultado

El reporte prueba Qwen3.8-Flash-Next UD-Q4_K_XL con MTP, 263K de contexto y KV
F16 repartido entre una RTX 5090 y una RTX 3090 ubicadas en dos PCs conectadas
por 10GbE. El mejor resultado publicado es de aproximadamente 19–23 tok/s.

Eso no supera ningún perfil prioritario de LlamaCode y no es comparable
directamente con nuestro reparto local: tenemos dos RTX 3090 en el mismo host,
P2P PCIe disponible y no necesitamos serializar las transferencias del modelo
por una red de 10GbE.

## Cruce con nuestras mediciones

| Variante | Rendimiento | Calidad/estado | Decisión |
| --- | ---: | --- | --- |
| Flash-Next RPC, 10GbE, MTP, KV F16 | 19–23 tok/s | Sin BCB ni tool-use comparable | No adoptar |
| ASTRA local, cache MoE | ~16–41 tok/s según variante | Experimental; algunas recetas corrompen la salida | No promover |
| QWEN38-Q8 local, contexto corto/largo | ~41,3 tok/s a 8K / ~22,1 a 262K | Smoke funcional; BCB pendiente | Experimental |
| SOL TP2/P2P + MTP4 | 74 tok/s narrativo / 102 tok/s código | BCB 8/8 y tool-use OK | Default |

El reporte alternativo menciona Qwen3.8-27B Q8 con 263K y KV F16. En
LlamaCode no se puede usar KV F16 en un perfil promovible: el límite del
proyecto es Q8. Además, nuestras mediciones del QWEN38-Q8 con KV Q8 ya
mostraron la penalización esperable al llenar el contexto, sin superar a SOL.

## Qué sí confirma

- RPC de llama.cpp es útil para capacidad o experimentación cuando no hay otra
  forma de sumar VRAM.
- Una red de 10GbE introduce un cuello de botella importante para el tráfico
  de expertos, activaciones y/o capas repartidas.
- Para una sola estación con dos GPU, conviene priorizar reparto local por
  capas/P2P antes que dividir el modelo entre máquinas.
- La comparación debe medir contexto lleno, no sólo el arranque de una sesión.

## Pruebas locales relevantes ya realizadas

- P2P lectura y escritura entre las dos 3090: OK.
- Reparto por capas con P2P: ~60,75 tok/s frente a ~60,61 sin P2P en el
  backend llama.cpp experimental; diferencia dentro del margen de medición.
- SOL vLLM TP2/P2P con MTP4: 74,03 tok/s narrativo y 102,36 tok/s código,
  con BCB 8/8 y tool-use correcto.
- Tensor split para Flash-Next: no implementado para `qwen4exp` en la build
  probada.

No se ejecutó una prueba RPC nueva porque no hay un segundo nodo remoto dentro
del setup de LlamaCode y el resultado externo ya queda por debajo de SOL. Una
prueba sobre localhost no representaría la latencia ni el ancho de banda de
10GbE y no aportaría una decisión útil.

## Decisión de perfiles

- SOL permanece como perfil principal y predeterminado.
- QWEN38-Q8 queda como experimental para fidelidad/contexto extremo.
- ASTRA sigue siendo la ruta experimental Flash-Next con cache de expertos.
- No se agrega un backend RPC, no se modifican los argumentos de SOL y no se
  descarga ningún modelo adicional.

La referencia queda anotada como evidencia de que la segunda máquina sólo
conviene si aporta un enlace de interconexión mucho más rápido que 10GbE o si
el objetivo es capacidad, no latencia de un agente interactivo.
