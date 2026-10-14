# Plan — Q-20261010-QWEN38-27B-OVERTHINKING

**Estado:** completa como auditoría documental; sin inferencia local.
**Inicio:** 2026-10-13T16:45:00Z.
**Lock:** token `cf548af5-73f7-4ba4-ac2f-3e52710458ff`, host 3090.

## Pregunta

¿Las ideas del post r/LocalLLaMA “Qwen3.8-27b appreciation moment” sobre
UD-Q3_K_XL/Q2_K_XL, scripts de diagnóstico, loops/overthinking y sampling
aportan una prueba o ajuste útil para los perfiles/harness de LlamaCode?

## Candidatos, controles y huellas existentes

- Candidatos reportados: Qwen3.8-27B UD-Q3_K_XL y UD-Q2_K_XL, sujetos a
  verificar el post, pesos, configuración y disponibilidad local.
- Controles posibles: ASTRA IQ3_S calibrado/Strata, SOL Qwen3.8-27B
  AutoRound INT4/vLLM y Flash-Next UD-Q4_K_XL/Strata. Antes de medir, comparar
  fingerprints con `docs/evaluacion-modelos-llamacode.md` y campañas previas;
  no repetir un par/fingerprint ya puntuado salvo hipótesis nueva explícita.
- Reutilizar los resultados históricos Hard Mode 28×3, HE/BCB/ADV/TaskFlow y
  evaluar qué evidencia ya responde a cada claim. Perfiles completos distintos
  se reportan como tales.

## Alcance y recursos

- Verificar la fuente comunitaria y contrastar claims técnicos con fuentes
  primarias del modelo, runtime y scripts enlazados.
- Inspeccionar configuración local, hashes/modelos presentes y artefactos
  existentes; no descargar ni modificar perfiles productivos en el preflight.
- Si una prueba local nueva está justificada por una hipótesis no cubierta,
  preregistrar suite, prompts, semillas, presupuesto, verificador y fingerprint.
  Mantener cada corrida por debajo del corte práctico de 30 minutos indicado
  por el usuario; ejecutar en serie si comparte GPU.
- GPU disponible prevista: 2×RTX 3090, sujeta a inspección de carga y memoria.
  Cualquier servidor de prueba será aislado y se apagará al cierre.
- Usos pertinentes: coding/agentes y conducta de razonamiento/overthinking.
  No inferir Computer Usage, voz, visión ni contexto largo sin pruebas propias.

## Resultado que habilitaría un cambio

Una recomendación de sampling sólo si una suite predefinida muestra una mejora
repetida en respuestas correctas, terminación y tiempo sin regresión importante
ni superar 30 minutos por corrida. La prueba del autor del post no cuenta como
réplica local. No cambiar perfiles/defaults sin evidencia suficiente y
reversión documentada.

## Ejecución prevista

1. Leer fuente compartida, README/cola/documento canónico y evidencia local.
2. Identificar versión, claims, scripts, modelo/quant/runtime y puntos no
   verificables; revisar candidatos y fingerprints locales.
3. Decidir si corresponde prueba local distinta o si el resultado correcto es
   cerrar como auditoría documental sin repetir fingerprints.
4. Guardar fuentes, recibos, límites, conclusión y fingerprint; actualizar el
   documento canónico y cerrar esta fila FIFO.

## Cierre

- El post y los comentarios se verificaron contra la tarjeta oficial de Qwen,
  el repositorio GGUF de Unsloth y la ficha del quant local de Agention.
- No se encontró localmente el UD-Q3_K_XL ni UD-Q2_K_XL exacto del post. El
  AP-Q3_K_XL local tiene calibración/encoding distintos, por lo que probarlo no
  replicaría el claim. GPU0 tenía activo el escritorio/ArtCraft y GPU1 mostró
  58% de uso sin una reserva exclusiva confirmada.
- No hubo descarga, inferencia ni cambio productivo. Se cierra como auditoría
  documental; confianza baja para cualquier conclusión de calidad o
  overthinking.
- Próxima acción útil: si el usuario quiere una prueba de terminación, fijar
  prompts y verificador independientes y probar una configuración por vez,
  siempre con límite menor a 30 minutos por corrida. No descargar otro quant
  antes de confirmar compatibilidad, espacio, revisión y hashes.
- Informe y recibo de fuentes/preflight: RESULTS.md y
  receipts/source-review.json.
