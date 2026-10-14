# Plan — Q-20261014-IQ3XXS-MODALITY-FOLLOWUP

**Fecha:** 2026-10-14
**Lock:** `b56b3d66-0abe-4273-b814-fe927b9a77c2`
**Estado:** preregistrado antes de iniciar inferencia.

## Propósito y evidencia ya válida

Cerrar las dimensiones que quedaron sin probar en el screening ISTA-DASLab
Qwen3.8-Flash-Next IQ3_XXS / Strata: recuperación real cerca de 115K tokens,
capacidad nativa 262K, entrada de imágenes, y un E2E de Computer Usage con
estado final verificable en más de una aplicación. No repetir coding/TaskFlow,
las ablations ni Server Speed v1, ya medidos en
`Q-20261009-FLASHNEXT-IQ3XXS-AB`. Sus resultados y decisión vigente siguen en
el informe de esa campaña y en el registro canónico.

### Perfiles

- **Candidato:** ISTA-DASLab GSQ-RCO IQ3_XXS, revisión
  `1c04b8102ca5346f1faf4d9914503e378d713021`; dos shards en
  `/media/cristian/Disco local/Models/FlashNext-IQ3XXS-ISTA-Strata-eval-20261009/models/IQ3_XXS/`.
  Se reutiliza Strata v0.1.41, commit
  `fb58e0dbc8399662c0e47c76578c6e878b14f6cf`, CUDA 12.8 / SM86, 2× RTX 3090,
  KV int8, 32K residente, MTP4, `spec-min-p=0.70`, `pcie-frac=0.00` y
  sampling conservador `0.6/0.95/20/0.0/1.0/0.0`.
- Se congela Strata **v0.1.41**, la versión instalada que produjo la cifra local
  previa de velocidad y corresponde al corte temporal del post. El post no fija
  pesos/hashes, tarea, prompt, seed, cuant exacta ni latencia TTFT; su cifra en
  2× RTX 5090 / 256 GB RAM no es comparable directamente con el host local
  2× RTX 3090. No se actualizará el runtime en medio de este A/B.
- Auditoría del código mencionado: upstream #711 habilita streaming de KV
  híbrida K8V4 con `--kv-resident`; este perfil Linux usa `--kv int8`. #749
  trata la capacidad de commit de Windows. Ninguno explica por sí solo una
  ganancia de decode en nuestra configuración Linux. Las versiones posteriores
  se registrarán como pendientes de A/B separado.
- **Control de recuperación y visión:** ASTRA Flash-Next IQ3_S calibrado,
  mismo engine/runtime, hardware y tratamiento KV. Es una comparación de
  perfiles completos; no atribuir diferencias sólo a los pesos.
- Hashes de pesos, binarios, packs y configuración se conservarán en
  `receipts/model-source-manifest.json`; no se descargarán ni alterarán pesos.

## Pruebas, orden y criterios

GPU serial, un servidor a la vez, en `127.0.0.1` con puerto libre. Antes de cada
carga se comprobarán procesos/listeners, RAM, swap, VRAM y salud del endpoint.
No se controlará el display `:0` ni se detendrán procesos ajenos. Se guardarán
logs, respuesta bruta, tokens de uso, hashes y telemetría. Si el engine cae, el
evento se clasifica como infraestructura y no como score de calidad.

1. **Context Retrieval v1, 115K:** repetir deliberadamente el fingerprint IQ3_XXS
   que cerró el proceso durante el prefill (motivo: diagnosticar el fallo de
   transporte anterior, no duplicar un score). Fixture preregistrado de 10
   hechos, 115.003 tokens de texto / SHA-256
   `ea4cd4a48080b0191273c4dfe4df54d69535a131d1e0117a31a3c75377d8ec84`;
   temperature 0, top-p 1, seed 4242, máximo 512 y reasoning none. Se contará
   sólo si HTTP termina, el endpoint reporta prompt dentro de 131072 tokens,
   no hay truncamiento y se obtiene JSON parseable; se reportarán hechos exactos
   de 10. Después se ejecutará el mismo fixture una vez en ASTRA IQ3_S. Una
   caída antes de respuesta detiene ese perfil y no genera cero de calidad.
   Si IQ3_XXS vuelve a caer, revisar logs y clasificar el punto de corte; no
   cambiar el prompt, sampling o memoria para rescatar el score.
2. **Contexto nativo 262K:** una solicitud IQ3_XXS según el plan/script ya
   preparado en la campaña original; configuración aislada idéntica salvo
   `max-context=262144` y puerto. Un único passkey sintético al 95% dentro de
   257K–259K tokens locales. Guardas duras antes y durante la prueba:
   `MemAvailable >=32 GiB` y swap usado `<2 GiB`; abortar si cualquiera falla.
   Éxito requiere respuesta HTTP completa, uso dentro del límite y recuperación
   literal del passkey. Es smoke de capacidad, no calidad general ni réplica del
   post Q4/4×P100.
3. **Visión:** generar un holdout geométrico nuevo (no reutilizar el de IQ2_XS)
   y congelar su SHA-256 antes de inferir. Una pregunta común para IQ3_XXS y
   ASTRA IQ3_S, con la misma imagen y mmproj BF16 existente
   (SHA-256 esperado `b1a82259702816a5330d7bd7607cd9676b11780e79ff7348c21103ff3ce49bd0`),
   encoder CPU (`gpu:false`), temperatura 0, top-p 1, top-k 1, seed 4242 y salida
   JSON de hasta 512 tokens. Holdout `vision-geometry-count-v1`, imagen
   1024×576, SHA-256 `7526fe77533223bc8dc5ab5ea00af77eae16b3a10a634dadd225591e2cdd9bbf`.
   Acierto requiere conteo exacto de 2 círculos, 2 triángulos, 2 rectángulos,
   1 estrella y un objeto por cada color azul, rojo, verde, amarillo, naranja,
   morado y negro. Una corrida por perfil es sólo un smoke visual; no se infiere
   OCR general ni calidad estadística.
4. **Computer Usage E2E:** candidato IQ3_XXS en el HarnessSpec/permisos de
   escritorio existentes, 3 réplicas secuenciales en Xvfb privado. Cada réplica
   usa GNOME Calculator y GNOME Text Editor: verificar `73×19=1387`, escribir
   la línea exacta `MUSE CU E2E: keyboard input verified.` sin guardar y volver
   a Calculator para comprobar `47×29=1363`. Variar resolución, locale y tema
   igual que en la campaña base. Éxito por réplica requiere estado final
   visible/verificado en ambas aplicaciones. Conservar acciones, observaciones,
   capturas/OCR, reintentos y tiempos. Un fallo de tool/agent con servicio sano
   cuenta como fallo del perfil completo; un endpoint no listo es infraestructura.
   El brazo ASTRA ya tiene 2/3 réplicas completas comparables en
   `Q-20261013-MUSE-CU-E2E`; reutilizar esa evidencia, sin volver a ejecutarlo.
5. **Ingi-Charla / audio:** auditoría de capacidad y rutas. El model card de
   Flash-Next declara Image-Text-to-Text y la app usa STT/TTS separados; no se
   atribuirá WER/CER o voz al modelo si no existe endpoint acústico nativo. No
   enviar audio ni aceptar una transcripción textual como prueba acústica.

## Decisión preregistrada

Esta ejecución completa cobertura de uso y no es una candidatura a promoción.
No modificar perfiles productivos, HarnessSpec, defaults ni código. Aun si
alguna dimensión resulta favorable, sólo se recomendará uso acotado con esta
evidencia; no un ganador global. Si una prueba no llega a cumplir sus guardas,
se registra como bloqueada/inválida y se conserva el punto exacto de reanudación.
