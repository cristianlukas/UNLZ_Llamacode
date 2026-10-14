# Plan — Q-20261010-LIQUID-D1-DECISION

## Objetivo

Determinar si Liquid AI d1-3B o d1-omni-600M tiene una aplicación verificable como modelo de decisión de una pasada (selección/ruteo de tools) dentro de LlamaCode, sin atribuirle generación general, Computer Use real, audio, visión o contexto largo.

## Candidatos y controles

- Candidatos: las versiones oficiales d1-3B y d1-omni-600M. Fijar repositorio/revisión, formato, licencia, requisitos y salida tipada antes de cualquier posible inferencia.
- Control: política determinista y evidencia local del screen de decisiones textuales MUSE / Git-risk, sólo como referencia histórica; no combinar sus métricas si el corpus, el esquema o el runtime difieren.
- Fixtures potenciales: suites locales de decisión de Computer Use textual y clasificación de riesgo Git. Revisar independencia, clases, salidas esperadas, esquema y límites antes de ejecutar.

## Alcance y protocolo

- Primero comprobar fuentes primarias, presencia local de pesos/runtime y compatibilidad con el harness/fixtures.
- Sin descargas, GPU ni cambios de perfiles. Si hay una copia compatible local, se permite únicamente una sonda acotada de CPU que no exceda 30 minutos de tiempo total por perfil; fijar before/after y mantener el control.
- No convertir texto explicativo en acción ejecutada. Evaluar sólo decisión tipada, calibración/ranking si la API la expone, validez del esquema, aciertos/errores por clase y latencia total.
- Si no hay pesos/harness compatibles, cerrar como auditoría documental y dejar explícito qué falta para un screen local.
- No proponer que el modelo sustituya guardrails, autorización, comprobaciones deterministas o aprobación humana sin evidencia externa independiente.

## Evidencia prevista

Fuentes oficiales/model cards, manifiestos de disponibilidad local, hashes de fixtures/runner si se ejecuta, matriz de compatibilidad, resultados por caso, latencia y registro de limitaciones. No se crearán nuevas etiquetas ni se alterarán fixtures compartidos.
