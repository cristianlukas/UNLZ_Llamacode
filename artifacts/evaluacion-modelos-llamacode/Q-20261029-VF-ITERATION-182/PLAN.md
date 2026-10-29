# Q182 — Ruta Linux para DeepSeek-V4.1-Flash-1017

**Tipo:** revisión de gates y sincronización de cola; no es un benchmark.
**Estado:** bloqueada antes de descargar o ejecutar el candidato nuevo.

## Pregunta

¿Existe una ruta Linux con valor para evaluar DeepSeek-1017 en las dos RTX 3090 sin confundirla con los resultados locales previos ni atribuirle los 41 tok/s del post?

## Identidades que deben permanecer separadas

- El post de Reddit atribuye 41 tok/s y 91,5% top-1 al `nazeshinjite ds4 Q2` de unos 366 GB servido por Delta en una sola RTX 3090. Es una medición del autor, no una medición local.
- Q172 local evaluó `lxe/dsx` T16 en dos RTX 3090: 89/100 frente a 73/100 de ASTRA en una semilla, pero ambos filtraron datos entre tenants en TC-92. Esa corrida no midió los 41 tok/s y no usó el archivo del post.
- La prueba anterior Xolotl/Q172 usó el quant XQ de IndrasMirror; cargó en ambas GPUs, pero la primera generación falló con SIGSEGV. No es un resultado de calidad.
- Xolotl ahora documenta soporte Linux para los shards ISTA-DASLab GSQ-RCO IQ2_XS. Es otro paquete/quant/runtime; sus cifras publicadas en una RTX 4090 no validan el post ni anticipan el rendimiento en estas 3090.

## Gates medidos

- Espacio libre actual: NVMe D `145,357,176,832 B`; NVMe del checkout `121,917,898,752 B`; total NVMe `267,275,075,584 B` (267,3 GB decimales). HDD extra tiene `30,834,577,408 B`, pero no cuenta como NVMe para esta ruta.
- La receta oficial para IQ2_XS enumera aproximadamente 155 GB de modelo, 111 GB de Engram y 8 GB de drafter: 274 GB antes de espacio de build y margen. Se fija un umbral operativo de **300 GB libres en NVMe** para poder preparar y ejecutar sin agotar los volúmenes.
- Q172 local ya documentó un fallo de generación en el layer split Xolotl con 2×RTX 3090. El issue público de Xolotl también registra respuestas incorrectas tras parches en 2×RTX 5060 Ti y un segfault de primer prompt en 4×RTX 3090; no se encontró evidencia pública de una corrección posterior al reporte.
- El servidor Qwen3.5-9B indicado por el usuario fue detenido. El preflight actual no encontró servidores de inferencia ni procesos CUDA de cómputo. Q179 ya completó Q172 dual para Flash-Next; no se repite.

## Diseño preregistrado si se reabre

1. Fijar commit del runtime, revisión y SHA-256 de los cuatro shards, Engram, drafter y config. Mantener separado el `nazeshinjite ds4 Q2` de la variante ISTA IQ2_XS.
2. Exigir al menos 300 GB libres en NVMe y comprobar que no haya otro inference server antes de preparar los recursos.
3. Con ambas RTX 3090, pasar primero un smoke de 3 respuestas deterministas con oracles exactos, confirmar capas/VRAM en ambas GPUs, estado del proceso y limpieza. Cualquier respuesta incorrecta, salida vacía, crash o fuga de datos cancela Tool-Eval.
4. Sólo después del smoke, preregistrar Q172 pareado contra el perfil ASTRA actual, misma plantilla/sampling/contexto y tres semillas seriales; la seguridad es un gate absoluto. La ladder de velocidad se hace sólo si calidad y seguridad pasan.

**Resultado de preregistro:** ningún paso de descarga, build, inferencia o GPU se habilitó en Q182 porque fallan los gates de espacio y corrección dual.
