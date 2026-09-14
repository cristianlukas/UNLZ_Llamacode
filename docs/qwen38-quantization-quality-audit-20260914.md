# Auditoría de cuantización de Qwen3.8-27B para LlamaCode

Fecha: 2026-09-14

## Alcance

Se revisó el informe público de Quesma sobre Qwen3.8-27B y se lo contrastó con
las pruebas ya ejecutadas en esta máquina, usando dos RTX 3090, Linux, P2P
habilitado y la política de LlamaCode de no superar Q8 ni en pesos ni en KV.

Fuente externa: [Qwen3.8-27B quantizations benchmarked](https://quesma.com/blog/qwen38-27b-quantizations-benchmarked/).

## Qué aporta el informe externo

Quesma comparó Q8_0, Q4_K_M, UD-Q2_K_XL y UD-IQ1_S contra BF16 en GPQA
Diamond, IFBench y Terminal-Bench 2.1. En esas tareas, y con el contexto y
presupuesto de razonamiento de su experimento, Q4_K_M quedó muy cerca de BF16;
Q2 conservó utilidad con una pérdida medible; e IQ1, aproximadamente 1 bit,
se degradó hasta resultados cercanos al azar. El resultado no demuestra que
cualquier Q4 sea idéntico en un agente, pero sí fija un límite práctico: no
conviene sacrificar calidad de tool-use para ganar unos pocos GB usando Q1.

El estudio usó KV F16 para sus comparaciones. Eso sirve para aislar el efecto
de los pesos, pero no es una receta admisible para el perfil promovido de
LlamaCode: nuestra política limita también el KV a Q8.

## Cruce con nuestras mediciones

| Variante local | Evidencia disponible | Lectura |
|---|---|---|
| **SOL** · Qwen3.8-27B AutoRound INT4, TP2/P2P, MTP4, KV FP8 | 74 tok/s narrativo, 102 tok/s código, BCB 8/8, tool-use OK y 262K validado | Sigue siendo la mejor combinación validada de calidad, velocidad y contexto. |
| Qwen3.8-27B GGUF Q4_K_M + MTP | Aproximadamente 73,75 tok/s en la campaña local; el perfil Q4_K_M mantiene variantes de 131K y visión | Confirma que 4 bits es un punto razonable, pero no supera la huella actual de SOL. |
| QWEN38-Q8 | 41,3 tok/s a 8K y 22,1 tok/s a 262K en la medición local | Aporta fidelidad/contexto, no una mejora de velocidad ni una validación de agente superior a SOL. |
| UD-Q2 / IQ1 | Q2 local quedó como variante experimental; no hay evidencia de que IQ1 sea utilizable | No promover. IQ1 contradice directamente el requisito de calidad mínima para loops y tools. |
| MINI · MiniCPM5-2B Q4 | 248,90 tok/s, pero BCB 1/8 | Sigue siendo mejor auxiliar rápido que un Qwen extremo de 1 bit. |

Las cifras de la fila GGUF provienen de la comparación local documentada en
[qwen38-27b-vs-flash-next-2026-09-06.md](qwen38-27b-vs-flash-next-2026-09-06.md).
Las cifras actuales de SOL y QWEN38-Q8 se mantienen en la matriz de perfiles y
en los artefactos de benchmark del repositorio.

## Presupuesto de razonamiento y muestreo

El informe también confirma que el presupuesto de razonamiento puede cambiar
mucho el resultado más que una diferencia pequeña entre Q4 y Q8. Para Qwen de
coding, LlamaCode ya conserva el muestreo conservador (`temp 0.6`, `top-p 0.95`,
`top-k 20`, `min-p 0`, penalizaciones neutras) y las variantes de razonamiento
separadas. No se cambia ese default ni se convierte un benchmark de contexto en
una afirmación de calidad agéntica.

## Decisión para LlamaCode

1. **SOL permanece como default y perfil prioritario.** El informe externo
   respalda el uso de una cuantización alrededor de 4 bits, pero no supera la
   validación local de SOL.
2. **No se agrega Q1/IQ1.** La pérdida esperada es incompatible con BCB,
   tool-use y loops autónomos.
3. **No se reemplaza SOL por QWEN38-Q8.** El Q8 local es más lento y todavía no
   tiene una validación BCB superior.
4. **No se usa F16/BF16 KV como default.** Aunque el estudio externo lo emplea
   como control, excede la política máxima Q8 de LlamaCode.
5. **No se modifica el dropdown ni los perfiles operativos.** El resultado es
   una confirmación de la matriz existente, no una nueva variante superior.

## Resultado

No hubo una implementación de código ni descargas: los artefactos necesarios ya
están en `/media/cristian/7CFE1E0FFE1DC1F6/models`. La tabla vigente queda sin
cambios; la recomendación sigue siendo **SOL** para coding/agentes, **QWEN38-Q8**
cuando se prioriza fidelidad/contexto, y **MINI** para subagentes rápidos.
