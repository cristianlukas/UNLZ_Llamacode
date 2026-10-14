# Incidente de transporte — Context Retrieval v1 / IQ3_XXS

- El health check previo reportó `status=ok`, modelo cargado, `max_context=131072`
  e imágenes desactivadas.
- Prompt: 115.003 tokens de texto; 115.015 tokens mostrados por Strata con el
  wrapper. SHA-256 `ea4cd4a48080b0191273c4dfe4df54d69535a131d1e0117a31a3c75377d8ec84`.
- Solicitud SHA-256 `17cff24ebc39318f26be2302e1400edb0284ddc59fcf0793e357b4a3edc091cf`;
  temperatura 0, top-p 1, seed 4242, máximo 512 tokens, reasoning none.
- El log visible de la sesión Strata avanzó el prefill hasta 65.536 de 115.015
  tokens y luego mostró la parada del proceso. El cliente registró
  `RemoteDisconnected('Remote end closed connection without response')` tras
  22,725 s. No hubo body, `usage` ni `finish_reason`; ningún caso fue evaluado.
- Al inicio quedaban 68.918.796 kB de MemAvailable; las GPUs reportaban 23.751
  y 23.662 MiB usados de 24.576 MiB. Después del cierre MemAvailable era
  116.703.324 kB y el engine había liberado casi toda la VRAM. La consulta al
  journal del kernel para el intervalo revisado no devolvió eventos filtrados
  de OOM, proceso muerto, NVRM o Xid. Esto no determina por qué terminó el
  proceso; la causa raíz queda desconocida.
- Clasificación: fallo de infraestructura/transporte, **inválido para puntuar
  calidad o capacidad de contexto**. No interpretar el campo vacío `0/10` del
  JSON como resultado. No se lanzó el control ASTRA después de este incidente.

El recibo JSON íntegro está en `iq3xxs.json`. No se repitió la misma petición
porque no se aisló la causa del cierre. Se puede reintentar este fingerprint
cuando endpoint y proceso Strata sean estables; después ejecutar ASTRA en serie.
