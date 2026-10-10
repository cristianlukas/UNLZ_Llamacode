# Evaluación del post de r/Qwen_AI: Flash-Next IQ3_XXS en RTX 4060 Laptop

Fecha: 2026-10-10. Tarea: `Q-20261009-FLASHNEXT-IQ3XXS-AB`.

## Conclusión

El post sirve como indicio de que Strata puede hacer viable una cuantización
grande en una laptop de 8 GB al repartir trabajo entre RAM, CPU y GPU. No
demuestra por sí solo 131K tokens efectivos, calidad de coding, ni una mejora
para los perfiles o el harness de LlamaCode. La campaña local no justifica
promover ISTA IQ3_XXS: perdió frente al control ASTRA IQ3_S calibrado en BCB8 y
TaskFlow ULTRA; ADV v1 empató después de reparaciones, con primera pasada más
baja y más tiempo y llamadas. **No se cambiaron perfiles productivos, sampling
ni HarnessSpec.**

## Qué afirma la publicación

El autor informa un Ryzen 7 7840HS, 64 GB DDR5, RTX 4060 Laptop con 8 GB,
NVMe y Windows. Con IQ3_XXS y visión en CPU, configuró el contexto en 131.072
y reportó aproximadamente 180 tok/s de prefill y 27–32 tok/s de decode. Para
IQ2_XS reportó aproximadamente 430 tok/s y 29–35 tok/s. Un comentario menciona
250 tok/s/24 tok/s en otra laptop; otro usuario con 2× RTX 3090 Ti y 32 GB de
RAM dice preferir Qwen3.6-35B-A3B o Qwen3.8-27B para coding/análisis.

Son observaciones de usuarios sin prompt, longitud efectiva, caché, protocolo
ni recibos comparables. La documentación de Strata confirma opciones de
contexto y visión por CPU; su tabla estima IQ3_XXS en torno a 47 GB de RAM+VRAM.
El model card de Qwen declara 262.144 tokens nativos. Esos datos documentan
posibilidad/configuración, no validan el rendimiento o la calidad de la laptop.

Fuentes: [post de r/Qwen_AI](https://www.reddit.com/r/Qwen_AI/comments/1x097l9/strata_is_the_best_magic_qwen38_fn_iq3_xxs_on_a/),
[configuración de Strata](https://github.com/Niko1221/Strata/blob/main/docs/AI_SETUP.md),
[tabla de modelos de Strata](https://github.com/Niko1221/Strata/blob/main/docs/MODELS.md),
[model card de Qwen3.8-Flash-Next](https://huggingface.co/Qwen/Qwen3.8-Flash-Next).

## Evidencia local relevante

La comparación fue ISTA-DASLab GSQ-RCO IQ3_XXS contra ASTRA IQ3_S calibrado,
ambos sobre Strata v0.1.41 en dos RTX 3090 de 24 GB y RAM física de 123,6 GiB.
Es una comparación de perfiles completos en otro hardware; no replica la
laptop ni permite extrapolar sus tok/s.

| Suite/medición | ISTA IQ3_XXS | ASTRA IQ3_S | Lectura |
|---|---:|---:|---|
| HE0 (prerrequisito) | 1/1 | 1/1 | Ambos pasaron. |
| HE20 | 20/20 | 20/20 | Empate. |
| BCB8 | 4/8 final; 3 reparaciones | 8/8 final; 2 reparaciones | ASTRA mejor. |
| ADV v1 | 7/10 → 10/10; 2 reparaciones; 977,519 s; 105 llamadas | 8/10 → 10/10; 2 reparaciones; 773,404 s; 63 llamadas | Empate final tras reparación; IQ3_XXS tuvo menor primera pasada y necesitó más tiempo/llamadas. Una pareja de screening, no una mejora estable. |
| TaskFlow ULTRA | 11/13; 3 reparaciones | 13/13; 2 reparaciones | ASTRA mejor. En IQ3_XXS fallaron `py_compile` y el unittest generado por un `SyntaxError` en el test del agente; clasificado como calidad, no infraestructura. |
| Server Speed v1, decode | 126,59 tok/s, rango 119,78–133,40; n=2 | 122,09 tok/s, rango 120,32–123,86; n=2 | Rangos solapados; no hay ganador demostrado. |
| Server Speed v1, TTFT | 370,63 ms media | 451,00 ms media | IQ3_XXS fue menor en ambas pasadas, señal de latencia que requiere repetición. |

Las tres suites de calidad usaron `agent-maximo`, thinking activado y la misma
semilla 4242. LC-H1 sumando HE20, BCB8 y ADV v1 terminó 34/38 para IQ3_XXS y
38/38 para ASTRA; HE0 se informa aparte. TaskFlow aporta otros 11/13 frente a
13/13. Se requieren más pares para afirmar cualquier diferencia estable.

### Contexto

La configuración local declaraba `max-context=131072`, pero el mayor prompt
válido de Server Speed fue de 38.804 tokens. Se generó además una sonda
determinista de retrieval con 115.003 tokens de texto (115.015 reportados por
el servidor incluyendo el wrapper), diez hechos en posiciones aproximadas
5–95% y preguntas exactas al final. La petición de IQ3_XXS llegó al prefill
del token 65.536/115.015; el proceso/endpoint terminó y el cliente recibió
`RemoteDisconnected`, sin respuesta, `usage` ni `finish_reason`. Duró 22,725 s.
Por tanto, no hay score de retrieval; el `0/10` vacío del recibo no es un
resultado de calidad. No se estableció la causa del cierre y no se probó ASTRA.
El contexto largo para IQ3_XXS sigue **no evaluado**.

## Lectura por uso de LlamaCode

- **Coding y agentes:** el candidato no supera a ASTRA en BCB8/TaskFlow y no
  mejora ADV de manera concluyente. SOL sigue como perfil principal de coding y
  agentes según la matriz vigente. IQ3_XXS no se promueve.
- **Computer Usage:** esta campaña no interactuó con un escritorio real. La
  auditoría previa de 216 prompts es textual, sin capturas ni validación E2E;
  no aporta evidencia GUI para esta cuantización ISTA.
- **Ingi-Charla:** no se probaron audio, ASR/STT ni TTS. Mantener Qwen3.5-9B y
  el pipeline de voz existente; texto de Flash-Next no mide calidad acústica.
- **Visión:** el post usa visión en CPU, una ruta que Strata documenta. El
  perfil de esta campaña tenía imágenes desactivadas; no se midieron entradas
  visuales. Mantener las recetas visuales ya validadas.
- **Contexto:** contexto configurado no significa contexto consumido. El
  intento 115K falló por transporte a mitad del prefill, por lo que no afirma
  capacidad efectiva ni recuperación. Reintentar después de aislar el cierre
  y ejecutar el control ASTRA en serie.
- **Rendimiento:** las cifras del post no tienen longitud/protocolo y son de
  hardware distinto. La comparación local dual-3090 muestra TTFT menor para
  IQ3_XXS, pero decode con rangos solapados y sólo dos pasadas; no se extrapola
  a la RTX 4060 Laptop.

## Alcance, artefactos y estado

No se editaron C++, QML, harness, perfiles productivos ni `profiles/launches.json`.
No correspondían builds ni pruebas del producto. La corrida ADV de ASTRA ya
estaba activa antes de encontrar el plan de preregistro; quedó marcada como
desviación. El par ADV se presenta sólo como screening.

El plan, el texto de fuente recibido, fixture, respuesta fallida, recibos de
calidad/velocidad, configuraciones y suites están en
[`artifacts/evaluacion-modelos-llamacode/Q-20261009-FLASHNEXT-IQ3XXS-AB/`](../artifacts/evaluacion-modelos-llamacode/Q-20261009-FLASHNEXT-IQ3XXS-AB/).
El manifiesto de hashes de esta evidencia está junto a esos recibos.
