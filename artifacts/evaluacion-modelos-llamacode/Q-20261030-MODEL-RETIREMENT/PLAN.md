# Q192 — Retiro de modelos localmente dominados

Aplicar el pedido del usuario: retirar sólo archivos con valores menores en las tres columnas comparativas de la planilla (prefill promedio, decode promedio, Q172), sin dependencia de PeritoSoft. Se verifican huella, ruta, tamaño y consumidores antes de borrar; los resultados históricos permanecen en el sheet y el recibo.

## Archivos autorizados para retiro

- Fila 20: Ternary Bonsai 2 27B PrismML PQ2_0. SHA-256 `3907dc1658db1f78a9826bf8d5bcb8dc65db0d466388937af57f2294fae62ec1`; 7.206.168.928 bytes. Frente al NInfer v3 de la fila 17: 832,88 < 1.513,90 prefill; 53,53 < 157,44 decode; 75 < 83,33 Q172. Mismo modelo base y ladder 8K–256K. Sin dependencia PeritoSoft encontrada.
- Fila 27: Qwen3.6-35B-A3B UD-Q4_K_XL. SHA-256 `55983c5a75a1ab969824077b3bb3de4146e82a9234072b48ad4e8f92ad3fe9f1`; 22.853.663.008 bytes. Frente a LFM2.5-VL-3B, fila 26: 6.426,38 < 8.712,98 prefill; 114,17 < 159,18 decode; 0 < 25 Q172. El comparador es VLM y su ladder llega a 31.872 tokens, mientras Qwen3.6 se midió hasta 261.888; el enlace de supersesión registra sólo la dominancia en las tres métricas agregadas pedidas, no equivalencia funcional. El Qwen3.6 Q172 dio 0/100 porque agotó el presupuesto de razonamiento sin responder en 84/84 escenarios. La auditoría Q187 y la búsqueda de fuentes/configuración de PeritoSoft no encontraron esta cuantización exacta.

## Conservados

- Gemma 4 12B QAT Q4_0, aunque numéricamente dominado: PeritoSoft contiene fixtures que esperan el archivo bajo `D:\Models\llamacpp\gemma-4-12b-it-qat-q4_0.gguf`.
- TERRA Qwen3.8-27B AutoRound: numéricamente inferior a SOL, pero sigue enlazado al perfil de lanzamiento `2_TERRA · Qwen3.8 27B · vLLM TP2 P2P MTP4` en la configuración local de LlamaCode; se conserva para no dejar roto ese perfil. Q173 válido corresponde a MTP-off y Q172 es una sola semilla; MTP4 está bloqueado por assert CUDA.

No se modifican ASTRA, SOL, los recibos de benchmark ni los locks archivísticos/snapshots.
