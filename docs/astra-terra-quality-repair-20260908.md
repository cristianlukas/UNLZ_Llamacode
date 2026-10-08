# Reparación de calidad ASTRA/TERRA — Ubuntu — 2026-09-08

## Cambios aplicados

- ASTRA mantiene Qwen3.8 Flash-Next UD-Q4_K_XL, cache experto 188, contexto
  196K y KV Q8/Q8. Se activó razonamiento `medium`, presupuesto 8192 y el
  sampling recomendado para thinking (`temp=1.0`, `top_p=0.95`, `top_k=20`).
- TERRA dejó de apuntar al Qwen 28B duplicado de SOL. Ahora usa Ling 3.0 Tiny
  Q6_K, contexto 131K, KV Q8/Q8, thinking `medium` y presupuesto 2048.
- La configuración anterior de Qwen 28B quedó como `TERRA-LEGACY`, deprecated,
  sólo para rollback.
- El template Bailing V3 de Ling quedó bundleado como recurso
  `ling3-tools.jinja`; el perfil lo materializa en la carpeta de datos de la
  aplicación, sin depender de una ruta fija de Windows o Linux.
- El control de calidad de thinking/sampling se mantiene separado en
  `platformArgs.linux`; Windows conserva su selección de plataforma y puede
  reutilizar el mismo template bundleado sin cambiar sus rutas de modelos.

## Evidencia inicial

- ASTRA: carga y smoke API correctos, pero las pruebas con `ubatch=512` y
  `ubatch=1` siguen produciendo corrupción de texto en matemática, código y
  tool-calling. No se promociona: el problema queda identificado como una
  limitación del camino experimental de prefill/cache, no como un simple
  parámetro de sampling.
- TERRA/Ling: el template Bailing V3 produjo una llamada OpenAI estructurada
  (`finish_reason=tool_calls`, nombre y argumentos JSON válidos) y una función
  Python con tests en el smoke directo; HE0/BCB completo del harness todavía
  debe repetirse para convertir esa evidencia en una puntuación oficial.

No se presenta ninguna mejora de calidad como validada hasta completar esa
repetición. Todos los pesos y caches respetan el límite máximo Q8.
