# Liquid AI d1-3B / d1-omni-600M — evaluación de encaje

## Resultado

**Auditoría documental completa; sin corrida local, descarga ni GPU.** Los pesos no están en las raíces de modelos revisadas. La evidencia del fabricante describe dos modelos de decisión de una pasada que devuelven resultados tipados (`noul`, `choice`, `score`) leyendo la distribución sobre opciones; no generan texto. Eso los hace candidatos posibles para un selector asesor de intención, riesgo o grupo de herramientas, no para reemplazar al modelo coding ni para ejecutar acciones.

## Diferencias entre candidatos

- **d1-3B**: toma texto/JSON e imágenes, contexto anunciado de 32.768 tokens y 3,12B de parámetros. La ficha del fabricante informa Decision Index 0.2.1 = 48,57 y latencia de 8 ms por pregunta en RTX 4090. Es la primera opción documental para un test local de routing textual porque el fabricante lo presenta como modelo de decisión general y esa es la métrica publicada más alta dentro de esta familia.
- **d1-omni-600M**: 587M de parámetros, texto/imágenes o un clip de audio de hasta 30 s, contexto de 16.384; con imágenes, el texto de estado/pregunta se recorta a 896 tokens. Su ficha lo marca experimental y publica 15,95 en Decision Index. El fabricante indica que la evaluación específica de decisiones sobre audio sigue abierta; no transfiere a ASR/TTS ni a Ingi-Charla.

Son cifras y capacidades publicadas por Liquid AI, no mediciones locales ni una comparación con SOL/ASTRA/Q4. No prueban que uno reduzca errores en LlamaCode, que autorice tools correctamente ni que sea más rápido en estas RTX 3090.

## Encaje con LlamaCode

El punto de evaluación más razonable sería pasarle al candidato estado ya construido por el host y alternativas de routing cerradas, por ejemplo “tool group A/B/no tool”, y medir aciertos por clase, calibración/probabilidades, latencia fría y caliente y rechazo/fallback. No entregarle autoridad para escribir argumentos, ejecutar tools, sortear permisos o confirmar acciones. La ruta existente de `adaptiveToolRouting` reduce la primera superficie de tools y preserva la expansión posterior; el informe Mica anterior también concluyó que un modelo de decisión necesita un endpoint tipado separado, no un perfil generativo convencional.

No hay pesos d1 ni un backend de inferencia compatible local en las raíces examinadas. El Mica instalado es sólo una referencia de benchmark y no se reutiliza como resultado d1. Sin corpus de imágenes/audio para este objetivo, no se abre una evaluación multimodal; contexto largo tampoco aplica, y los 32K/16K publicados quedan muy por debajo de 262K.

## Decisión

**No integrar d1 ni cambiar perfiles/defaults.** Mantenerlo como candidato de benchmark para una comparación local futura, empezando por d1-3B en una suite de routing textual etiquetada, con un control determinista y el control generativo actual. d1-omni sólo merece una pista separada si aparece un caso de clasificación sobre audio real o imágenes, no como modelo de voz conversacional.

No se generó fingerprint de inferencia: no hubo pesos, runtime, HarnessSpec ni ejecución. Próximo requisito para medir: preparar un holdout etiquetado para decisiones de herramientas y contar con una integración que consuma las respuestas probabilísticas tipadas sin conceder permisos al modelo.

Fuentes: [model card d1-3B](https://huggingface.co/LiquidAI/d1-3B), [model card d1-omni-600M](https://huggingface.co/LiquidAI/d1-omni-600M), [blog oficial de lanzamiento](https://www.liquid.ai/blog/open-d1).
