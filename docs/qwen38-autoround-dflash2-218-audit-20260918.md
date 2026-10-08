# Qwen3.8 AutoRound INT4 + DFlash2 — auditoría del resultado 218 tok/s

## Veredicto

El resultado es técnicamente plausible y merece una prueba local prioritaria,
pero no reemplaza todavía a **SOL**. Es una variante distinta de la candidata
INT8/W8A16 que ya está documentada: aquí el target es **AutoRound INT4** y el
drafter es DFlash2.

La ganancia publicada es muy atractiva para una sesión corta o media:

| Medición publicada | Resultado |
| --- | ---: |
| Decode narrativo | 120,1 tok/s |
| Decode código | **218,3 tok/s** |
| Wall TPS código | 204,8 tok/s |
| Prefill a 10K / 90K | 1.342 / 628 tok/s |
| DFlash2 | 7 tokens; aceptación 47,8%; longitud 3,35 |
| VRAM | 22,3 GB por RTX 3090 |
| Contexto | **131K**, no 262K |

La receta usa vLLM `0.26.1rc1`, AutoRound INT4 grupo 128, TP=2, P2P
parcheado y cambios locales de vLLM. La fuente es un benchmark externo de
2× RTX 3090 sin NVLink, no una medición de LlamaCode.

## Comparación con SOL

| Perfil | Decode publicado/local | Calidad | Contexto | Estado |
| --- | ---: | --- | --- | --- |
| **SOL** | 74 narrativo / **102 código** | BCB 8/8, tool-use estable | **262K validado** | Default local |
| AutoRound INT4 + DFlash2 | 120,1 / **218,3** | BCB8, HE20, visión y tool-use: pendientes | **131K** | Candidato fuerte |
| INT8 W8A16 + DFlash2 | 102–117 publicados | BCB8, HE20, visión y tool-use: pendientes | 262K configurado | Candidato externo separado |

El número 218 no debe interpretarse como una mejora universal: compra casi
2,1× de decode en código a cambio de reducir aproximadamente a la mitad el
techo de contexto de SOL. Además, el benchmark mide la suite canónica del
autor, no nuestro BCB8 con harness, ni sesiones multi-turno con herramientas.

## Riesgos que aparecieron al revisar vLLM

- Hay un reporte reproducible donde DFlash2 cambia la salida greedy de Qwen3.8
  durante el razonamiento, incluso con `K=1` y `--enforce-eager`; target-only y
  DFlash2 divergen en el token 30. Es un problema de corrección, no sólo de
  sampling.
- Hay otro reporte donde DFlash2 interactúa mal con xgrammar/JSON: la respuesta
  termina siendo HTTP 200 y JSON válido, pero la FSM entra en reintentos y
  llena el log de errores. Esto afecta directamente tool-use estructurado.
- En Ampere se reportan problemas específicos de cuantización del drafter:
  `hf_overrides` callable, empaquetado Marlin con `K=0` y necesidad de una ruta
  W8A16/DFlash INT8 compatible con `torch.compile`.
- También existe un fallo de regresión donde una revisión de vLLM deja de
  construir `DFlash2Qwen3DecoderLayer`; el arreglo es pequeño, pero obliga a
  fijar commit y parche exactos.
- DFlash2 puede reprocesar el contexto completo en respuestas posteriores,
  mientras MTP conserva el estado. Para un agente multi-turno esto puede
  anular parte de la ganancia de decode.

## Qué pude verificar localmente

El target AutoRound INT4 ya está completo y coincide con el modelo de SOL:

```text
/media/cristian/7CFE1E0FFE1DC1F6/models/club-3090/qwen3.8-27b-autoround-int4
```

Tiene los 7 shards safetensors y ocupa aproximadamente 18 GB. La prueba local
posterior descargó el drafter W4A16 compatible en el Disco D y aplicó el
backport DFlash2 sobre la imagen vLLM 0.27.1. Los resultados reproducidos,
incluyendo el control sin drafter, están en
[`docs/sol-dflash2-local-audit-20260918.md`](sol-dflash2-local-audit-20260918.md).
El GGUF Q2 existente sigue siendo una ruta distinta y no se intercambia con
esta receta.

La descarga del target INT8/W8A16 alternativo quedó incompleta y fue movida de
forma recuperable a `Disco local/.llamacode-staging`; no se usa en ningún
perfil activo.

## Matriz necesaria antes de promoverlo

1. Usar el mismo target AutoRound de SOL y fijar la revisión exacta de vLLM y
   los parches DFlash2.
2. Comparar autoregresivo, MTP4 y DFlash2 con el mismo prompt, sampling y
   `TP=2/P2P`.
3. Medir 8K, 32K, 90K y 131K con PP, TG, wall TPS, TTFT, VRAM y aceptación.
4. Ejecutar HE0, HE20 y BCB8 con harness, además de tool-use, JSON estricto y
   una sesión multi-turno con prefijo repetido.
5. Probar visión sólo después de que el camino textual sea correcto.
6. Verificar greedy-equivalence contra SOL sin thinking y con thinking; si
   diverge, dejar DFlash2 como acelerador experimental y no como default.

## Decisión de perfil

No se cambia SOL, su dropdown ni sus flags. El resultado se registra como
**candidato `SOL-DFlash2-131K`**, con prioridad alta para una futura campaña
cuando haya espacio para el drafter y un entorno vLLM reproducible. La
promoción exigiría superar a SOL en TG en tareas reales sin perder BCB8,
tool-use ni la garantía de 262K.
