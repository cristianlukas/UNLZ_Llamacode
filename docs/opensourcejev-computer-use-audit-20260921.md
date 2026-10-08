# Auditoría OpenSourceJev para Computer Use — 2026-09-21

## Qué se verificó

Se revisó el repositorio oficial
[OpenSourceJev](https://github.com/sabeel111/OpenSourceJev), su motor nativo,
el ejemplo de ViZDoom y sus pruebas. El proyecto extrae logits directamente de
llama.cpp y puntúa candidatos finitos; no genera JSON libre para decidir una
acción.

Sus primitivas son:

- `Choice`: elegir una acción entre opciones conocidas;
- `Noul`: decisión booleana calibrada;
- `Score`: nivel ordinal o puntuación;
- `Text`: generación opcional, fuera del camino seguro.

El ejemplo de DOOM recibe estado estructurado del juego —ángulo, enemigos,
salud, munición— y elige entre acciones como `shoot` o `strafe`. No interpreta
capturas de escritorio ni tiene un detector de controles UIA.

## Pruebas reproducibles

Se clonó el repositorio en un directorio temporal y se creó una venv aislada;
no se modificó el repositorio ni el entorno de LlamaCode.

| Prueba | Resultado |
|---|---:|
| Suite oficial Python (`tests/`) | **16/16 PASS** |
| Tests de API/workflow | PASS |
| Tests de logits y candidatos | PASS |
| Test con modelo Qwen real | No ejecutado: el checkpoint/dll nativo del proyecto no está instalado |

La afirmación externa de aproximadamente 100 ms por decisión simple y 3,4 s
para diez decisiones proviene del autor y de otra máquina; no es comparable
directamente con nuestra RTX 3090 ni con la latencia de LlamaCode.

## Comparación con LlamaCode

| Capacidad | OpenSourceJev | LlamaCode / Laya |
|---|---|---|
| Decisión finita sin JSON frágil | Sí | El harness valida schemas y tool-calls |
| Clasificación rápida de intención/riesgo | Posible, si el estado se construye manualmente | Laya local ya mide 13–15 ms warm y clasifica coding, inyección y triage |
| Comprensión de pantalla | No | UIA, OCR, snapshots, visión y búsqueda de imágenes |
| Acciones de PC | Sólo devuelve una etiqueta candidata | Ejecuta tools con stale guard, receipts, aprobación y verificación |
| Seguridad destructiva | No es un autorizador | `isDestructiveAction`, approval/HITL y Zero-Autonomy |
| Acciones arbitrarias de escritorio | No | Sí, mediante herramientas semánticas y visuales |

## Dónde sí podría servir

El único uso razonable es un sidecar opt-in para bucles de acción con un espacio
cerrado y explícito, por ejemplo:

```text
estado UIA/OCR resumido + acción propuesta
  → choice: {read, reversible, external, destructive}
  → score: confianza / ambigüedad
  → el guardrail determinista decide si ejecutar, pedir aprobación o rechazar
```

También podría elegir entre `desktop_click_element`, `desktop_key`,
`desktop_type` y `desktop_wait` cuando el programa ya expuso controles y el
conjunto de acciones está completamente definido. Nunca debería recibir
autoridad para aprobar por sí solo un borrado, publicación, envío de correo o
acción externa.

## Decisión

No se agregó un perfil generativo, no se descargó otro modelo y no se modificó
el ejecutor Computer Use. OpenSourceJev no es superior a Laya en latencia local
medida ni a LlamaCode en cobertura/seguridad de PC. La idea transferible —
decisiones tipadas sobre candidatos finitos— ya está cubierta parcialmente por
schemas, router, aprobación y receipts; queda registrada como posible sidecar
de bajo riesgo para bucles de UI estructurada.

Para promoverlo habría que medir con el mismo corpus de 100 estados UIA/OCR:

1. exactitud de acción y tasa de abstención;
2. falsos permisos sobre acciones destructivas;
3. p50/p95 de decisión y coste de serializar el estado;
4. impacto frente a Laya y frente al camino actual sin sidecar.
