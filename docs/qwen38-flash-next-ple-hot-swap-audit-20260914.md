# Auditoría: memoria PLE hot-swappable para ASTRA — 2026-09-14

## Resultado ejecutivo

El proyecto `llama.cpp-NLTM` propone aplicar overlays pequeños sobre la tabla
PLE/N-gram de Qwen3.8-Flash-Next sin reescribir el GGUF ni reiniciar el
servidor. Es una idea interesante para memoria experimental de ASTRA, pero no
es un reemplazo de los perfiles actuales ni puede activarse con nuestro
artefacto Q4.

**Decisión:** no cambiar el default, no modificar SOL y no añadir la función al
dropdown. La implementación queda como investigación futura, aislada del
runtime principal.

## Qué hace la propuesta

El fork aplica un archivo `.plepatch` como overlay copy-on-write sobre la tabla
`per_layer_token_embd.weight`. El servidor vuelve a comprobar el archivo antes
de cada `decode()`, por lo que puede sustituirse o eliminarse sin recargar el
modelo. El inyector calcula las filas direccionadas por hash para un n-grama y
permite operaciones como `blend`, `set`, `add`, `zero` y `copy_from`.

La documentación del proyecto indica que el mecanismo es POSIX/mmap-only,
que los overlays están acotados a la tabla PLE y que las filas pueden colisionar
entre distintos n-gramas. Por lo tanto, no equivale a una memoria semántica
general ni a RAG: afecta sólo a disparadores concretos y puede producir efectos
laterales sobre filas compartidas.

## Pruebas ejecutadas

Se clonaron temporalmente los dos repositorios y se ejecutó la suite propia del
inyector en un entorno Python aislado:

| Prueba | Resultado |
| --- | --- |
| Suite sintética del inyector | **8/8 OK** |
| Hash Python frente a vectores C++ | OK en 18 ventanas |
| Reset EOS y tokenización | OK |
| Round-trip Q8_0 | Bit-exacto |
| Filas no modificadas | Bit-exacto |
| Overlay COW sintético | OK |
| Overlay sobre nuestro ASTRA Q4 | **No compatible** |

El intento con el primer shard local de
`Qwen3.8-Flash-Next-UD-Q4_K_XL` detectó:

```text
table=per_layer_token_embd.weight
qtype=IQ4_NL
ValueError: gguf-py cannot quantize to IQ4_NL
```

El modelo local contiene una tabla PLE `IQ4_NL`, mientras que el inyector
declara haber probado sólo `Q8_0` y algunos tipos básicos. Por eso no se creó
ningún `.plepatch`, no se alteró el GGUF y no se tocó el servidor.

## Comparación con el estado de LlamaCode

| Opción | Estado local | Uso recomendado |
| --- | --- | --- |
| SOL | BCB 8/8, tool-use válido, 74/102 tok/s | Default para coding y agentes |
| ASTRA Q4 + cache de expertos | Experimental; TPS alto pero calidad no validada | Contexto largo experimental |
| PLE hot-swap sobre ASTRA Q4 | Incompatible por `IQ4_NL` | No activar |
| PLE hot-swap sobre Q8 | Teóricamente posible según el proyecto | Sólo laboratorio, con runtime separado |

## Riesgos antes de una integración

- Un overlay puede cambiar el comportamiento de un modelo compartido entre
  sesiones; habría que aislarlo por proceso o por perfil.
- Las colisiones de hash hacen que una edición dirigida a un disparador pueda
  afectar otros n-gramas.
- La inyección no ofrece garantías de obediencia, factualidad ni persistencia
  conversacional general.
- El runtime externo usa `MAP_FIXED` y depende de mmap; no es compatible con
  `--no-mmap`/`load-mode none`.
- La modificación requiere un fork de `llama.cpp`; no debe reemplazar el
  binario estable de LlamaCode sin pruebas de regresión de salida, tool-calls,
  contexto largo y aislamiento de sesiones.

## Siguiente paso posible

Si se quiere continuar, la ruta segura sería crear un backend experimental
separado para ASTRA, exigir un formato de overlay con manifiesto y hash del
modelo, y validar primero una sola entrada sintética con `IQ4_NL` soportado de
forma nativa. Después habría que comprobar HE0, BCB, tool-use, colisiones y
que borrar el overlay restaure exactamente el comportamiento original.

No se descargó un modelo Q8: no está disponible localmente, ocuparía mucho
espacio y no resolvería la incompatibilidad actual del artefacto Q4 que usa
ASTRA.
