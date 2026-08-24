# Tabla final de benchmarks y recomendaciones

Fecha de corte: 2026-08-24.

Este documento consolida los resultados persistidos disponibles. Los benchmarks
están pausados actualmente: la instrumentación de memoria fue corregida y pasó
69/69 pruebas, pero todavía no se ejecutó una nueva campaña completa después de
ese cambio. Por eso no presento como nuevos resultados las corridas inválidas
por infraestructura.

El catálogo actual contiene **23 perfiles con `benchmark=true`**: 5 de sistema
y 18 de usuario. El número anterior de 51 correspondía a una fotografía
histórica del catálogo y no es el total vigente.

## Cómo leer la tabla

- HE0, HE20 y BCB son los scores de cada etapa; BCB se expresa sobre 8 casos.
- `TPS BCB` es la velocidad media de la etapa BCB, no la velocidad de cola ni
  la de un prefijo repetido.
- `Tiempos HE0 / HE20 / BCB` son tiempos de etapa en segundos. Cuando se usa
  un tiempo E2E consolidado de una tabla de candidatos, se indica explícitamente.
- `*` significa que el score apareció en una corrida con evidencia de
  infraestructura posterior o mezcla de intentos; no se usa para promover un
  perfil.
- Las filas con `—` no deben leerse como calidad cero: no tienen una medición
  BCB comparable y necesitan reintento.

## Todos los perfiles activos

| # | Perfil | GGUF / familia | HE0 | HE20 | BCB | TPS BCB | Tiempos HE0 / HE20 / BCB (s) | Estado consolidado |
|---:|---|---|---:|---:|---:|---:|---:|---|
| 1 | ULTRA-Q DeepSeek V4 Flash IQ3_S 131k, sin DSpark | DeepSeek V4 Flash UD-IQ3_S | 1/1 | 20/20 | 8/8 | 9,65 | 216,2 / 1.557,8 / 2.830,6 | Único DeepSeek con BCB completo válido; muy lento |
| 2 | DeepSeek V4-7-8-26, sin speculative | DeepSeek V4 | 1/1 | 19/20 | — | — | 138,7 / 1.597,1 / — | HE20 parcial; BCB no comparable |
| 3 | Laguna S 2.1 CUDA safe 64k | Laguna S Q2_K_XL | 1/1 | 20/20 | — | — | 194,9 / 1.069,5 / — | BCB pendiente/bloqueado por timeout |
| 4 | Qwen3.8 Q4_K_M 131k | Qwen3.8-27B Q4_K_M | 1/1 | 20/20 | 5/8 | 53,83 | 27,3 / 265,3 / 603,4 | Calidad parcial; candidato 24 GB |
| 5 | Qwen3.8 Q5_K_M 131k | Qwen3.8-27B Q5_K_M | 1/1 | 20/20 | 3/8 | 47,13 | 28,3 / 314,5 / 293,0 | Calidad parcial; más pesado que Q4 |
| 6 | KAT Coder Q4 | KAT Coder | 1/1 | 20/20 | 3/8 | 111,77 | 40,1 / 250,2 / 639,3 | Rápido, pero BCB inestable en reintentos |
| 7 | BigBang MTP, perfil activo | BigBang | 1/1 | 20/20 | 4/8 | 39,35 | 48,7 / 267,2 / 252,1 | Calidad parcial; no confundir con METEOR reparado |
| 8 | ThinkingCap Qwen3.6 MTP4 | Qwen3.6-27B | 1/1 | 20/20 | 6/8 | 56,84 | 27,9 / 228,8 / 298,8 | Candidato LUNA; baja latencia |
| 9 | Laguna S fit 100k, agent máximo | Laguna S Q2_K_XL | 1/1 | 20/20 | 0/8 | 22,14 | 130,1 / 488,8 / 241,8 | Calidad insuficiente; no recomendar |
| 10 | DeepSeek Fusion leloch | DeepSeek Fusion | 1/1 | 20/20 | 4/8* | 8,57–9,45 | 180,5 / 1.175,7 / 1.396,9–7.169* | Parcial y muy lento; requiere reparación |
| 11 | DeepSeek Fusion leloch, VRAM balance | DeepSeek Fusion | 1/1 | 20/20 | 2/8 | 9,45 | 135,4 / 1.249,7 / 6.328,8 | Experimental; no promocionar |
| 12 | DeepSeek Fusion, expertos 0–2 | DeepSeek Fusion | 1/1 | 20/20 | 3/8 | 8,71 | 163,2 / 1.225,4 / 1.263,9 | Experimental; reparto de expertos costoso |
| 13 | Laguna S CUDA safe 65k | Laguna S Q2_K_XL | 1/1 | 20/20 | 4/8 | 50,54 | 52,4 / 231,1 / 911,1 | Calidad parcial |
| 14 | Laguna S fit 100k | Laguna S Q2_K_XL | 1/1 | 20/20 | 0/8 | 0,21 | 123,1 / 658,9 / 66,5 | Calidad insuficiente |
| 15 | Laguna S dual GPU safe 32k | Laguna S Q2_K_XL | 1/1 | 20/20 | 4/8 | 44,33 | 52,1 / 663,4 / 871,6 | Calidad parcial; contexto largo experimental |
| 16 | Qwen3.8 MTP separado 131k | Qwen3.8 UD-Q4_K_XL | 1/1 | 20/20 | 8/8 | 55,17 | 30,0 / 259,5 / 365,9 | Uno de los mejores controles limpios |
| 17 | Qwen3.8 KV Q8 MTP2 131k | Qwen3.8 UD-Q4_K_XL | 1/1 | 20/20 | 4/8 | 46,07 | 24,9 / 267,6 / 278,4 | KV Q8 no compensó en esta configuración |
| 18 | Qwen3.8 Browser Agent medium 131k | Qwen3.8 UD-Q4_K_XL | 1/1 | 20/20 | 8/8 | 71,51 | 53,3 / 211,3 / 369,1 | Candidato TERRA; E2E aceptado 592,5 s |
| 19 | Qwen3.8 Browser Agent xhigh 131k | Qwen3.8 UD-Q4_K_XL | 1/1 | 20/20 | 8/8 | 65,94 | 36,5 / 212,1 / 513,1 | Alta calidad de harness; más lento que medium |
| 20 | Qwen3.8 DSH medium 160k MTP2 | Qwen3.8 UD-Q4_K_XL | 1/1 | 20/20 | 8/8 | 54,74 | 13,3 / 215,1 / 661,7 | Candidato SOL; E2E aceptado 890,1 s |
| 21 | Qwen3.8 DSH medium 192k MTP2 | Qwen3.8 UD-Q4_K_XL | 1/1 | 20/20 | 8/8 | 55,11 | 14,0 / 227,1 / 403,6 | Máxima calidad/contexto; E2E documentado 644,7 s |
| 22 | Qwen3.8 MTP embebido 131k | Qwen3.8 UD-Q4_K_XL | 1/1 | 20/20 | 7/8 | 49,67 | 29,1 / 266,4 / 646,0 | Casi completo; inferior al MTP separado |
| 23 | Qwen3.8 MTP embebido 64k | Qwen3.8 UD-Q4_K_XL | 1/1 | 20/20 | 8/8 | 52,58 | 26,6 / 468,5 / 625,5 | BCB completo; contexto más corto |

## Recomendación principal: SOL, TERRA, LUNA y METEOR

Estas etiquetas son decisiones de producto, no sólo un ranking por TPS. Pesan
calidad BCB, tiempo total, estabilidad, contexto y el tipo de trabajo.

| Tier | Perfil recomendado | Calidad BCB | Velocidad | Tiempo total medido | Mi opinión |
|---|---|---:|---:|---:|---|
| SOL | Dynamic V3 DSH medium · 160k · MTP2 | 8/8 | 54,74 tok/s | 890,1 s E2E | Mejor opción para calidad, contexto largo y tareas difíciles. |
| TERRA | Dynamic V3 Browser Agent medium · 131k | 8/8 | 71,51 tok/s | 592,5 s E2E | Mejor equilibrio general para uso diario, agentes y coding. |
| LUNA | ThinkingCap Qwen3.6 · MTP4 | 6/8 | 56,84 tok/s | 298,8 s E2E | Menor tiempo total; bueno para interacción rápida, aceptando menor calidad. |
| METEOR | BigBang MTP reparado | 3/8 | 211,18 tok/s | 670,8 s E2E | Máximo throughput; no lo usaría como modelo principal por su calidad parcial. |

### Mi orden de preferencia

1. **TERRA** como perfil por defecto: mantiene 8/8 y entrega la mejor
   combinación de velocidad y tiempo total.
2. **SOL** cuando importan más la profundidad, el contexto y la robustez que
   la latencia.
3. **LUNA** para respuestas interactivas y tareas donde 6/8 sea suficiente.
4. **METEOR** únicamente para lotes o generación masiva donde el throughput
   justifique sacrificar calidad.

## Perfiles recomendados por caso de uso

| Caso de uso | Recomendación | Motivo |
|---|---|---|
| Agente general con máxima calidad | SOL · DSH medium 160k MTP2 | 8/8 y contexto amplio; prioriza calidad. |
| Uso diario balanceado | TERRA · Browser Agent medium 131k | 8/8, 71,51 tok/s y tiempo E2E razonable. |
| Documentos muy largos | SOL · DSH medium 192k MTP2 | 192k manteniendo 8/8 y 55,11 tok/s. |
| Razonamiento con baja latencia | LUNA · ThinkingCap MTP4 | 298,8 s E2E y 6/8. |
| Máximo throughput o lotes | METEOR · BigBang reparado | 211,18 tok/s; calidad sólo parcial. |
| Navegación y uso de herramientas | TERRA · Browser Agent medium | Harness validado con 8/8. |
| Coding rápido | Qwen3.8 MTP separado 131k | 8/8 y 55,17 tok/s; más confiable que KAT en BCB. |
| Coding con razonamiento fuerte | Browser Agent xhigh 131k | 8/8 y mayor nivel de thinking, con penalización de tiempo. |
| Visión en 48 GB | Qwen3.8 UD-Q4 196k · MTP2 · KV Q8 · mmproj RAM | 8/8, 43,71 tok/s y 941,9 s E2E; especializado. |
| DeepSeek local | DeepSeek V4 Flash IQ3_S sin DSpark | Es el único DeepSeek con 8/8 BCB completo, pero 9,65 tok/s lo deja como experimental. |

## DeepSeek: conclusión

No todos los GGUF DeepSeek funcionan igual. El **IQ3_S sin DSpark** sí tiene
una corrida BCB completa y válida, pero es demasiado lento para SOL/TERRA/LUNA.
Los perfiles Fusion/antirez conservaron HE0 y HE20 en varias configuraciones,
pero BCB quedó parcial, muy lento o afectado por timeout/infraestructura. No
corresponde convertir esos fallos en calidad cero ni retirarlos definitivamente;
corresponde reintentarlos con la cola serial y la nueva planificación fit-aware.

## Familias retiradas o no promocionadas

| Familia | Decisión | Motivo |
|---|---|---|
| KAT APEX-MTP | Fuera de la cola activa | Experimental; falta HE0 validado en este checkout. |
| Dynamic V3 DFlash2 local | Fuera de la cola activa | El loader falla por incompatibilidad de arquitectura/backend (`wrong number of tensors`, `FGDN_AR`). |
| Dynamic V3 DFlash2 vLLM | No local en Windows | Requiere endpoint vLLM parcheado y drafter externo; no es comparable en este entorno. |
| BigBang base / fast | No promocionados | Fallos históricos de HE0, CUDA o estancamiento; sólo se conserva el control reparado. |
| DeepSeek antirez B2048 | No promocionado | BCB terminó en `0/0` por timeout; se conserva como control para reintento. |
| DeepSeek Q3 / IQ3_S con DSpark | No promocionado | La ruta DSpark no es estable en llama.cpp/Windows; se conserva IQ3_S sin DSpark. |
| Variantes DeepSeek de reparto de expertos | No promocionadas | OOM, crashes o BCB incompleto; no hay ganancia evaluable que justifique promoverlas. |

## Próximo paso para una tabla definitiva post-corrección

La tabla anterior es la mejor consolidación de lo que ya se midió. Para
convertirla en una tabla final post-corrección, hay que reanudar la cola de a
un perfil, ejecutar HE0 → HE20 → BCB, registrar la telemetría fit-aware de
VRAM/RAM y repetir sólo los casos con timeout, estado de turno o backend
inestable. Hasta entonces, los números de SOL/TERRA/LUNA/METEOR son los
candidatos consolidados existentes y no una nueva campaña posterior al parche.
