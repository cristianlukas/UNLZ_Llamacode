# Auditoría Laya / Jev — 2026-09-18

## Qué es

Laya no es un modelo generativo ni un reemplazo para SOL. Es un motor de
decisiones no autoregresivo basado en un encoder bidireccional, con salidas
estructuradas `choice`, `score` y `noul` (probabilidad booleana). El paquete
oficial se presenta como un componente para routing, guardrails, moderación y
triage, no para generar código ni operar herramientas directamente.

Fuentes: [repositorio oficial](https://github.com/NandhaKishorM/laya),
[modelo en Hugging Face](https://huggingface.co/convaiinnovations/laya) y
[paquete PyPI](https://pypi.org/project/laya/).

## Instalación y artefacto local

El modelo quedó en:
`/media/cristian/7CFE1E0FFE1DC1F6/models/Laya-421M/`.

| Archivo | Tamaño | SHA-256 |
|---|---:|---|
| `model.safetensors` | 842.609.210 bytes | `891102d372688fc2a094dac56a384bc537b87c63f21f9f3dac0be2b7cbc8d86c` |
| `tokenizer/tokenizer.json` | 3.583.228 bytes | `6c8aaa9a542084f2457eab775d4eeb51f92a70c0fd9de28d5ed2b0ddec3c08d30` |

Se probó con `laya==0.1.6`, PyTorch 2.14 y Transformers 5.17 en una RTX 3090.

## Pruebas locales

| Prueba | Resultado | Decisión |
|---|---:|---|
| Router incorporado, warm-up GPU | **13–15 ms** por consulta | Muy útil como System 1 local |
| Guardrail de prompt injection | Detectó `jailbreak=0,9689` y `prompt_injection=1,0` | Candidato para filtro previo |
| Routing coding | `domain=code`, probabilidad 0,9824 | Útil para elegir perfil/modelo |
| Triage técnico | `technical_help=0,9953` | Útil para clasificar intención |
| Clasificación de acción de PC | Identificó lectura, reversible, destructiva y externa | Útil como señal adicional |
| Confirmación genérica | Inconsistente: no elevó de forma fiable la confirmación en acciones destructivas | **No usar para autorizar acciones** |
| Generación de texto/código | No aplica: no genera tokens | No reemplaza ningún perfil |

En CPU las mismas consultas tardaron aproximadamente 248–564 ms; la GPU es la
configuración práctica para un control interactivo.

## Integración recomendada para LlamaCode

No se agrega al dropdown de modelos ni a la tabla de modelos generativos. La
integración correcta, si se implementa, sería un módulo auxiliar delante del
harness:

1. Laya clasifica intención, dominio, dificultad y presencia de prompt injection.
2. LlamaCode aplica una política determinista de permisos, confirmaciones y
   sandbox; nunca delega esa decisión únicamente a Laya.
3. Sólo después se selecciona SOL, MINI u otro perfil y se invocan herramientas.
4. La confianza de Laya se registra como señal de observabilidad y routing,
   no como autorización de una acción destructiva o externa.

Esto podría reducir llamadas innecesarias a SOL para routing/guardrails y
mejorar el modo de control de PC, pero no es una mejora de PP/TG/BCB de los
modelos actuales. No se modifica todavía el código del harness: primero habría
que definir el contrato de decisión, los umbrales y una suite de regresión con
acciones permitidas, reversibles, destructivas y externas.

## Decisión

**Conservar descargado como componente experimental de routing/guardrail.**
No promoverlo como perfil de modelo, no cambiar SOL y no permitir que sus
probabilidades sustituyan las reglas de seguridad existentes.
