# Preregistro — Q-20261017-DS4-STARFORGE-EVAL

Fecha: 2026-10-17 UTC
Task ID: `Q-20261017-DS4-STARFORGE-EVAL`
Lock: `68658b7d-2c49-4bf9-a233-0a57c5fb8982`

## Pregunta

¿La bifurcación `sf-q3-8flash` (StarForge/DwarfStar) o su harness aporta una
mejora que podamos usar en Coding/agentes, Computer Usage, Ingi-Charla, visión,
contexto largo o rendimiento de LlamaCode? Separar la evidencia publicada en
Apple Metal de cualquier resultado local sobre Linux/CUDA.

## Candidatos y controles

- Candidato externo: `Chida82/sf-q3-8flash`, Qwen3.8 Flash Next (`qwen4exp`),
  Apple Metal, MTP incorporado; servidor HTTP OpenAI/Anthropic y cliente externo.
- Orquestador: `Chida82/StarForge`, que mantiene hijos por modelo y sincroniza
  con `antirez/ds4`.
- Controles locales ya disponibles y no repetibles en este trabajo: ISTA
  IQ3_XXS/Strata frente a ASTRA IQ3_S/Strata, además de los perfiles SOL y
  Flash-Next locales. La comparación IQ3_XXS/ASTRA y las modalidades de esa
  campaña ya tienen recibos; no se vuelve a correr ninguna.

## Hipótesis y alcance

1. Los cambios publicados de kernels/MTP pueden mejorar rendimiento de
   Qwen3.8 Flash Next en el M5 Max usado por el autor, conservando salida
   idéntica según sus pruebas. Es evidencia específica de Metal y no predice
   la velocidad ni calidad en RTX 3090/CUDA.
2. La reducción del árbol a un solo modelo/backend facilita la lectura por
   agentes de código. No demuestra que mejore la calidad del agente LlamaCode,
   que usa otro runner y otros perfiles.
3. El protocolo A/A, pares ABBA, control de reloj/temperatura y paridad
   token/logit puede servir de referencia. Comparar con `Server Speed v1` y
   `docs/kv-cache-qa.md` para ver si ya cubrimos la necesidad antes de proponer
   cambios al harness.

No cambiar perfiles, defaults, HarnessSpec ni producto. No descargar GGUFs,
compilar el fork, ejecutar inferencia CPU/GPU, ni lanzar nuevas suites de
coding, visión, CU o contexto durante esta auditoría.

## Pruebas registradas antes de ejecutarlas

| ID | Comprobación | Criterio de validez | Estado esperado |
|---|---|---|---|
| P1 | Verificar OS/arquitectura, presencia de herramientas Apple Metal (`xcrun`, `system_profiler`) y GPUs locales (`nvidia-smi`). Lectura solamente. | El candidato se considera ejecutable sólo si el host es macOS/Apple Silicon y dispone del toolchain Metal. | Determinar aplicabilidad local; no es una prueba de calidad. |
| P2 | Buscar referencias/binarios/perfiles `sf-q3-8flash`, `StarForge` y `ds4` dentro del checkout, sin rastrear volúmenes completos. | Evidencia reproducible sólo si aparecen artefactos locales identificables. | Determinar si existe runtime candidato ya instalado. |
| P3 | Contrastar capacidades y límites del README/documentación primaria del candidato con la documentación local del benchmark. | Registrar rutas compatibles e incompatibilidades; no convertir declaraciones del autor en resultados propios. | Auditoría documental, no inferencia. |

Si P1 falla por plataforma, no correr `make`, `make test`, test de kernels,
paridad, MTP, visión ni speed bench del fork: requieren macOS/Metal y modelo.
La ruta CPU del proyecto se describe como referencia/debug y no representa el
uso normal; ejecutarla no produciría una comparación útil. No se instalarán
herramientas Apple ni se descargará un modelo de 137–165 GiB para un host
incompatible.

## Desviación de preregistro

Durante la triage inicial, antes de guardar este archivo, ya se consultó de
forma read-only `uname -srm`, `nvidia-smi` y la presencia de `xcrun`/
`system_profiler`. No se cargó un modelo, compiló código ni se envió trabajo a
GPU. Se registra como desviación temporal y se repetirá P1 después de guardar
este plan para que el resultado formal quede trazable.

## Fingerprints no repetibles

La campaña previa de IQ3_XXS/ASTRA usó Strata v0.1.41 y ya completó coding,
Server Speed, retrieval a 115K y pruebas parciales de visión/CU. El detalle de
hashes de modelo, suites, prompts, perfiles y límites está en la sección
“Índice para no repetir” de `docs/evaluacion-modelos-llamacode.md` y en
`artifacts/evaluacion-modelos-llamacode/Q-20261009-FLASHNEXT-IQ3XXS-AB/` y
`Q-20261014-IQ3XXS-MODALITY-FOLLOWUP/`. Este trabajo no crea ni reusa un
fingerprint de inferencia.

## Criterio de cierre

Publicar qué comprobaciones fueron ejecutables, el estado por uso de LlamaCode,
qué diferencias de metodología son transferibles y qué evidencia futura haría
falta en Apple Silicon. Sin cambio de recomendación/modelo/harness salvo que
aparezca evidencia local compatible, repetible y mejor que la ya registrada.
