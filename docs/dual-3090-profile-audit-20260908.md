# Auditoría de perfiles dual-3090 — 2026-09-08

## Conclusión

La receta externa contiene perfiles potencialmente superiores en **otro stack**,
pero no hay evidencia local suficiente para promoverlos en LlamaCode. Sus
mejores números corresponden a vLLM con pesos AutoRound/FP8, TP=2 y un drafter
MTP; esta instalación sólo tiene llama.cpp/GGUF operativos. No están instalados
vLLM, los pesos AutoRound/FP8 ni los modelos Tess/AgentWorld del listado.

Por seguridad, se mantienen los perfiles prioritarios actuales. No se agrega un
perfil que sólo tenga cifras publicadas pero no pase carga, generación coherente
y el harness de calidad local.

## Comparación con lo disponible en esta PC

| Candidato | Resultado publicado | Estado local | Decisión |
|---|---:|---|---|
| vLLM Qwen3.8-27B FP8, MTP, 262K | 67,4 narr. / 85,8 code tok/s | Sin vLLM ni pesos FP8; MTP expuesto a un bug de escritura reportado por la propia receta | No promover |
| vLLM Qwen3.6-27B AutoRound INT4, KV FP8, 262K | 72 / 90 tok/s | Sin artefacto AutoRound, vLLM ni drafter MTP compatible | No promover |
| vLLM Qwen3.6-35B-A3B, concurrencia | Perfil para múltiples agentes | No hay runtime vLLM ni artefacto dual validado | No promover |
| Gemma-4-31B QAT-AWQ | 224K, dual-only | El GGUF local no equivale al artefacto AWQ/vLLM de la receta | No promover |
| Tess-4-27B / AgentWorld-35B | 262K | No hay modelos ni runtime local | No promover |
| llama.cpp Qwen3.8 Q8_K_XL | 262K | No hay artefacto Q8 local; la política del proyecto permite como máximo Q8 | Pendiente, no descargar automáticamente |

Los números de la receta tampoco son directamente comparables con nuestros
BCB/TPS: mezclan throughput de concurrencia, decode narrativo/código, KV FP8 y
un scheduler vLLM. En un agente individual, la latencia de prefill y la
confiabilidad de las tool-calls importan tanto como el decode agregado.

## Prueba local del análogo más cercano

Se probó el archivo disponible:

`Qwen3.8-27B-Q5_K_M.gguf`

con dos RTX 3090, P2P PCIe activo, `split-mode layer`, contexto 262K, KV K/V
`q8_0`, batch 2048/512 y MTP embebido.

| Variante | Carga | Smoke test | Resultado |
|---|---|---|---|
| Q5 + MTP3 + 262K + KV Q8 | OK, health `ok` | 19,57 tok/s; aceptación MTP 0%; salida `////////////////////////////////` | Fallida para promoción |
| Q5 sin MTP + 131K + KV Q8 | OK, health `ok` | 31,51 tok/s; respuesta exacta `Q5-NOMTP-OK` | Funciona, pero no supera SOL/TERRA |

El fallo no es de carga ni de P2P: el modelo funciona cuando se desactiva el
drafter. La configuración Q5+MTP no se convierte en perfil prioritario porque
un smoke test inválido bloquearía cualquier BCB posterior.

## Candidatos ya investigados

- **NInfer-3090 Qwen3.8:** compila y carga un artefacto histórico, pero produjo
  texto repetitivo/corrupto con y sin MTP; permanece experimental.
- **club-3090 / ik_llama:** el GGUF Qwen3.6 disponible aborta con acceso ilegal
  CUDA antes de atender una petición; no se promueve.
- **vLLM/AutoRound:** queda como línea de trabajo futura. Requiere instalar un
  entorno aislado, descargar pesos específicos y repetir HE0 → HE20 → BCB con
  el mismo harness. No se debe inferir superioridad a partir de los números de
  otra máquina o de throughput concurrente.

## Estado aplicado en LlamaCode

- **SOL** continúa como perfil Qwen 28B prioritario validado.
- **ASTRA** continúa experimental para contexto largo.
- **LUNA** continúa como perfil de visión/interacción.
- Los perfiles vLLM/DFlash existentes siguen siendo opt-in y no fueron
  promovidos a la cola principal.
- No se modificó Windows.
- El servidor de LlamaCode fue restaurado y quedó saludable después de las
  pruebas (`http://127.0.0.1:8031/health` → `{"status":"ok"}`).

