# Auditoría del patrón Qwen Flash-Next para aplicaciones agentivas — 2026-09-14

## Fuente y alcance

La publicación describe una integración anecdótica de Qwen Flash-Next dentro de
una aplicación de alquiler de autos. El modelo consulta datos mediante tools,
propone altas o cambios y deja la mutación definitiva detrás de una pantalla de
aprobación. También menciona RAG y un harness estilo DeepSeek, pero no informa
hardware, quant, backend, plantilla, tasa de errores de tools ni una evaluación
reproducible.

Los 35 millones de tokens y el resultado “one shot” sirven como experiencia del
autor, no como benchmark comparable con LlamaCode. No se usan para cambiar el
perfil principal ni para promover ASTRA.

## Qué sirve para LlamaCode

| Idea del post | Situación en LlamaCode | Decisión |
|---|---|---|
| Consultar información con RAG | `hybrid_search`, `repo_slice`, memoria por capas y expansión del grafo de contexto | Ya cubierto; conservarlo como recuperación, no como acceso directo a bases externas |
| Acceder a datos y acciones mediante tools | El agente usa tools con payloads estructurados, permisos y trazabilidad | Ya cubierto; no agregar acceso directo del modelo a SQLite o archivos de dominio |
| Proponer cambios antes de aplicarlos | La UI muestra tarjetas de aprobación para `write`, `shell` y acciones externas; Tasks tiene workflows `approval` | Ya cubierto; mantener aprobación por defecto para mutaciones sensibles |
| Validar argumentos con un esquema | El parser y la política de tools validan nombres, argumentos, permisos y hashes de payload | Ya cubierto en C++; Pydantic no aplica como dependencia porque el harness nativo es Qt/C++ |
| Ejecutar trabajos largos durante la noche | LlamaCode conserva corridas administradas, contexto largo, presupuesto de razonamiento y sub-agentes configurables | Disponible; usar SOL para el trabajo principal y reservar sub-agentes según contexto/VRAM |
| PTC o llamadas más compactas | El post reconoce llamadas erróneas y repetidas con PTC | No se convierte en default: la robustez del tool-use pesa más que reducir tokens |

## Comparación con los perfiles actuales

| Perfil | Lectura para este caso |
|---|---|
| **SOL** | Sigue siendo la opción recomendada: BCB 8/8, tool-use estable, contexto 262K y mejor desempeño agentivo. |
| **ASTRA** | Qwen3.8 Flash-Next puede ser interesante para sesiones largas, pero su BCB/HE0 local no es válido y la salida quedó contaminada en pruebas previas. No reemplaza SOL. |
| **QWEN35-A3B** | Alternativa cuando importan visión, 262K y varias sesiones simultáneas; su BCB es inferior al de SOL. |
| **TERRA** | Fallback local razonable para razonamiento y visión, con 64K; no mejora la robustez general de SOL. |
| **MINI** | Útil como sub-agente para clasificación, extracción y tareas cortas; no para dirigir la aplicación. |

## Validación local

Se ejecutó la campaña focalizada relacionada con el patrón de la publicación:

| Prueba | Resultado |
|---|---:|
| Índice/contexto para recuperación | OK |
| Tools del agente, validación y errores | OK |
| AppController y ciclo de aprobación | OK |
| Workflows con aprobación | OK |
| Automatizaciones y permisos | OK |
| Total de la campaña | **5/5** |

La suite completa anterior permanece en **77/77**. No se observaron regresiones
en RAG, tool-use, aprobación ni automatizaciones.

## Resultado

No se incorpora un modelo nuevo ni se cambia el default. La publicación confirma
una arquitectura que LlamaCode ya implementa: recuperación controlada + tools
tipadas + propuesta revisable + aprobación antes de mutar estado.

Para una aplicación externa conectada a LlamaCode, la integración recomendada es
exponer una API/MCP con operaciones de lectura y propuestas de escritura, nunca
entregarle al modelo acceso directo a la base. Las operaciones de escritura deben
devolver una propuesta y esperar aprobación explícita.

