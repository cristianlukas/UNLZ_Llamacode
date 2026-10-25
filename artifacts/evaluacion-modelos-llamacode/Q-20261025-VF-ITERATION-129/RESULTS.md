# Q129 · Revisión del guard y compatibilidad NInfer Flash-Next

**Estado: auditoría completada; benchmark NInfer Flash-Next bloqueado por soporte de runtime/plataforma.** No se inició descarga, build, servidor, inferencia ni uso de GPU.

## Veredicto sobre presión de memoria

La evidencia concuerda con el usuario: una RSS/VRAM alta no debe bastar para detener una carga que conserva memoria disponible y no presenta OOM. No encontré una parada falsa de ASTRA DEFAULT 1M o SOL en las pruebas documentadas.

- **ASTRA DEFAULT 1M, carga real Q117:** 1.001.463 tokens, ambas RTX 3090, RSS máx. 51,306 GiB, `MemAvailable` mín. 58,698 GiB, PSI global máx. 53,61%, 0 hard-stops/OOM/swap del worker. Q118 reprodujo la traza AMD05 12/12; Q128 reprodujo el guard histórico Q97 11/11 y tampoco habría cortado por RSS alto.
- **SOL, Q34/Q127:** SOL Q34 completó 30/30 requests con TP=2 en las dos RTX 3090 y sin OOM. Q127 completó una solicitud de 24.319 tokens en esas mismas dos GPU; el pico fue 24.080/23.972 MiB de VRAM, RSS del árbol 12,421 GiB y `MemAvailable` mínima 99,973 GiB, sin abort, OOM ni swap. Esto valida VRAM casi llena y una ejecución SOL correcta; no equivale a una carga de RAM de host cercana a agotarse.
- **Semántica del guard:** RAM ocupada/RSS y VRAM ocupada no son señales de presión sostenida. AMD05 no se basa en RSS y exige presión PSI global severa junto con `MemAvailable <48 GiB` por 15 muestras; conserva el corte inmediato `<32 GiB` y OOM. Q126 pasó 4/4 fronteras CPU-only. AMD05 sigue candidate-only y no está integrado al producto.
- **Limitación real:** Q116 encontró que el guard histórico Q97/Q100 mantiene contadores separados para `full` y `some`; si las señales severas alternan, su OR por muestra no acumula 15 muestras. El helper compuesto candidate-only pasó 5/5 en Q116-A2; AMD05 también superó la alternancia con poco headroom en Q126. Por tanto, el guard histórico no está validado para todos los patrones severos. Esta limitación no contradice los éxitos ASTRA/SOL y no atribuye los cierres de Codex.

La guarda evaluada es un supervisor de workers de pruebas, no un detector general del proceso principal de Codex, la GUI, el driver o cualquier uso del sistema. No cambiar RAM, swap, contexto ni perfiles a partir de estos datos; ASTRA, SOL, Flash-Next productivo y PeritoSoft permanecen intactos.

## Decisión sobre NInfer y el host dual

Las fuentes primarias confirman que v0.16.1 publicó un archivo Linux, pero eso no habilita este test de Flash-Next: el perfil figura como preview de Windows, su forma de serving documentada está en `run.bat` y el README advierte que Linux/multi-GPU no ha sido revalidado para este runtime/modelo. La existencia de una distribución Linux para otros modelos no prueba compatibilidad Flash-Next.

No corresponde un A/B de adopción en este executor Linux. Tampoco se sustituye la configuración objetivo de **2×RTX 3090 + 128 GB** por un brazo de una GPU. La próxima condición habilitante es un runtime Linux que declare y valide Flash-Next en esta topología o una sesión Windows nativa con el artefacto v0.16.1. El screen previo de 1×3090 no se presentará como reemplazo del setup productivo.

## Preflight observado

Al revisar el host, no había proceso/listener de inferencia. `nvidia-smi` mostró dos RTX 3090; ArtCraft usaba 207 MiB de GPU0 y se dejó intacto. No se mató ningún proceso.

## Siguiente paso

Esperar una ruta compatible de Flash-Next para Linux dual-GPU o un executor Windows nativo. Mantener los siguientes tests de modelo bloqueados hasta que cambie esa condición. El lote VF-20261019-01 ya tiene 58/58 materiales con disposition; los resultados, pruebas ejecutadas y bloqueos permanecen en `WORK_QUEUE.md` y Google Sheets.

## Fuentes primarias

- https://github.com/ashalliants/ninfer-3090/releases
- https://github.com/Don-Chad/ninfer-3090/blob/master/docs/serving.md
- https://github.com/Don-Chad/ninfer-3090
