# Plan — Q-20261010-STRATA-QUANTS-89TASKS

## Objetivo

Auditar el post “Benchmarked some Strata Qwen3.8-flash-next quants” y decidir si las cifras/selección de IQ3_XXS, IQ3_S, Coder podado y Swift/Tiel aportan evidencia útil a los perfiles o harnesses de LlamaCode.

## Candidatos y controles

- Candidatos que menciona la fila: ISTA-DASLab IQ3_XXS, IQ3_S, variante Coder podada y Swift/Tiel. Identificar los nombres oficiales exactos, artefactos, hashes, runtime y qué representa “89 tasks” antes de atribuir resultados.
- Controles locales reutilizables: ISTA IQ3_XXS/Strata 0.1.41, ASTRA calibrado IQ3_S/Strata, Q4 UD-Q4_K_XL/Strata y la auditoría histórica IQ1_M Coder. No equiparar IQ1_M con IQ3_XXS Coder ni atribuirle score del modelo distinto.
- Reusar evidencia compatible antes de considerar inferencia nueva. Evitar repetir la suite Hard Mode v2.8.0/28 tareas si la huella no cambia y la pregunta no exige variación.

## Trabajo preregistrado

1. Encontrar el post exacto, inspeccionar anexos/comentarios y verificar la ficha del publicador/modelos, archivos, cuantizaciones y versión de Strata.
2. Determinar si “89 tareas” son prompts de coding, escenarios de tools u otra evaluación; revisar selección, denominadores, semillas, métrica y tiempos por perfil.
3. Comparar únicamente contra evidencia local de misma suite/configuración; distinguir quant, runtime y hardware. Usar intervalos de incertidumbre cuando los conteos lo permitan.
4. Preflight de assets/hardware de sólo lectura. No descargar ni iniciar GPU hasta conocer la hipótesis, validar espacio/origen/hash y reservar el turno de recurso.
5. Para cualquier nuevo screening Hard Mode, aplicar el límite vigente del usuario: como máximo 30 minutos acumulados para las tres semillas de cada perfil. Si la proyección total supera 30 minutos, no iniciar o parar las semillas restantes y marcarlo parcial. No completar HE/BCB/TaskFlow sólo por inercia si el perfil ya excede el límite y no aporta una pregunta distinta.
6. No cambiar perfiles productivos, HarnessSpec ni defaults.

## Métrica de decisión

El post sólo aporta una recomendación local si identifica los modelos exactos y su protocolo permite alinear al menos una métrica con evidencia local. Para declarar una mejora de agente se requieren verificadores independientes y riesgos de seguridad aceptables; una puntuación agregada de 89 casos por sí sola no prueba Computer Usage, visión, audio, contexto ni codificación general.

## Recursos

GPU no reservada. GPU0 mostró ArtCraft/escritorio activo en el preflight de la tarea inmediatamente anterior; revalidar antes de cualquier carga. No hay descarga ni benchmark autorizado por este plan hasta demostrar compatibilidad de perfil y proyección ≤30 min por perfil.

## Evidencia esperada

Guardar `RESULTS.md`, recibo de fuentes, preflight local, configuración/hashes si existe corrida, y punto de reanudación. Si no hay suite comparable o el post no define sus 89 casos, cerrar como auditoría documental sin inventar equivalencias ni scores.
