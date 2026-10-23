# Q62 — Factibilidad de P2.1 sin GPU

Inicio: 2026-10-23T15:04:08Z
Lock: `1b64d03d-e61f-46b7-9a04-3a955d3c98a9`

## Objetivo

Revisar el accionable P2.1 (orden de herramientas y aislamiento de tenant) para decidir si existe una prueba CPU-only pendiente que se pueda ejecutar ahora y si su mitigación pertenece a LlamaCode o al harness sintético/modelo. No repetir suites Qwen ni modelar el escenario con mocks nuevos.

## Prerregistro y límites

- Leer únicamente definiciones de TC-74/84/92, adaptador de tools/scorer y los módulos LlamaCode directamente relacionados que aparezcan en búsquedas dirigidas.
- Buscar validación del lado servidor/tenant, secuenciación de dependencias, precondiciones y pruebas de regresión ya existentes.
- No modificar código, contratos, prompts, modelos, perfiles, permisos, bases de datos, seeds o fixtures.
- No compilar, ejecutar suites, iniciar servicios/inferencia, enviar requests ni usar GPU.
- Resultado: distinguir un defecto reproducible del producto (candidato a fix y regresión) de un límite de conducta del modelo (mantener no adopción y esperar cambio material/driver para nuevo benchmark).
