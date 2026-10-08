# Auditoría CyberTiel Coder 35B-A3B — 2026-09-14

## Alcance

Se evaluó `peculiar-ragdoll/Cyber-Tiel-Coder-35B-A3B-GGUF-MTP` en las dos RTX 3090 de LlamaCode, usando el binario CUDA local con reparto por capas y P2P activo. Los artefactos quedaron en:

`/media/cristian/7CFE1E0FFE1DC1F6/models/CyberTiel-35B-A3B-MTP/`

- `Cyber-Tiel-Coder-35B-A3B-MTP-UD-Q4_K_XL.gguf` — 22,75 GB.
- `mmproj-BF16.gguf` — 0,90 GB.
- Pesos Q4 y KV se mantuvieron dentro del límite Q8 del proyecto.

La tarjeta oficial describe un modelo coder MoE 35B-A3B con MTP embebido y soporte multimodal. También advierte que es una variante abliterated/uncensored y que no debe tratarse como un agente con barreras de seguridad; para uso autónomo requiere sandbox y permisos limitados.

## Resultados reproducidos

| Prueba | Resultado |
|---|---:|
| Carga dual, sin MTP, KV Q8, 8K | OK; 12,1 / 10,7 GiB de VRAM |
| Carga dual, MTP3, KV Q8, 8K | OK |
| Carga dual, MTP3, KV Q8, 262K | OK; 15,0 / 15,7 GiB de VRAM reservada |
| Código, sin MTP | 135,9 tok/s; salida correcta |
| Código, MTP3 | 183,0 tok/s; 72/93 tokens aceptados |
| JSON estructurado, MTP3 | 218,97 tok/s; JSON válido |
| Prefill corto, MTP3 | 895 tok/s |
| Prefill con imagen, sin MTP | 950 tok/s |
| Visión con `mmproj-BF16.gguf` | OK; describió correctamente un logo local |
| Contexto 128K, sin MTP | OK; recuperó el dato final; 2.840 tok/s de prefill |
| Contexto 128K, MTP3 | OK; recuperó el dato final; 2.840 tok/s de prefill |
| Contexto acumulado ~184K | OK; recuperó el dato final mediante reutilización de prefijo |
| HE/BCB completo | Pendiente; no se asigna score de calidad |

La primera corrida con un binario anterior fue cancelada durante una generación larga; no se considera fallo del modelo. La validación con el binario CUDA actual fue estable en todos los casos reproducibles.

## Comparación con la tabla vigente

| Perfil | Velocidad local registrada | Calidad validada | Contexto / visión | Lectura |
|---|---:|---|---|---|
| SOL | 74 narrativo / 102 código | BCB 8/8; tool-use OK | 262K validado; sin visión validada | Sigue siendo el principal por evidencia de agente |
| QWEN35-A3B | 123,98 BCB / 134,4 directo | BCB 4/8 | 262K y visión 4/4 | Referencia más cercana; CyberTiel es más rápido en smoke |
| TERRA | 56–58 | BCB 6/8 histórico | 64K y visión | Más conservador para uso diario |
| CyberTiel Q4_K_XL MTP3 | 183 código; 219 JSON | HE/BCB pendientes | 262K carga; ~184K probado; visión OK | Candidato experimental rápido y multimodal |

## Decisión para LlamaCode

CyberTiel sí aporta algo concreto: combina visión, 262K de contexto operativo, MTP embebido, KV Q8 y un decode local claramente superior al histórico de TERRA/QWEN35-A3B en las pruebas cortas.

No reemplaza SOL ni se marca como perfil prioritario todavía porque faltan HE20/BCB bajo el mismo harness, y porque su variante uncensored aumenta el riesgo en loops autónomos y tool-use. Se conserva como candidato experimental local; no se cambia el perfil por defecto.

Siguiente compuerta antes de promoverlo: repetir HE0, HE20 y BCB con la misma huella de binario, agente, plantilla y temperatura que SOL/QWEN35-A3B. Si supera HE0/HE20 y mantiene tool-use sin reparaciones, puede entrar como perfil de velocidad/visión, separado de SOL por política de seguridad.
