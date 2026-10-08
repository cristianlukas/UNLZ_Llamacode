# Retiro de perfiles reemplazados — 2026-09-15

Se retiraron por decisión del usuario los tres modelos que no se usarán frente
a SOL:

| Perfil | Ubicación original | Tamaño aproximado | Acción |
|---|---|---:|---|
| ASTRA IQ1_S | `/media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.8-Flash-Next-IQ1_S` | 73 GB | Movido a la Papelera del volumen |
| DEEPSEEK FUSION | `/media/cristian/Disco local/Models/llamacpp/DeepSeek-V4-antirez-Q2Q4-imatrix-0731` | 91 GB | Movido a la Papelera del volumen |
| GALACTA | `/media/cristian/Disco local/Models/llamacpp/DeepSeek-V4-Flash-0731-UD-IQ3_S` | 109 GB | Movido a la Papelera del volumen |

Liberación aproximada: **273 GB**. No se usó `rm`; los directorios quedaron en
`.Trash-1000/files/` de cada partición y son recuperables mientras no se vacíe
la Papelera.

Los lanzamientos activos `ASTRA`, `DEEPSEEK FUSION` y `GALACTA` fueron marcados
como `deprecated`, sin `best` ni favorito, para que no aparezcan en los
selectores operativos. Se conservaron los registros históricos de benchmarks y
la documentación para no perder trazabilidad.

**SOL** permanece como perfil principal y no fue modificado.

## Segunda tanda: perfiles retirados frente a SOL

También se retiraron estos perfiles y sus artefactos locales:

| Perfil | Ubicación original | Tamaño aproximado | Acción |
|---|---|---:|---|
| NINFER-QWEN38 | `/media/cristian/Disco local/Models/llamacpp/NInfer-Qwen3.8-27B` | 17 GB | Movido a la Papelera del volumen |
| QWEN38-Q8 | `/media/cristian/Disco local/Models/llamacpp/club-3090/qwen3.8-27b-gguf/unsloth-q8kxl` | 30 GB | Movido a la Papelera del volumen |
| TERRA | `/media/cristian/Disco local/Models/llamacpp/ThinkingCap-Qwen3.6-27B-GGUF` | 17 GB | Movido a la Papelera del volumen |

Liberación adicional aproximada: **64 GB**; acumulada con la primera tanda:
**337 GB**. Los tres directorios siguen siendo recuperables desde
`.Trash-1000/files/` mientras no se vacíe la Papelera.

Los lanzamientos `TERRA` y `QWEN38-Q8` fueron marcados como `deprecated`, sin
`best` ni favorito. Se eliminó del catálogo operativo el perfil de sistema
específico de NInfer Qwen3.8. Los registros históricos restantes se conservan
únicamente para trazabilidad y no se ofrecen como perfiles activos.

**SOL** continúa como perfil predeterminado.

## Tercera tanda: ASTRA Q2_K_XL — 2026-09-24

Después de la comparación agentiva contra SOL, se retiró de forma recuperable la
copia física de ASTRA que correspondía al perfil
`sys-bench-48-qwen38-flash-next-q2kxl-long-256k-balanced-moe12`:

| Perfil | Ubicación original | Tamaño aproximado | Acción |
|---|---|---:|---|
| ASTRA — Qwen3.8 Flash-Next UD-Q2_K_XL | `/media/cristian/Disco local/.llamacode-staging/Qwen3.8-Flash-Next-UD-Q2_K_XL` | 74 GiB, tres shards GGUF | Movido a la Papelera del volumen |

Se conservaron el perfil técnico, los benchmarks, la suite adversarial y los
informes históricos. La carpeta quedó en
`/media/cristian/Disco local/.Trash-1000/files/Qwen3.8-Flash-Next-UD-Q2_K_XL`
y puede restaurarse mientras no se vacíe la Papelera. SOL permanece como modelo
principal.
