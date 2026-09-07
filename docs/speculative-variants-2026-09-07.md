# Variantes especulativas ASTRA/SOL/TERRA/LUNA/METEOR — 2026-09-07

Se probaron en Ubuntu las técnicas disponibles en el runtime CUDA actual:
MTP, DFlash2 y NGRAM. Las pruebas se realizaron con copias temporales y no
alteraron Windows ni los perfiles permanentes, salvo que LUNA ya conservaba
la promoción CUDA 64K validada anteriormente.

## Inventario de compatibilidad

- **ASTRA / Qwen Next:** existe el head MTP local de 2,79 GB; no hay un head
  DFlash2 o DSpark compatible con Flash-Next. También se probó NGRAM integrado.
- **SOL y TERRA / Qwen3.8-27B:** MTP separado ya funciona; DFlash2 Q4 local
  existe y NGRAM integrado está disponible.
- **LUNA / ThinkingCap Qwen3.6:** MTP4 ya funciona; NGRAM se puede encadenar,
  pero no hubo mejora. DFlash2 no es un draft validado para esta variante.
- **METEOR / BigBang:** el modelo puede usar su MTP embebido; NGRAM se pudo
  iniciar. No hay DFlash2 ni DSpark compatible validado.
- **DSpark:** el runtime acepta el tipo, pero no hay un draft DSpark compatible
  con estas cinco familias; no se forzó una combinación arquitectónicamente
  incorrecta.

## Resultados de velocidad

`decode P50` es la métrica principal del benchmark `LlamaCode Server Speed v1`.

| Perfil / variante | Contexto | Decode P50 | Estado de carga |
|---|---:|---:|---|
| ASTRA + MTP | 131K | — | No inicia |
| ASTRA + NGRAM | 131K | — | No llegó a servidor listo tras 292 s; cancelado |
| SOL + MTP + NGRAM | 131K | 66,17 tok/s | Estable |
| TERRA + MTP + NGRAM | 131K | 66,63 tok/s | Estable |
| SOL + DFlash2 n4 | 32K | — | No inicia |
| LUNA + MTP4 + NGRAM | 64K | 55,29 tok/s | Estable |
| METEOR + MTP + NGRAM | 64K | 50,09 tok/s | Estable |

Comparaciones directas de las variantes probadas:

- SOL+NGRAM: aproximadamente `+3,5%` frente al SOL CUDA de referencia.
- TERRA+NGRAM: aproximadamente `+4,4%` frente al TERRA CUDA de referencia.
- LUNA+NGRAM: aproximadamente `−2,3%` frente a LUNA CUDA 64K.
- METEOR+NGRAM: aproximadamente `+51%` frente a METEOR CUDA sin NGRAM,
  pero esa mejora no se trasladó al tiempo total del agente.

## Calidad y estabilidad

| Variante | HE0 | HE20 | BCB | Decisión |
|---|---:|---:|---:|---|
| SOL + NGRAM | 1/1 | 20/20 | Inconcluso; quedó reparando y se canceló | No promover |
| TERRA + NGRAM | 1/1 | 20/20 | No iniciado tras cancelar SOL | No promover todavía |
| METEOR + NGRAM | 1/1 | 13/20 al cancelar | No iniciado | No promover |
| LUNA + NGRAM | No ejecutado | No ejecutado | No ejecutado | Descartar: más lento |
| ASTRA + MTP | No carga | Bloqueado | Bloqueado | Descartar |
| ASTRA + NGRAM | No carga en tiempo práctico | Bloqueado | Bloqueado | Descartar |
| SOL + DFlash2 n4 | No carga | Bloqueado | Bloqueado | Descartar |

SOL y TERRA+NGRAM pasaron HE20 sin errores de infraestructura, pero SOL no
cerró la reparación de BCB y TERRA no alcanzó BCB dentro de la misma campaña.
El incremento de decode aislado no alcanza para cambiar un perfil que ya tiene
BCB 8/8 limpio. METEOR+NGRAM fue claramente demasiado lento en HE20 pese a su
mejor TPS sintético.

## Decisión aplicada

No se promovió MTP, DFlash2 ni NGRAM a ASTRA, SOL, TERRA, LUNA o METEOR.
Se conservaron los cinco perfiles y la promoción previa de LUNA CUDA 64K.
Las copias temporales fueron eliminadas del catálogo; TERRA quedó activo y
Windows no fue modificado.

Los artefactos de la campaña están en:

- `/home/cristian/.local/share/LlamaCode/LlamaCode/benchmark-runs/server_speed_20260907_163034`
- `/home/cristian/.local/share/LlamaCode/LlamaCode/benchmark-runs/server_speed_20260907_163630`
- `/home/cristian/.local/share/LlamaCode/LlamaCode/benchmark-runs/server_speed_20260907_165938`
