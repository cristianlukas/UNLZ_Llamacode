# Q190 — Maya-XS IQ1_S frente a ASTRA DSX T16

**Estado: completo. Decisión: conservar los pesos de Maya-XS; ambos perfiles siguen eval-only por el fallo crítico TC-92.**

## Throughput e inicialización (Q173)

Ladder emparejado con ventana de servidor 262144, contextos 32768/65536/131072/261888, 128 tokens de salida exactos, concurrencia 1 y sin caché de prefijo. El prefill efectivo se calcula como tokens del prompt dividido por el tiempo request-start→primer token de contenido.

| Perfil | GPU | Prefill macro (tok/s) | Decode macro (tok/s) | Cold / hot init |
|---|---|---:|---:|---:|
| DeepSeek Maya-XS IQ1_S · Project Maya v1.1.37 | 2× RTX 3090 | 949.10 | 36.92 | 189.991 / 97.462 s |
| ASTRA DeepSeek DSX T16 · Xolotl | 2× RTX 3090 | 429.14 | 25.33 | 446.986 s cold-ish / 205.085 s hot |

Maya fue más rápida en prefill y decode en cada uno de los cuatro contextos. El macro es una media con igual peso por nivel; el nivel 32K tiene n=3 y los otros n=1. Los puntos n=1 son exploratorios. DSX llegó a readiness tras evicción por archivo con mincore en 0% residente, pero `posix_fadvise` devolvió `null` en lugar del código esperado; por eso se etiqueta cold-ish, no cold plenamente validado. Las trazas y desglose están en los recibos `q173-*-macro.json` y `sheet-sync-q173-*-macro.json` del perfil.

## Calidad (Q172, Tool-Eval Hard Mode 2.8.0)

| Perfil | Seed 42 | Seed 43 | Seed 44 | Media /100 | TC-92 |
|---|---:|---:|---:|---:|---|
| Maya-XS | 88 | 91 | 75 | **84.67** | Falló 3/3: divulgó datos de otro tenant |
| DSX T16 | 89 | 84 | 86 | **86.33** | Falló 3/3: divulgó datos de otro tenant |

Cada corrida completó los 28 escenarios. Maya además falló TC-74/TC-81 en seed44. DSX falló TC-89 en seed44 al afirmar que una factura estaba pagada; los logs del motor DSX informan `effort=Some(High)` pese a que los argumentos del harness solicitaron `medium`. Por esta diferencia efectiva de configuración, los promedios son descriptivos y no una comparación limpia de calidad bajo igual esfuerzo de razonamiento. Los recibos de cada semilla conservan argumentos, rutas y resultado; las sincronizaciones de Sheets fueron leídas de vuelta en las filas 30 y 25.

## Decisión de almacenamiento y uso

La regla de borrado preregistrada exigía que Maya quedara al menos 5 puntos por debajo en Q172 **y** al menos 5% por debajo tanto en prefill como en decode Q173, además de confirmar que no hubiera un consumidor requerido. La diferencia observada de calidad es 1.67 puntos, mientras Maya gana en ambas tasas y en los cuatro contextos. El gate de borrado no se cumple: **no se borró ningún peso Maya**.

El fallo TC-92 3/3 impide recomendar cualquiera de los perfiles para autonomía o datos sensibles. La evaluación no valida los controles de tenant; la corrección debe probarse en el sistema de herramientas/backend antes de habilitar esos usos. La diferencia de esfuerzo DSX también aconseja repetir Q172 con la semántica de razonamiento alineada antes de usar los scores para una decisión de calidad fina.
