# Inventario físico y matriz de modelos — 2026-09-18

Inventario confirmado en las particiones C (`7CFE1E0FFE1DC1F6`), D (`Disco
local`) y `HDD extra`. Las métricas se toman de las auditorías locales más
recientes; no se mezclan cifras externas con BCB/HE locales. Un modelo que no
tiene una métrica aplicable aparece como `N/A`, no como cero. **Corte: 2026-09-24.**

## Modelos LLM y multimodales presentes en C/D

| Modelo / perfil | Ubicación y tamaño | PP/TG local | Calidad / estabilidad | Contexto | Visión | Estado |
|---|---|---:|---|---:|---|---|
| **SOL — Qwen3.8-27B AutoRound INT4** | D: `Models/llamacpp/club-3090`; ~18 GB. La copia de C se retiró a la papelera por duplicada. | 74 narrativo / **102 código TG** | **BCB 8/8**, HE20 20/20, tool-use estable | **262K validado** | 4/4 | Default principal |
| **ASTRA — Qwen3.8 Flash-Next UD-Q2_K_XL** | **Sin pesos activos; 74 GiB en la Papelera de D** | **47,14 TG @256K; 53,68 @128K. BCB directo ~30,3 TG** (`n-cpu-moe 40`) | **LC-H1 exacto:** HE0 1/1; HE20 20/20; BCB 8/8; 87 tool calls, 86 exitosos. BCB directo histórico separado | **256K cargable; needle/passkey 4/4 al 25/50/75/95%** | No validada | **Retirado el 2026-09-24; conservar documentación y benchmarks** |
| **QWEN35-A3B — AutoRound INT4** | D: `Models/llamacpp/club-3090/qwen3.6-35b-a3b-autoround-int4`; ~21,5 GB | 123,98 BCB / 134,4 directo TG | BCB **4/8 histórico; 1/8 directo**; HE0 1/1; HE20 histórico 20/20 | 262K | **4/4** | Experimental multimodal/concurrente |
| **OCCAMY 1.0 Q4_K_M** | C: `models/Occamy-1.0-Q4_K_M`; ~21,2 GB + mmproj | 233 PP / 164 TG @8K; 132 PP / 163 TG @262K; BCB 143,6 TG | HE0 1/1; HE20 20/20; **BCB 3/8**; tool-call válido | **262K estable** | 175,7 PP / 162,7 TG @32K | Experimental multimodal |
| **QWEN38-SHAPELEARN IQ4_XS** | C: `models/Qwen3.8-27B-ByteShape-IQ4_XS`; ~13,1 GB + mmproj | 156,8/25,9 sin MTP; 180,7/**53,6** @8K; 108/**66,2** @262K; 77,9 TG HE20 | HE0 1/1; HE20 **20/20**; BCB bloqueado por salida excesiva previa a tools | **262K estable** | 163,5/55,9 @32K; MTP3 funcional | Experimental contexto/fidelidad |
| **METEOR / BigBang-v1 Q4_K_M** | D: `Models/llamacpp/BigBang-v1-Q4_K_M-GGUF`; ~22,8 GB + mmproj | **207 texto / 195,3 visión TG** | BCB **3/8 histórico; 2/8 directo**; HE0 1/1 | 64K | Funcional en smoke | Throughput/lotes |
| **QWEN38-Q8** | No quedan pesos activos; sólo referencias históricas en el catálogo | 41,3 @8K / **22,1 @262K** | BCB directo histórico 8/8; agente LC-H1 no validado | 262K | No validada | Retirado; conservar sólo documentación |
| **TERRA / ThinkingCap** | No quedan pesos activos; sólo referencias históricas | 56–58 TG | BCB histórico 6/8 | 64K | Smoke funcional | Retirado; conservar sólo documentación |
| **GSQ-RCO IQ3_S + DFlash2 Q2** | C: `models/Qwen3.8-27B-GSQ-RCO-IQ3_S`; ~12,1 GB + mmproj + drafter 536 MB | 67,7 TG corto; 25,0 @8K; visión 52,1 TG; HE0 29,1 TG | HE0 **1/1**; HE20 cancelado en 5/20 por latencia; BCB no iniciado | 81,9K configurado; 9,6K probado | Funcional | Experimental DFlash2 |
| **Qwen3.6-35B-A3B GGUF MTP** | D: `Models/llamacpp/Qwen3.6-35B-A3B-MTP`; ~23,7 GB + mmproj | 140,2 TG base / **207,8 TG con MTP** | Calidad agentiva comparable no cerrada; MTP+visión no compatible de forma estable | Inferior a la ruta AutoRound | Visión sin MTP funcional | Variante legacy; no confundir con QWEN35-A3B AutoRound |
| **Qwen3.5-9B MTP** | D: `Models/llamacpp/Qwen3.5-9B/MTP`; ~5,9 GB + mmproj; existe copia base ~5,7 GB | 166,1 texto / 144,2 visión TG | BCB **1/8 directo**; HE0 1/1; HE20 19/20 | 8K probado | Funcional | Auxiliar potente; parcialmente superado para el rol auxiliar medido, pero no reemplazable por Occamy por tamaño |
| **Qwen3.5-4B MTP** | D: `Models/llamacpp/Qwen3.5-4B`; ~2,8 GB + mmproj | 200 texto / **206,6 visión TG** | BCB **1/8 directo**; HE0 1/1; HE20 20/20; reparación no convergente | 8K probado | Funcional | Auxiliar equilibrado |
| **Qwen3.5-2B MTP** | D: `Models/llamacpp/Qwen3.5-2B`; ~1,3 GB + mmproj | **318,9 / 344,8 visión TG** | BCB **0/8 directo**; HE0 0/1 | 8K probado | Funcional | Auxiliar rápido, no agente confiable |

## Componentes de IA auxiliares presentes en C

| Componente | Ubicación / tamaño | Métricas reproducibles | Uso y estado |
|---|---|---|---|
| **Laya 421M** | C: `models/Laya-421M`; ~808 MB | Routing GPU warm **13–15 ms**; coding 0,982; prompt injection 1,0; triage 0,995 | Sidecar de routing/guardrails; no genera código ni tiene BCB |
| **Qwen3 TTS Base Q8** | C: `models/audio-cpp/Qwen3-TTS-12Hz-0.6B-Base-GGUF`; 1,99 GB | Servidor residente RTF **0,18–0,23**; clonación funcional | TTS experimental para Charla |
| **Qwen3 ASR Q8** | C: `models/audio-cpp/Qwen3-ASR-0.6B-GGUF`; 1,15 GB | Servidor residente RTF **0,021–0,024**; 2/2 muestras exactas en inglés | STT experimental; falta corpus español |
| **Parakeet TDT 0.6B Q8** | C: `models/audio-cpp/Parakeet-TDT-0.6B-v3-GGUF`; 916 MB | Servidor residente RTF **0,0028–0,0031**; 2/2 muestras exactas en inglés | STT de baja latencia; falta WER español |
| **Pocket TTS español Q8** | C: `models/audio-cpp/PocketTTS-GGUF/spanish`; 128 MB | RTF caliente **0,017–0,019** con referencia WAV | TTS español experimental; embedding `alba` incompleto |

## Artefactos incompletos o no evaluables

| Artefacto | Ubicación / peso | Resultado |
|---|---:|---|
| **Qwen3.8 INT8 W8A16 + DFlash2 parcial** | D `.llamacode-staging`; **~27 GB** | Sólo existen 5 de 6 shards; no se puede cargar ni medir |
| **DFlash2 Q2** | C; 536 MB | Drafter, no modelo independiente; sólo válido en GSQ-RCO |
| **Vocabularios `ggml-vocab-*` dentro de builds** | D; megabytes por copia | Tokenizadores auxiliares, no modelos independientes |

## HDD extra

No se detectaron modelos AI reconocibles (`GGUF`, `safetensors`, `NInfer`,
`ONNX`, `PT` o `PTH`) en `/media/cristian/HDD extra/Models` ni en el resto del
HDD. El único `.bin` grande identificado pertenece a una descarga/backup no
identificado (`411-b-l-pa.bin`, ~704 MB) y no se clasificó como modelo de IA.
Por pedido, no se ejecutaron pruebas sobre el HDD; se informa sólo el peso.

## Conclusión operativa

Las velocidades marcadas como `directo`, `smoke`, `BCB` o `visión` pueden
provenir de protocolos distintos y no son comparables automáticamente. Sólo
los resultados **LC-H1** usan el mismo harness agentivo. En particular, los
47,14 TG de ASTRA a 256K, su BCB directo de ~30,3 TG y la campaña LC-H1 son
mediciones separadas; la última sí tiene harness comparable con los demás
resultados LC-H1.

**SOL = Qwen3.8-27B**. La receta DSH medium de 54,74 tok/s es histórica; la
receta actual principal es AutoRound/vLLM TP2/P2P, con 74 narrativo / 102 código.

SOL continúa siendo el único perfil activo que combina BCB8 8/8, tool-use estable,
visión validada y 262K. Occamy es el mejor throughput multimodal experimental;
ShapeLearn es el mejor equilibrio Flash-Next de contexto y fidelidad; Qwen3.5
2B/4B/9B son auxiliares. Occamy los supera para calidad/contexto de agente
principal, pero no los supersede globalmente: 2B y 4B son más rápidos y mucho
más pequeños, y 9B conserva una capacidad intermedia en sólo 5,9 GB. Los
perfiles CyberTiel, Agnes, ASTRA IQ1_S/IQ4_XS, Flash-Next EXL3 y ASTRA Q2_K_XL
fueron retirados a la papelera por quedar dominados operativamente o por salida
no confiable.
La copia activa de SOL quedó centralizada en D
(`/media/cristian/Disco local/Models/llamacpp/club-3090`). El entorno de
`club-3090` y el compose activo `autoround-int4/mtp.yml` montan esa ruta y
sirven el backend en `127.0.0.1:8113`; los historiales de benchmarks conservan
sus rutas antiguas como evidencia histórica.

## Perfiles retirados el 2026-09-19

Se enviaron a la papelera, de forma recuperable, los pesos de CyberTiel,
Agnes-3.0-Flash, ASTRA IQ1_S, ASTRA IQ4_XS y Flash-Next EXL3. No deben
considerarse disponibles para nuevas pruebas salvo que se restauren desde la
papelera.

## Perfil retirado el 2026-09-24

También se envió a la Papelera la copia física de **ASTRA Q2_K_XL** (74 GiB,
tres shards), después de la comparación agentiva SOL vs ASTRA. El resultado
histórico queda preservado; no debe considerarse disponible para nuevas pruebas
salvo restauración explícita desde la Papelera. Ver
[`model-removal-20260915.md`](model-removal-20260915.md) y
[`intelligence-adversarial-v1-results-20260924.md`](intelligence-adversarial-v1-results-20260924.md).
