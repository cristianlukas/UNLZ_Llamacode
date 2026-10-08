# Qwen3.8 Flash-Next IQ1_S en RTX 3090 — auditoría

> Revisión posterior: la ejecución local del 2026-09-15 descargó y probó el
> par IQ1_S + head MTP Q4. Ver [la auditoría actualizada](qwen38-flash-next-iq1s-3090-audit-20260915.md);
> este documento conserva el análisis previo y no debe leerse como evidencia de
> que el artefacto no se descargó.

Fecha: 2026-09-14  
Equipo LlamaCode: Ubuntu, 2× RTX 3090, P2P disponible, ~123 GiB de RAM

## Evaluación del post

El reporte ejecuta `UD-IQ1_S` en una sola RTX 5070 de 12 GB y publica 21–22
tok/s con sólo 10K de contexto. Es una demostración de que el modelo puede
cargar en hardware pequeño, pero no es una mejora para nuestro setup: IQ1_S es
un quant de menor fidelidad que el UD-Q4_K_XL que ya tenemos, y la medición no
incluye BCB, HE0/HE20 ni tool-use comparable.

## Pruebas anteriores relevantes

| Variante local | Resultado | Lectura |
|---|---:|---|
| Flash-Next con `n-cpu-moe` y KV Q8 | Carga en el entorno dual; ~9–10 tok/s en las campañas antiguas | El offload a CPU resuelve memoria, no supera SOL |
| ASTRA con cache MoE 188 | ~16–41 tok/s según contexto | Experimental; calidad agéntica no validada |
| `lazy on`/SSD | TPS bruto alto, pero salida `////` corrupta | Rechazado |
| `lazy on-direct` | ~7,54 tok/s con salida válida | Demasiado lento |
| BeeLlama KVarN5/KVarN5 | ~36 tok/s a 131K; JSON, Python y tool-call válidos | Mejor alternativa Flash-Next local |
| SOL | 74 narrativo / 102 código; BCB 8/8 | Default |

## Ideas del post

- `KVarN5` ya está probado en BeeLlama y se mantiene con cola cero, sin KV
  superior a Q8.
- MTP puede empeorar cuando los expertos están en RAM; nuestras pruebas
  anteriores muestran la misma limitación y no lo activamos en ASTRA.
- `n-cpu-moe` es una variable válida de memoria, pero no convierte un quant IQ1
  en una opción de mayor calidad.
- La visión no pudo repetirse con los archivos actuales. El Flash-Next
  `n_embd=2560` rechazó el mmproj local `n_embd=5120`, que corresponde a otra
  variante Qwen3.8. No se debe clasificar como visión validada.

## Decisión

No se descarga el IQ1_S, no se agrega un perfil y no se cambia el default. El
post no supera SOL ni la variante BeeLlama KVarN5. La única conclusión útil es
mantener KVarN5 como opción de contexto largo texto-only y seguir evitando MTP,
lazy loading y SSD offload hasta que produzcan salida correcta y una mejora
medida en el mismo harness.
