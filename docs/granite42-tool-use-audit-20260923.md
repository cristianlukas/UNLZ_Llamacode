# Auditoría Granite 4.2 8B Q8 para tool-use — 2026-09-23

## Objetivo y criterio

Se investigó si la experiencia reportada con Granite 4.2 8B Q8 + Pi se
traslada a LlamaCode, en particular la afirmación de que Q8 reduce errores de
tool calling y el fenómeno de “sobrepensamiento” antes de una llamada.

Fuentes externas revisadas:

- [IBM: Granite 4.2](https://huggingface.co/blog/ibm-granite/granite-4-2):
  Granite 4.2 8B fue post-entrenado con trayectorias agentivas de software,
  terminal y tool calling, y soporta razonamiento y tool calling nativo.
- [Pi: documentación](https://pi.dev/docs/latest) y [cómo funciona el loop](https://pi.dev/docs/latest/how-pi-works):
  Pi usa turnos de tools, sesiones persistentes, compaction y extensiones; sus
  herramientas recomiendan truncar resultados grandes indicando dónde leer el
  resultado completo.

Regla de promoción: un candidato sólo puede reemplazar un perfil si conserva la
calidad funcional, la corrección de tools y la estabilidad, y además mejora una
métrica operativa relevante. Un smoke de selección de tools no equivale a HE0,
HE20 o BCB del harness completo.

## Condiciones reproducibles

- Ubuntu, `llama-server` de
  `llama.cpp-adaptive-build-linux-20260915`, endpoint OpenAI-compatible local.
- Sampling común: `temp=0.60`, `top_p=0.95`, `top_k=20`, `min_p=0.0`,
  `repeat_penalty=1.0`, `presence_penalty=0.0`, un slot, contexto 8192.
- El checkout ya tenía otros servidores de benchmark activos; por eso los
  tiempos son orientativos y no se usan para declarar una mejora de throughput.
  La corrección de tool calls se evaluó por secuencia y resultado verificable.
- Granite descargado desde
  `bartowski/granite-4.2-8b-GGUF:granite-4.2-8b-Q8_0.gguf`:
  9.345.614.240 bytes, SHA-256
  `b06eac4b12ee3b65a8bf9c6fd122fe46203291fd9c09cba7765d4d6400419aa9`.
- Controles locales: Qwen3.5-9B Q4_K_M y Qwen3.5-4B Q4_K_M ya presentes en el
  root de modelos.

## Prueba A: la pregunta exacta del reporte

Prompt:

```text
run tools, what is the current directory and list the files
```

Tools declaradas: `cmdshell(command)` sólo para `pwd` y
`listFiles(path)` sólo para listar un directorio.

### Un único request

Se hicieron 10 repeticiones con `tool_choice=auto` y 10 con
`tool_choice=required`, sin ejecutar todavía los resultados.

| Modelo | Auto: `cmdshell → listFiles` | Auto: sólo `cmdshell` | Required: `cmdshell → listFiles` | Required: sólo `cmdshell` |
|---|---:|---:|---:|---:|
| Granite 4.2 8B Q8 | 0/10 | 10/10 | 0/10 | 10/10 |
| Qwen3.5-9B Q4 | 7/10 | 3/10 | smoke previo: 1/3 doble | — |
| Qwen3.5-4B Q4 | 0/10 | 10/10 | — | — |

Granite no intentó poner `listFiles` dentro de `cmdshell`; simplemente eligió
hacer una sola llamada por request. Por lo tanto, contar ese primer response
como fallo sería incorrecto si el harness continúa el loop.

## Prueba B: loop real de observación → tool → resultado → siguiente tool

Después de `cmdshell("pwd")` se devolvió `/workspace/project`; después de
`listFiles` se devolvió un inventario fijo y se verificó la respuesta final.

| Modelo | Repeticiones | Secuencia válida | Resultado | Mediana aproximada |
|---|---:|---:|---:|---:|
| Granite 4.2 8B Q8, thinking OFF | 10 | 10/10 | correcto | ~2,24 s (2.238 ms) |
| Qwen3.5-9B Q4, thinking OFF | 10 | 10/10 | correcto | ~1,08 s (1.081 ms) |

Granite usó `listFiles` con la ruta absoluta recién obtenida; Qwen usó `.`.
Ambos comportamientos son válidos. Granite no fue superior en el loop que usa
LlamaCode y fue más lento en esta captura; no se promueve como perfil principal.

## Prueba C: contrato `read_file → write_file`

Se creó un workspace temporal con `README.md`. El agente debía hacer
exactamente `read_file(README.md)`, luego `write_file(tool_contract.txt,
CONTRACT_OK)`, y el verificador comprobó el contenido real.

| Modelo | Repeticiones | PASS | Llamadas extra |
|---|---:|---:|---:|
| Granite 4.2 8B Q8, thinking OFF | 5 | 5/5 | 0 |
| Qwen3.5-9B Q4, thinking OFF | 10 | 10/10 | 0 |

La primera medición de Qwen que marcaba 0/10 tenía un verificador que exigía un
salto de línea no solicitado; se descarta y se repitió con `strip()`. No se
conserva ese falso resultado.

## Prueba D: costo de thinking y “overthinking”

Se repitió la pregunta del reporte con `--reasoning on`, `max_tokens=900` y el
mismo schema.

| Modelo | Repeticiones | Primera acción | Razonamiento observado | Tiempo por primer request |
|---|---:|---|---:|---:|
| Granite 4.2 8B Q8 | 3 | siempre `cmdshell(pwd)` | 1.069–2.207 caracteres | 3,7–7,3 s (3.699–7.329 ms) |
| Qwen3.5-9B Q4 | 3 | `cmdshell(pwd)` + `listFiles(.)` en el mismo response | 283–400 caracteres | 1,1–1,4 s (1.119–1.382 ms) |

La diferencia confirma que el razonamiento puede gastar muchos tokens antes de
la primera acción, pero en este caso Granite no obtiene una decisión mejor que
Qwen: Qwen produce ambas llamadas válidas en el primer response y con menos
latencia. La cifra de caracteres es la salida de razonamiento que el endpoint
dejó disponible para el probe, no una afirmación de que deba mostrarse al
usuario.

## Qué sí sirve para LlamaCode

1. **Mantener la evaluación por loop completo.** La primera respuesta puede
   contener sólo la primera tool y ser correcta; el score debe considerar la
   secuencia, los resultados ejecutados y la verificación final. Esto ya es
   compatible con el harness nativo de LlamaCode.
2. **Separar costo de thinking de corrección.** Registrar TTFT/primera acción,
   tokens de reasoning, cantidad de tools, reparaciones y éxito verificado en
   columnas separadas. No premiar una respuesta final que esconda llamadas
   omitidas o resultados inventados.
3. **Conservar el contrato de tools pequeñas y explícitas.** El caso funcionó
   mejor cuando `cmdshell` quedó restringida a `pwd` y `listFiles` fue una tool
   independiente. Esto coincide con las schemas y la validación fail-closed de
   LlamaCode.
4. **Resultados grandes:** Pi refuerza una idea ya identificada en la auditoría
   de harness: truncar mostrando cómo recuperar el resultado completo puede
   reducir contexto, pero requiere un almacén de artefactos confinado,
   escritura atómica, expiración y una tool de lectura. No se implementa por
   inferencia de este smoke.

## Decisión

- **No se agrega Granite 4.2 como perfil productivo ni default.** En el loop
  real y en el contrato de escritura no supera a Qwen3.5-9B; en thinking ON es
  claramente más lento y hace menos trabajo por primer turno.
- **No se modifica el harness de ejecución.** La semántica correcta —una tool a
  la vez, resultado real, siguiente turno y verificación— ya está presente.
  La medición queda registrada para que una campaña futura no repita el mismo
  smoke ni confunda un primer response parcial con un fallo.
- **No se agrega Granite Q4/Q8 a `assets/system_profiles.json`.** Para
  justificar un perfil experimental harían falta HE0, HE20, BCB, estabilidad de
  carga y una comparación con condiciones de GPU aisladas. La descarga queda
  fuera del repo como artefacto local de investigación.

Identificador de campaña: `granite42-tool-use-audit-20260923`.

## Validación del repositorio

- `python3 -m unittest discover -s tests -p 'test_harness_matrix.py' -v`:
  6/6 PASS.
- `XDG_CACHE_HOME=/tmp/llamacode-codex-cache ./scripts/tests-linux.sh Release`:
  build Release correcto y 77/77 tests PASS (incluye QML y `test_agent_tools`).
- El primer intento con la caché predeterminada quedó bloqueado porque en esta
  notebook `/home/.cache` está montado sobre NTFS; se canceló y se repitió en
  filesystem nativo. No es un fallo del producto ni de la campaña.
