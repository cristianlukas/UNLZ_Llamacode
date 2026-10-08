# Auditoría del head MTP oficial para Qwen3.8-Flash-Next

Fecha: 2026-09-14  
Estado: disponible localmente, no promovido

## Qué aporta la novedad

Un head MTP compartido permite que Flash-Next proponga tokens y que el modelo
principal los verifique. La verificación es exacta: el head debería cambiar la
velocidad, no el contenido de salida. La guía de Unsloth recomienda
`mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf`, con `--spec-type draft-mtp` y
`--spec-draft-n-max 2`. El fabricante declara aproximadamente 1,3–1,7x en
baja concurrencia, pero advierte que puede perder rendimiento con muchas
solicitudes simultáneas.

Fuentes:

- [Guía MTP oficial del artefacto GGUF](https://huggingface.co/unsloth/Qwen3.8-Flash-Next-GGUF/blob/main/MTP/README.md)
- [PR de soporte MTP en llama.cpp](https://github.com/ggml-org/llama.cpp/pull/28243)
- [PR de Unsloth](https://github.com/unslothai/llama.cpp/pull/144)
- [Problema de prefill con MTP y reparto multi-GPU](https://github.com/ggml-org/llama.cpp/issues/27428)

## Estado local

El head ya estaba descargado en:

```text
/media/cristian/Disco local/Models/llamacpp/Qwen3.8-Flash-Next-UD-Q4_K_XL/MTP/mtp-Qwen3.8-Flash-Next-shared-Q8_0.gguf
```

El binario experimental CUDA local reconoce `--spec-type draft-mtp`,
`--spec-draft-model` y `--spec-draft-n-max`. No fue necesario descargar ni
duplicar modelos.

## Cruce con pruebas previas de LlamaCode

| Configuración | Resultado | Lectura |
| --- | --- | --- |
| Flash-Next sin MTP, cache de expertos | ~16–41 tok/s según variante/contexto; hubo salidas corruptas en el engine experimental | No apto para default |
| Flash-Next con cache + MTP/NGRAM | No estable; corrupción o acceso ilegal CUDA | No activar |
| Flash-Next Q4 con MTP separado | La combinación ASTRA Q4 validada previamente no pasó la estabilidad del smoke | No activar en Q4 |
| Flash-Next IQ1_S + head compartido Q8 | Carga, tool-call 1/1, BCB parcial 1/1, 94–100% de aceptación en las pruebas locales | Opt-in experimental |
| SOL, Qwen3.8-27B AutoRound INT4 + MTP4 | 74 tok/s narrativo / 102 tok/s código; BCB 8/8; tool-use OK | Default actual |

Además, una prueba controlada previa de Qwen3.8 base estableció que MTP4 era el
mejor punto local para ese modelo. Eso no se puede trasladar automáticamente a
Flash-Next: son arquitecturas y rutas de memoria distintas.

## Repetición con P2P y ASTRA actual — 2026-09-14

Se repitió la prueba con el `UD-Q4_K_XL` de ASTRA, dos RTX 3090, P2P del
driver habilitado, `--split-mode layer`, cache de expertos 188, KV Q8/Q8,
`parallel=1`, batch 256/ubatch 128 y el head compartido Q8. El control sin MTP
usó exactamente la misma receta y el mismo prompt.

| Variante | Resultado textual | Decode | Aceptación |
|---|---|---:|---:|
| Control sin MTP | `/` repetido durante 128 tokens | **44,02 tok/s** | No aplica |
| MTP, smoke corto | Python válido | 4,77 tok/s | **6/10 = 60%** |
| MTP, prompt largo de control | `/` repetido durante 128 tokens | **5,74 tok/s** | **0/251 = 0%** |

El smoke corto no es reproducible: MTP llegó a cargar y producir una función
Python correcta, pero la generación de control más larga volvió a mostrar la
corrupción característica de ASTRA, con aceptación nula y un coste de decode
aproximadamente 7,7 veces mayor que el control bruto.

También se probó MTP junto con el `mmproj-BF16.gguf` oficial, límites visuales
1024–2240 tokens y la misma receta P2P. El servidor cargó como multimodal y
procesó la imagen, pero devolvió `/` repetido durante 64 tokens, con **0/123
tokens aceptados**. Durante el prefill aparecieron advertencias de posiciones
no consecutivas, por lo que esa ruta no se considera estable.

| Variante visual | Resultado | Decode | Aceptación |
|---|---|---:|---:|
| ASTRA + MTP + `mmproj` GPU | `/` repetido; carga multimodal OK | 4,77 tok/s | **0/123 = 0%** |

La visión con MTP tampoco es promovible: el proyector correcto carga, pero la
salida no contiene una descripción visual válida.

El mensaje interno `borrow_shared_tensor` que aparece durante la medición del
modelo extra se recupera correctamente: el head se carga como draft del modelo
principal y el servidor llega a `/health`. No es la causa del fallo de calidad.

### DFlash2 y variantes similares

No hay un drafter DFlash2 compatible con **Flash-Next** en los artefactos
locales. Los drafts DFlash2 disponibles pertenecen a Qwen3.8-27B base u otras
variantes, y no se pueden emparejar con el `UD-Q4_K_XL` de Flash-Next sin
mezclar arquitecturas y falsificar la comparación. Las pruebas previas de
DFlash2 sobre Qwen3.8 base ya fallaron con incompatibilidad de tensores o
`CUDA device-side assert`; la variante estable requería KV BF16, fuera del
límite Q8 del proyecto.

## Riesgos relevantes

1. **Calidad primero.** La especulación sólo es segura si el modelo principal
   verifica exactamente los tokens y el grafo de Flash-Next no pierde celdas de
   predecesores. Nuestras pruebas anteriores observaron pérdida de caracteres,
   repetición de `/` y salidas no válidas en la rama experimental.
2. **Prefill multi-GPU.** La incidencia upstream documenta que `draft-mtp` puede
   aproximadamente partir por la mitad el prompt processing cuando el modelo se
   divide por capas entre dos GPU. En un agente, un decode algo más rápido no
   compensa necesariamente un prefill largo mucho más lento.
3. **Concurrencia.** El resultado externo de MTP está medido principalmente con
   una sola secuencia. No sirve para afirmar una mejora en el servidor de
   LlamaCode con varios turnos o agentes.
4. **Política de cuantización.** El head Q8 respeta el máximo Q8 de la
   aplicación. No se debe sustituir por KV o pesos BF16 para ocultar fallos de
   estabilidad.

## Decisión

- No se agrega `ASTRA-MTP` al grupo prioritario.
- No se reemplaza SOL.
- ASTRA mantiene su estado experimental y sin MTP por defecto.
- Se conserva el head local para una futura campaña específica con:
  `draft-mtp`, `n-max=2`, KV Q8, `parallel=1`, pruebas de prefill a 8K/32K/80K,
  varias generaciones deterministas, BCB y tool-use.

La mejora aprovechable ahora es de infraestructura: LlamaCode ya tiene soporte
para registrar el binario, el head separado y los flags MTP. Lo que falta para
promoverlo no es descargar otro archivo, sino demostrar salida correcta y una
ganancia neta de tiempo en nuestro escenario de dos RTX 3090.
