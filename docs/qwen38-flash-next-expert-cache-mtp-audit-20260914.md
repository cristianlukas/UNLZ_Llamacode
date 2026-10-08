# Auditoría: Flash-Next con cache de expertos + MTP — 2026-09-14

## Resultado

El nuevo reporte propone combinar tres cambios:

1. Qwen3.8 Flash-Next UD-Q4_K_XL en lugar de Q6.
2. Cache LRU de expertos en VRAM.
3. Cabezal MTP compartido en la segunda RTX 3090.

El autor informa 37–41 tok/s en prompts de código cortos, hasta 49 tok/s sin
thinking, y 18–20 tok/s a 131K. También describe una corrección importante en
la ruta del cache: limitar la operación batched a ocho tokens para evitar que
varios tokens compartan un slot dummy y provoquen escrituras fuera de rango.

La idea es técnicamente relevante, pero **no es todavía superior ni segura en
LlamaCode**. La variante local con cache + MTP ya fue probada y no pasó el
smoke funcional. SOL permanece como default.

## Qué ya tenemos

La build experimental local de Flash-Next contiene las piezas principales de
la rama publicada:

- cache LRU de expertos de la PR #27861;
- buffers de host fijados y arreglo de carga de la PR #28223;
- cabezal MTP de la PR #28243;
- reparto `--numa distribute` y expertos `CUDA_Host`;
- cache Q8 del cabezal MTP ya descargado localmente.

Por eso no se descargó otro modelo ni se duplicó el artefacto existente.

## Comparación local

| Configuración | Resultado local | Decisión |
| --- | --- | --- |
| Flash-Next sin cache | ~16,45 tok/s a 16K | Control |
| Cache 188 sin MTP | ~36,04–36,9 tok/s | TPS alto, salida repetitiva/no válida en el smoke experimental |
| Cache 150 + MTP | No estable; acceso ilegal CUDA/corrupción en generación | No activar |
| MTP sin cache | Arranca, pero queda por debajo de cache188 | No reemplaza ASTRA |
| N-gram con cache 188 | ~36,97 tok/s | Inferior al cache sin speculative |
| SOL | 74 tok/s narrativo / 102 tok/s código | BCB 8/8, tool-use OK; default |

El reporte externo usa KV F16/BF16. Eso no puede trasladarse a un perfil
promovible porque LlamaCode limita pesos y KV a Q8 como máximo. Además, sus
37–49 tok/s son mediciones de decode de un único prompt; no incluyen BCB,
HE0/HE20, tool-use, errores de generación ni estabilidad en sesiones largas.

## Cambios útiles para una futura reparación

Sí conviene conservar estas ideas como trabajo de ingeniería:

- corregir la asignación de IDs del cache para batches mayores que un token;
- conservar el límite seguro de ocho tokens por operación `mul_mat_id`;
- reservar aproximadamente 150 slots cuando el cabezal MTP ocupa VRAM;
- medir la aceptación MTP por separado para thinking y emisión de código;
- comprobar la memoria libre durante un prefill de 131K, no sólo al arrancar;
- ejecutar BCB y un tool-call después de cada transición cache/MTP.

La rama también indica que más de dos subidas de cache por paso saturan el
enlace y que el cache Q8 reduce el rendimiento en contexto largo. Ambas
observaciones coinciden con nuestras pruebas anteriores y no justifican
modificar SOL.

## Decisión de perfiles

- **SOL:** permanece como principal y predeterminado.
- **ASTRA:** conserva cache de expertos como perfil experimental, sin MTP.
- **ASTRA-MTP:** no se agrega al dropdown hasta que la generación sea estable
  con KV Q8 y pase HE0, BCB y tool-use.
- No se usa KV F16/BF16, `load-mode none`, más de dos uploads por paso ni
  speculative encadenado.

La auditoría anterior del cache LRU queda complementada por este documento:
`docs/qwen38-flash-next-expert-cache-pr27861-audit-20260914.md`.
