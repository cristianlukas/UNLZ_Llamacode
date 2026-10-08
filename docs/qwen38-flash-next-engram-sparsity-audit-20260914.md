# Qwen3.8 Flash-Next Engram/PLE — auditoría de optimizaciones por frecuencia

Fecha: 2026-09-14  
Equipo LlamaCode: Ubuntu, 2× RTX 3090, P2P disponible y ~123 GiB de RAM

## Qué aporta el análisis

El estudio describe la tabla Engram/PLE de Flash-Next como una tabla de
embeddings hashados de bigramas y trigramas. En su conjunto ocupa alrededor de
51B parámetros, pero los accesos siguen una distribución muy sesgada: una
minoría de filas recibe la mayor parte de las consultas. El autor propone
pruning por frecuencia (`keep75`, `keep50`, `keep25`) y reordenamiento físico de
las filas para mejorar el acceso en SSD.

Es una hipótesis interesante de optimización del artefacto, pero el propio
análisis todavía no mide perplexity ni calidad del modelo completo. Una fila
rara puede contener una señal importante precisamente porque tiene menos
colisiones; eliminarla por frecuencia podría degradar coding, idiomas o dominios
que no aparecen en la calibración.

## Cruce con LlamaCode

| Propuesta | Situación local | Decisión |
|---|---|---|
| Poda `keep50`/`keep25` | No existe un GGUF reempaquetado compatible ni una validación de pérdida global | No implementar |
| Máscaras por dominio | La calibración del post es principalmente inglés/código; puede dañar otras tareas | No implementar |
| Factorización low-rank | El estudio informa rango efectivo casi completo; no ofrece ahorro seguro | Descartar |
| Quitar cabezas Engram | Cada cabeza parece aportar señal similar; no hay cabezas débiles | Descartar |
| Ordenar filas por frecuencia | Podría mejorar lecturas secuenciales del SSD, pero requiere cambiar el layout y el loader | Trabajo futuro |
| `mmap` y page cache del sistema | Ya está incorporado en ASTRA y fue probado localmente | Mantener |
| Cache de expertos 188 | Es una caché runtime de expertos, no poda filas Engram; ya es nuestra optimización segura actual | Mantener |

## Comparación con las pruebas previas

Las pruebas de LlamaCode ya cubren el cuello de botella operativo relacionado:

- `mmap`/lazy loading: `lazy on` produjo salida `////` corrupta.
- Lectura directa (`on-direct`): salida válida, pero ~7,54 tok/s.
- ASTRA con cache de expertos 188: carga, pero la calidad agéntica no quedó
  validada.
- BeeLlama KVarN5/KVarN5: ~36 tok/s a 131K con JSON, Python, tool-call y needle
  válidos.
- SOL: 74 tok/s narrativo / 102 código, BCB 8/8 y tool-use OK.

El estudio externo no aporta BCB, HE0/HE20 ni tool-use comparable. Tampoco
demuestra que una máscara que conserva el 50% de las filas mantenga la calidad
en el modelo completo.

## Decisión

No se descarga ni se modifica ningún modelo. No se agrega un perfil nuevo y no
se cambia SOL, ASTRA ni BeeLlama. La mejora segura que se conserva es seguir
usando `mmap` y la caché runtime existente. Para considerar una futura variante
Engram reducida habría que obtener un artefacto compatible, medir perplexity en
inglés, español, código y tool-use, ejecutar BCB/HE0 y comprobar contexto largo
antes de permitirla en LlamaCode.

