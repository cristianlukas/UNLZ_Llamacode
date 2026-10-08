# Swift-Qwen3.8-27B — auditoría local

Fecha: 2026-09-14  
Decisión: **no reemplaza SOL ni se agrega como default**. Queda como candidato
experimental multimodal, rápido y con razonamiento más corto.

## Qué propone

[Swift-Qwen3.8-27B](https://huggingface.co/ukisai/Swift-Qwen3.8-27b) es un
fine-tune de Qwen3.8 que intenta reducir razonamiento redundante, no recortar
el presupuesto de pensamiento por fuerza. El repositorio afirma reducciones de
tokens de pensamiento y mantiene variantes GGUF hasta Q8, MTP y un proyector de
visión. La propia tarjeta aclara que sus tablas principales son comparaciones
BF16/adaptador y que la suite completa todavía no fue re-evaluada sobre los GGUF.

La licencia es `Swift Open License 1.0`: uso personal, de investigación,
educativo, de evaluación y organizaciones con ARR de hasta US$1M; por encima de
ese umbral requiere licencia empresarial.

## Artefactos descargados

Todos quedaron en el directorio requerido:

`/media/cristian/7CFE1E0FFE1DC1F6/models/Swift-Qwen3.8-27B-GGUF/`

| Archivo | Tamaño |
|---|---:|
| `Swift-Qwen3.8-27B-Q4_K_M.gguf` | 18.024.380.576 bytes |
| `mmproj-Swift-Qwen3.8-27B-F16.gguf` | 927.606.976 bytes |

Se respetó el límite de quant del proyecto: pesos Q4_K_M y KV Q8; no se usó
ningún KV superior a Q8.

## Pruebas locales

Hardware: 2× RTX 3090, reparto por capas, driver 595.71.05, CUDA 12.0.140,
MTP3 cuando correspondía, KV K/V `q8_0/q8_0`. El smoke, BCB y visión se
ejecutaron con el backend CUDA local compilado para SM86.

| Prueba | Resultado | Estado |
|---|---:|---|
| Carga + HE0, thinking apagado | Responde correctamente | **Pasa** |
| Decode corto, MTP3, thinking apagado | 71,79 tok/s; aceptación 135/165 | Funcional |
| Contexto profundo, 55.032 tokens | Prefill 948,62 tok/s; decode 78,41 tok/s; marcador correcto | **Pasa** |
| Tool-use `read_file` | `finish_reason=tool_calls`, JSON válido | **Pasa** |
| Visión con `mmproj` | Describe correctamente una captura de discos y red | **Pasa** |
| BCB/8 | **1/8** | Calidad agentiva insuficiente |

La prueba con thinking habilitado y presupuesto 512 llegó a truncar la respuesta
antes del código porque el razonamiento consumió el límite; no es un fallo del
servidor, pero demuestra que el presupuesto debe parametrizarse por perfil.

## Comparación con la tabla actual

| Perfil | Velocidad | Calidad / agentes | Contexto | Visión | Decisión |
|---|---:|---:|---:|---|---|
| SOL | 74 narrativo / 102 código | BCB 8/8; tool-use validado | 262K validado | No validada | Default |
| Swift Q4_K_M | 71,79 tok/s sin thinking; 78,41 a 55K | BCB 1/8; tool-use puntual OK | 55K probado; 262K declarado | **Sí, validada localmente** | Experimental |
| TERRA | 56–58 tok/s | BCB histórico 6/8 | 64K | Sí | Sigue siendo más confiable como agente |

Swift aporta una combinación útil de visión, contexto largo y reducción de
razonamiento, pero no es globalmente superior: queda por debajo de SOL en
calidad agentiva y no ofrece una mejora clara de decode frente a sus 102 tok/s
de coding. Tampoco se debe trasladar directamente el `x1.95` del post: esa
cifra depende de la reducción de tokens generados y de benchmarks BF16/W4A16,
no de tok/s brutos reproducidos en nuestro entorno.

## Resultado operativo

- No se modificó SOL ni el orden del dropdown.
- No se agregó Swift como perfil activo.
- Se conserva el modelo y el `mmproj` para futuras pruebas multimodales.
- Si se necesitara un perfil de visión alternativo, Swift es candidato a una
  entrada experimental separada; no debe presentarse como reemplazo de SOL sin
  repetir HE0, HE20 y BCB con thinking y tool-use del harness real.

## Actualización de la nueva referencia comunitaria — 2026-09-18

La publicación reciente del autor no cambia esta decisión. El model card ahora
publica comparaciones BF16/adaptador y cuantizadas a 4 bits con menos tokens de
razonamiento, además de soporte declarado para visión, MTP y tool-calling. Son
resultados útiles para justificar una segunda ronda, pero no sustituyen los
resultados locales: fueron obtenidos con vLLM 0.27.1, BF16/W4A16 y cinco semillas,
mientras que nuestro dato reproducido en 2× RTX 3090 es Q4_K_M + KV Q8 con
BCB 1/8.

La afirmación de `x1,95` se refiere principalmente a la reducción de tokens de
thinking y no a una multiplicación garantizada de tok/s brutos en LlamaCode.
Además, las tablas del autor comparan Swift contra su propio Qwen3.8 base y no
contra SOL con el mismo harness. El anuncio de Swift1.5 y Swift Flash-Next se
deja como vigilancia futura: no se descarga ni se agrega una variante que aún
no tiene artefacto y benchmark local reproducible.

No se repitió BCB ni se volvió a descargar el GGUF porque ya existen pruebas
locales de Swift con la misma familia de runtime y el resultado fue claramente
inferior a SOL en calidad agentiva. La referencia comunitaria se incorpora al
registro, no al catálogo activo.
