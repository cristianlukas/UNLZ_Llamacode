# Perfiles LlamaCode por caso de uso — Ubuntu — 2026-09-14

Esta es la clasificación operativa después de corregir los perfiles que no
cargaban. Las estrellas son relativas a esta PC con dos RTX 3090; no son una
nota universal del modelo.

## Política de precisión

- El cuantizado de pesos no supera Q8. Los perfiles actuales usan Q2/Q4/Q5/Q6
  o IQ3/IQ4, todos dentro del límite solicitado.
- El KV cache activo no supera Q8: se usa `q4_0` o `q8_0`.
- ASTRA DEFAULT ahora selecciona ISTA-DASLab Flash-Next IQ2_XS con Strata
  0.1.41, KV int8/resident 32768 y MTP4 a 131K. Hard Mode 28×3: 77,98/100,
  154,19 tok/s de media y 11:05 total. TC-92 filtró otro tenant en las tres
  semillas; no usarlo con datos sensibles ni aislamiento entre tenants. El
  perfil Q2_K_XL balanceado de 256K sigue disponible como benchmark aparte.
- El mmproj BF16 de METEOR es el encoder de visión, no el modelo ni el KV
  cache cuantizado. No se utiliza una cuantización de pesos superior a Q8.

## Matriz operativa consolidada

Esta es la tabla canónica de perfiles para la interfaz y para los informes de
benchmark. El orden prioriza calidad/agencia, contexto, visión y estabilidad;
la velocidad se usa como desempate. “Visión” describe la receta exacta
validada, no sólo que el modelo anuncie capacidad multimodal.

| Puesto | Perfil | Modelo / configuración | Velocidad local | Calidad / agentes | Contexto | Visión | Sub-agentes recomendados | Estado |
|---:|---|---|---|---|---|---|---|---|
| 1 | **SOL** | Qwen3.8-27B AutoRound INT4 · MTP4 · vLLM TP2/P2P · KV FP8 | 74 narr. / 102 código | ★★★★★ · BCB 8/8 | 262K validado | **Sí · 4/4 en vLLM TP2/P2P**; fallback GGUF no validado | Hasta 2×64K o 3×32K | Principal |
| 2 | **GALACTA** | DeepSeek V4 Flash IQ3_S · KV Q4 | 9,65 tok/s | ★★★★★ · BCB 8/8 | 131K | No validada | Hasta 2×64K | Calidad máxima |
| 3 | **DEEPSEEK FUSION** | DeepSeek Fusion IQ3/Q4 · KV Q4 | 10,55 tok/s histórico | ★★★★★ · BCB 8/8 histórico | 131K | No validada | Hasta 2×64K | Alternativo |
| 4 | **QWEN35-A3B** | Qwen3.6-35B-A3B AutoRound INT4 · vLLM TP2/P2P · KV FP8 | 123,98 BCB / 134,4 directo | ★★★☆☆ · BCB 4/8 | 262K validado | **Sí · 4/4 hasta 262K** | Hasta 2×64K o 3×32K | Experimental |
| 5 | **QWEN38-Q8** | Qwen3.8-27B UD-Q8_K_XL · **sin MTP · KV Q8** | **23,3 @8K / 23,2 @262K**; PP 160/144 | ★★★☆☆ · BCB directo 8/8; LC-H1 pendiente | 8K y 262K smoke; **64K/131K abortan** en la build actual | **QWEN38-VISION separado**; no transferir visión a esta ruta | Hasta 2×64K sólo como experimento | Experimental/inestable |
| 6 | **TERRA** | ThinkingCap Qwen3.6-27B Q4 · MTP4 · KV Q8 | 56–58 tok/s | ★★★☆☆ · BCB 6/8 histórico | 64K | **Sí · smoke visual validado; MTP 4/4** | Hasta 2×32–64K | Razonamiento y visión |
| 7 | **ASTRA DEFAULT** | ISTA-DASLab Qwen3.8 Flash-Next GSQ-RCO IQ2_XS · Strata 0.1.41 · MTP4 · KV int8 · 131K | **154,19 tok/s media** en Hard Mode; 11:05 por 28×3 | 77,98/100 en Hard Mode; HE0 1/1, HE20 20/20, BCB 8/8; TaskFlow 13/13 tras 3 reparaciones | 131K evaluado; 256K no probado | No evaluada localmente | No recomendar para subagentes con datos sensibles | **Predeterminado por pedido del usuario; TC-92 fuga cross-tenant 3/3, TC-74 falla 3/3.** |
| 8 | **NINFER-QWEN38** | Qwen3.8-27B `.ninfer` · MTP3 · INT8/Q8 | 73–75 @8K / 50–63 @80–120K | ★★☆☆☆ · BCB 3/8 | 120K probado / 131K operativo | No validada | Hasta 2×64K o 3×32K | Experimental |
| 9 | **METEOR** | BigBang Q4_K_M · MTP histórico / control sin MTP · KV Q8 | **138–148 control; 211,18 histórico MTP** | ★★☆☆☆ · BCB 3/8 | 64K | **1/1 sin MTP**; 61,69 tok/s visual; MTP visual no validado | Hasta 2×32–64K | Throughput y lotes |
| 10 | **LUNA** | Ling 3.0 Tiny Q6 · KV Q8 | **202–206**; PP 397–428 | ★★☆☆☆ · HE0 0/1 histórico | 131K medido | No: modelo text-only | Hasta 2×64K | Perfil rápido; HE0 pendiente |
| 11 | **MINI** | MiniCPM5-2B Q4 · KV Q8 | **230–258**; PP 1.954–2.061 estable | ★★☆☆☆ · BCB 1/8 | 131K medido | No validada | Hasta 2×64K o 3×32K | Auxiliar rápido |

`★` = una estrella; `☆` = una estrella no obtenida. Las cifras históricas no
se presentan como una nueva medición cuando la configuración cambió.

## Orden de lanzamiento en LlamaCode

El menú **LANZAR** usa un orden operativo separado del ranking de calidad:
primero muestra los cuatro perfiles solicitados como acceso directo y después
el resto como perfiles secundarios. El orden persistido es:

**GALACTA → SOL → TERRA → MINI → DEEPSEEK FUSION → QWEN35-A3B → QWEN38-Q8 →
ASTRA → NINFER-QWEN38 → METEOR → LUNA**.

`TERRA-LEGACY` queda fuera del orden prioritario por ser un rollback
deprecated. `QWEN38-VISION` queda después de estos perfiles como variante visual
experimental separada.

## Reparaciones aplicadas y evidencia

- **ASTRA DEFAULT:** ISTA-DASLab Qwen3.8-Flash-Next GSQ-RCO IQ2_XS, Strata
  0.1.41, 131072 tokens, KV int8/resident 32768, MTP4, `spec-min-p 0.70`,
  caché de expertos automática y sampling conservador. Hard Mode v2.8.0
  obtuvo 77,98/100 en 28 tareas × 3 semillas; TPS medio 154,19 (mediana
  153,05) y 11:05 de tiempo total. La suite usa herramientas simuladas.
  **TC-92 filtró datos de otro tenant en 3/3 seeds y TC-74 falló 3/3:** no
  usar este perfil con datos sensibles ni aislamiento multi-tenant. Fue
  seleccionado como default por pedido del usuario; `best=false` se conserva.
- **Flash-Next Q2_K_XL 256K:** sigue como perfil benchmark aparte, no es el
  ASTRA predeterminado. La receta balanceada usa KV Q8/Q8, `n-cpu-moe 12` y
  `tensor-split 1.4,1`; midió 47,14 tok/s con aproximadamente 1,1 GiB libres
  por GPU. A 128K, `n-cpu-moe 8` + `tensor-split 1.22,1` midió 53,68 tok/s.
  La campaña LC-H1 exacta a 256K pasó HE0 1/1, HE20 20/20 y BCB 8/8, con
  87 tool calls (86 exitosos); además pasó needle/passkey 4/4 al
  25/50/75/95%. No se le asigna visión.
- **LUNA:** ahora usa Ling 3.0 Tiny sin duplicar Qwen 28B, B1024/U256, KV
  Q8/Q8, thinking `medium` y presupuesto 2048. El template Bailing V3
  bundleado produjo una llamada estructurada con `finish_reason=tool_calls`,
  nombre de función y argumentos JSON válidos; HE0/BCB debe repetirse para
  certificar la calidad completa del harness.
- **METEOR:** el modelo estaba asociado por error a stable 121, que es Qwen
  3.8-27B Q5_K_M. Se corrigió a stable 116, el BigBang Q4_K_M instalado, y
  mmproj stable 117. Cargó a 64K con MTP5/KV Q8 y respondió por API con
  aceptación MTP 4/5.
- **SOL:** la receta documentada es el endpoint vLLM/AutoRound TP2/P2P de
  `127.0.0.1:8113`, con MTP4, KV FP8 y verificación visual 4/4. El fallback
  GGUF conserva una validación separada y no hereda automáticamente esa
  capacidad multimodal.
- **TERRA:** ThinkingCap ocupa el nivel intermedio por su mejor razonamiento,
  estabilidad y visión; LUNA queda como el escalón de mayor velocidad.
- **TERRA-LEGACY:** el Qwen 28B antiguo queda oculto/deprecated sólo como
  rollback; ya no compite con SOL ni duplica el modelo activo de TERRA.
- **QWEN38-Q8:** se descargó y verificó `Qwen3.8-27B-UD-Q8_K_XL.gguf` en
  `/media/cristian/7CFE1E0FFE1DC1F6/models/club-3090/qwen3.8-27b-gguf/unsloth-q8kxl/`.
  Con MTP2 fue estable a 131K (~48,07 tok/s) y 262K (~43,08 tok/s); MTP3
  quedó por debajo (~44,69 tok/s). El primer intento con 262K y B4096/U512
  agotó memoria, pero B512/U128 cargó y generó sin fallback, corrupción ni
  `device-side assert`. El BCB formal todavía no se ejecutó, por lo que no se
  lo presenta como 8/8.
- **NINFER-QWEN38:** el artefacto actual se rechaza por
  `dflash2/feature_projection`; el histórico compatible se fijó sólo en Linux
  mediante `platformModelFiles`. GPU1 pasó generación, tool-use y 120K de
  contexto con INT8 KV; BCB dio 3/8 con thinking 2048. Windows conserva el
  artefacto y argumentos anteriores.

## Recomendación por uso

- **SOL:** coding y agentes; BCB 8/8, contexto amplio y mejor estabilidad
  global.
- **GALACTA:** calidad máxima validada, con mucha paciencia.
- **QWEN35-A3B:** contexto largo, visión y concurrencia.
- **TERRA:** razonamiento y visión en una ruta local estable.
- **QWEN38-Q8:** fidelidad y techo de 262K; todavía experimental.
- **ASTRA DEFAULT:** ISTA IQ2_XS es la selección rápida para tareas que no
  requieren aislamiento sensible; el 28×3 fue 77,98/100 y tomó 11:05, pero
  TC-92 falló las tres semillas. Usar SOL para tareas con datos sensibles o
  acceso multi-tenant. El perfil Flash-Next Q2_K_XL sigue para contexto 256K.
- **NINFER-QWEN38:** backend experimental de una GPU y contexto largo; no
  usarlo como agente principal por su BCB 3/8.
- **METEOR:** throughput y lotes.
- **LUNA:** interacción rápida y tareas auxiliares de texto; Ling es text-only.
- **MINI:** subagentes, clasificación y tareas auxiliares.

La matriz se refiere a Linux. Las reparaciones específicas quedaron en
`platformArgs.linux`; los argumentos Windows existentes se conservaron.
