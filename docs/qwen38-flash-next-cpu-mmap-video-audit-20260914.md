# Auditoría del video: Qwen3.8-Flash-Next sólo con CPU

Fecha: 2026-09-14  
Estado: referencia de capacidad, sin promoción

## Qué muestra el video

El video afirma aproximadamente 8,7 tok/s ejecutando Flash-Next sólo con CPU,
un GGUF de unos 111 GB y aproximadamente 58 GB de RAM residente. La explicación
propuesta es `mmap`: el sistema operativo no mantiene todos los bytes del GGUF
en RAM física, sino que carga páginas cuando se consultan desde el SSD.

La idea es técnicamente plausible para este modelo. Flash-Next combina un
backbone MoE con una tabla N-gram grande y el modelo card describe 125B de
parámetros de lenguaje, 51B de embeddings N-gram y un head MTP adicional. [Modelo
GGUF y arquitectura](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/blob/main/README.md)

## Comparación contra LlamaCode

| Variante | Resultado | Calidad/validación | Decisión |
|---|---:|---|---|
| Video: CPU-only + `mmap` | ~8,7 tok/s reportados | Sin BCB, HE0/HE20 ni tool-use comparable | No supera perfiles actuales |
| Flash-Next local con offload CPU | ~9–10 tok/s en campañas antiguas | No supera SOL; rutas experimentales | Diagnóstico, no default |
| ASTRA Flash-Next | ~16–41 tok/s según contexto/receta | Calidad agéntica no validada; hubo corrupción en rutas lazy/cache | Experimental |
| BeeLlama Flash-Next KVarN5 | ~36 tok/s a 131K; ~27,33 tok/s en ~77,8K | JSON, Python y tool-call válidos; texto-only | Mejor alternativa Flash-Next local |
| SOL | 74 tok/s narrativo / 102 tok/s código | BCB 8/8 y tool-use OK | Default |

## Qué significa realmente la cifra de RAM

Que el proceso muestre 58 GB residentes no significa que el modelo necesite
solamente 58 GB ni que todo el resto sea gratis. Los otros bytes permanecen
respaldados por el archivo y pueden provocar page faults, presión de caché e
I/O variable. La cifra de 8,7 tok/s puede depender de:

- velocidad y latencia del NVMe;
- tamaño del contexto y del batch;
- páginas N-gram que ya quedaron calientes en la caché del sistema;
- cantidad de threads y afinidad NUMA;
- longitud y contenido del prompt;
- cuantización y build exactas de llama.cpp.

Por eso no es comparable directamente con SOL, que usa dos RTX 3090, otro
backend y un perfil INT4/MTP validado.

## Pruebas locales que ya cubren la hipótesis

No se volvió a cargar durante horas el modelo sólo con CPU porque el resultado
ya está acotado por debajo de SOL y no cambiaría una decisión de perfil. Las
pruebas previas de LlamaCode ya validaron las partes relevantes:

1. `mmap` reduce la RAM residente, pero no corrigió la corrupción de Flash-Next.
2. `lazy on` llegó a producir TPS bruto alto, pero salida `////` no utilizable.
3. `lazy on-direct` produjo salida válida alrededor de 7,54 tok/s, inferior a
   la cifra del video y demasiado lento para reemplazar ASTRA o SOL.
4. El offload de expertos a CPU resuelve capacidad, no mejora la calidad ni el
   throughput frente a SOL.

## Decisión

- No se descarga ningún modelo.
- No se agrega un perfil CPU-only.
- No se cambia el default ni el orden prioritario.
- `mmap` continúa siendo una opción de memoria para perfiles experimentales,
  nunca una prueba suficiente de calidad.

El video queda registrado como evidencia de fallback para máquinas sin GPU,
pero no como mejora para nuestro equipo. SOL continúa siendo claramente
superior para LlamaCode por velocidad, calidad, BCB y tool-use.
