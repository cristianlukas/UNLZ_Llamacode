# SOL — resultados locales tool-eval-bench v2.7.0

- **Perfil completo:** Qwen3.8-27B AutoRound INT4, vLLM 0.27.1, TP2, MTP4, KV FP8, contexto 262144, ambas RTX 3090. Pesos locales en `/media/cristian/Disco local/Models/llamacpp/club-3090/qwen3.8-27b-autoround-int4`; ya estaban descargados y fueron reutilizados, sin descargas.
- **Image ID:** `sha256:0a51ea5b4ae2dc5d81890e5173f54203d2a3ae0cfffe51b8fd2afd4391bfd967`; revisión de pesos `b4c61732c4f2d8af323d75ba5702b5c7f3361539`; hashes por shard en `model-source-checksums.txt`.
- **Suite:** tool-eval-bench 2.7.0, commit `c483eef867d75d9dd04c7d370fe553f96a49d672`; parámetros comunes: seed 42/43/44, T=1, top-p=.95, top-k=20, min-p=0, repeat=1, presence=0, `max_tokens=16384`, thinking enabled, reasoning_effort medium, 8 turns, 600 s, una solicitud a la vez, sin error injection.
- Los resultados son de perfil completo en el entorno local; no replican el checkpoint Q5_K_XL, la Radeon R9700 ni los builds del post.

## Corridas válidas (retry de seed42 tras un fallo de infraestructura)

| Suite | Seed | Score tool-eval | Puntos | Pass / partial / fail | Tiempo agregado de escenarios | Tokens | Huella runner |
|---|---:|---:|---:|---:|---:|---:|---|
| standard | 42 | 25/100 | 34/138 | 10 / 14 / 45 | 752.08 s | 235284 | `9192e33dfc31` |
| standard | 43 | 25/100 | 34/138 | 10 / 14 / 45 | 597.19 s | 224862 | `cec402342550` |
| standard | 44 | 27/100 | 37/138 | 11 / 15 / 43 | 829.49 s | 261598 | `0bf6409f252c` |
| hardmode | 42 | 58/100 | 22/38 | 10 / 2 / 7 | 139.89 s | 82283 | `7673ca2da329` |
| hardmode | 43 | 61/100 | 23/38 | 11 / 1 / 7 | 150.79 s | 90868 | `087e272f4ec5` |
| hardmode | 44 | 55/100 | 21/38 | 10 / 1 / 8 | 156.79 s | 104718 | `8ed65ca57a02` |

**Resumen standard:** media 25.67/100; mediana 25; resultados por semilla 42=25, 43=25, 44=27. Tiempo agregado de escenario: 2178.76 s (36.31 min).

**Resumen hardmode:** media 58.00/100; mediana 58; resultados por semilla 42=58, 43=61, 44=55. Tiempo agregado de escenario: 447.47 s (7.46 min).

## Corrida estándar seed 42 invalidada por infraestructura

El primer intento recorrió 47 casos con inferencia (38 pass, 4 partial, 5 fail; 80/94), pero el Worker_TP0 de vLLM sufrió un CUDA device-side assert y TC-48–TC-69 devolvieron HTTP 500. El score 85/100 que imprimió el runner no es válido para 69 casos y no entra en las medias. Tras reiniciar el contenedor propio, TC-48 aislado respondió con HTTP normal y la repetición completa seed 42 terminó 69/69 con score 25/100. Se conservan ambos resultados y la causa en `incident-standard-seed42.md`.

## Observaciones de ejecución

La suma de `duration_seconds` del runner mide tiempo de escenarios (incluye las llamadas secuenciales observadas, no startup del servidor). TC-45 y TC-64 pueden tomar varios minutos; por ejemplo, TC-64 duró 289.73 s en seed42 y falló funcionalmente, pero devolvió respuesta antes del timeout, por lo que cuenta como calidad. El primer crash fue infraestructura, no fallo del modelo. El runner y el servidor registraron algunos mensajes `Failed to advance FSM` de XGrammar; los casos que devolvieron respuesta se puntuaron por los criterios de la suite y se conservan sus trazas.

TPS no es una métrica formal de esta comparación: el objetivo es calidad de tool-use. Los logs de vLLM contienen tasas instantáneas de generación/MTP; no deben confundirse con un Server Speed A/B ni con los TPS de la tabla de perfiles previa.
