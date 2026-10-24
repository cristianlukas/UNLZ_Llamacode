# Q107 — Resultados: diagnóstico de `update_binary_sh`

**Estado:** PASS; se cerró como error del comando de prueba, no del updater. **Lock:** `307e2ed3-6036-4a52-852b-d4f481e21ee0`.

## Hallazgo

El entorno de shell original no tenía variables `LLAMACODE_*`. Las pruebas Q106/Q107 las añadieron explícitamente con valores vacíos para omitir endpoints live. `scripts/update-binary.sh` busca nombres exportados mediante `compgen -e`, sin filtrar por valor vacío, y por eso escribió `launcher.env`; el updater consideró seguro migrar el wrapper, lo que disparó las dos aserciones. La fixture mínima reprodujo este camino y guardó stdout y los archivos antes/después.

No hubo fallo del updater ni motivo para cambiar el test/source: bastó con no exportar esas variables.

## Verificación tras corregir el entorno

- Ejecución directa de `test_update_binary_sh.sh`: exit 0, `TODO OK`.
- CTest aislado `update_binary_sh`: 1/1 PASS.
- `./scripts/tests-linux.sh Release`: exit 0, **95/95 PASS** (112,55 s en el bloque CTest).
- Para estas ejecuciones `LLAMACODE_Q77_SERVER_URL` y `LLAMACODE_Q102_SERVER_URL` estuvieron ausentes; `CUDA_VISIBLE_DEVICES` vacío. El opt-in live quedó sin endpoint.

## Recursos y alcance

Sólo CPU, shell y temporales. Sin inferencia/modelo/servidor/red/GPU; no se editaron archivos fuente. El host dispone de **2× RTX 3090 + 128 GB RAM**; las GPU no participaron en estas pruebas. No se atribuye este problema ni el anterior cierre de la app a memoria: Q106 ya confirmó que ASTRA 1M y SOL dual completaron y que Q102 no detiene por RSS alto aislado.

P2.1 tenant auth sigue pendiente de un backend/API y fixture multitenant concretos; no adopta Qwen con tools.
