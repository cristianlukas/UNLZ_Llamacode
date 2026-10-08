# Auditoría de `jungledesh/profile` para LlamaCode — 2026-09-18

## Conclusión

`profile` es una herramienta de diagnóstico para servidores vLLM en producción:
lee `/metrics`, calcula una cota física aproximada, identifica un único cuello
de botella y mide el delta después de que el operador cambia los flags. No es un
motor de inferencia, un drafter, un optimizador de kernels ni una evaluación de
calidad.

La idea es útil para observar SOL cuando haya tráfico real y presión de KV, pero
no hay una mejora de modelo que promover ni un perfil que supere al actual. No
se modificó SOL, QWEN35-A3B ni ningún otro perfil por esta auditoría.

Fuente primaria revisada: [repositorio oficial de `jungledesh/profile`](https://github.com/jungledesh/profile),
incluyendo [engine.md](https://raw.githubusercontent.com/jungledesh/profile/main/docs/engine.md),
[workflow.md](https://raw.githubusercontent.com/jungledesh/profile/main/docs/workflow.md) y
[limitations.md](https://raw.githubusercontent.com/jungledesh/profile/main/docs/limitations.md).

## Qué hace y qué no hace

El engine externo observa ocho condiciones: under-batching, presión/admisión de
KV, bajo reaprovechamiento de prefijo, riesgo de OOM, saturación de concurrencia,
prefill-bound y headroom de configuración. Su regla importante es no tratar un
KV alto como problema si no hay evictions o cola: 95% de KV puede ser un estado
saludable si el servidor no espera ni expulsa solicitudes.

El bucle es deliberadamente manual: recopila durante una ventana, recomienda un
flag, espera que el operador reinicie vLLM y vuelve a medir. No reinicia el
servidor ni genera carga sintética. Esto es apropiado para seguridad operativa,
pero no se puede interpretar como una mejora automática del modelo.

## Compatibilidad con nuestros perfiles

| Perfil/ruta | Compatibilidad | Utilidad real | Decisión |
|---|---|---|---|
| **SOL** — vLLM TP2/P2P | Parcial: el programa actual rechaza `tensor-parallel-size > 1`; SOL necesita TP2 | La lógica de KV, cola, TTFT/TPOT y prefix-cache es relevante, pero no puede diagnosticar esta instancia dual directamente | Mantener SOL sin cambios |
| **QWEN35-A3B** — vLLM TP2/P2P | Igual que SOL | Útil sólo después de soporte TP2 o mediante un colector propio de LlamaCode | Mantener como secundario multimodal/concurrente |
| GGUF/llama.cpp | No compatible | Sus flags de KV, batch, split y MTP no tienen la misma semántica que vLLM | No trasladar flags |
| NInfer | No compatible | No expone el contrato de métricas vLLM usado por el engine | No trasladar flags |
| Perfiles CPU/auxiliares | No relevante | La cota de ancho de banda de GPU no describe su cuello principal | Sin cambios |

## Validaciones realizadas en esta máquina

### Estado del host

- 2× NVIDIA GeForce RTX 3090 de 24.576 MiB.
- Driver NVIDIA 595.71.05.
- Topología `GPU0 ↔ GPU1: PHB`; no hay NVLink.
- No había procesos ni endpoint de inferencia activos en los puertos locales
  revisados (`8000`, `8010`, `8013`, `8051`, `8080`, `8091`).
- El módulo Python `vllm` no está instalado en el entorno del host.
- La imagen Docker `vllm/vllm-openai:v0.27.1` sí está disponible, pero no había
  contenedor de inferencia ejecutándose en reposo.

Por lo tanto no era posible ejecutar honestamente `profile diagnose`: requiere
un `/metrics` vLLM vivo y tráfico durante al menos una ventana de 30 segundos.
No se inventaron métricas ni se arrancó un servidor sin una campaña controlada.

### Auditoría del código externo

Se clonó el repositorio en un directorio temporal para revisar el código y sus
pruebas. El checkout fue `d3eb54d79ece89236cd377e868777b74e7b5379` (versión de
paquete `2.2.2`). El toolchain Rust (`cargo`) no está instalado en este host, por
lo que no se pudo compilar el binario; esto no afecta la revisión estática ni la
compatibilidad declarada por el propio proyecto.

La limitación decisiva está explicitada por el upstream: una instancia con TP
mayor que 1 se rechaza actualmente. Sus demostraciones de RTX 5090/H100 no son
comparables con nuestro SOL dual, y tampoco prueban BCB, HE20, tool-use o visión
de LlamaCode.

## Qué ya estaba implementado en LlamaCode

No se repitieron como si fueran hipótesis nuevas las pruebas que ya tienen
evidencia local:

1. **Prefix cache de SOL.** Con un prefijo de 19.919 tokens se midió TTFT de
   aproximadamente 10,1 s en frío y 1,2 s en caliente, con 17.776 tokens
   reutilizados. Reordenar tools/claves inutilizó el hit; el harness ahora
   canonicaliza tools por nombre y objetos JSON recursivamente, conservando el
   orden semántico de arrays.
2. **Prefill largo.** SOL ya usa `max-num-batched-tokens=8192` y
   `long-prefill-token-threshold=4096`. El A/B local 2048/4096 no mostró una
   ventaja reproducible de 2048; se conservó 4096.
3. **KV de SOL.** SOL ya usa KV FP8, dentro del límite operativo Q8. Cambiarlo
   otra vez a FP8 no sería una mejora nueva.
4. **Contexto y calidad.** SOL ya tiene 262K de techo validado, 200K recomendado,
   BCB 8/8, tool-use correcto y visión 4/4 en la receta vLLM/AutoRound TP2/P2P.
   El diagnóstico externo no puede subir ninguna de esas columnas.

La evidencia detallada está en
[`vllm-prefix-cache-mcp-audit-20260918.md`](vllm-prefix-cache-mcp-audit-20260918.md)
y [`vllm-qwen38-p2p-sol-20260908.md`](vllm-qwen38-p2p-sol-20260908.md).

## Flags que no se aplican automáticamente

- `--kv-cache-dtype fp8`: ya está activo en SOL; en GGUF/NInfer no es un flag
  equivalente.
- `--max-model-len` menor: puede bajar presión y TTFT, pero sacrifica contexto;
  no se cambia sin evictions/cola observadas y una comparación de agente.
- `--gpu-memory-utilization` mayor: puede dejar margen insuficiente para
  checkpoints, visión o MTP en 24 GB por placa; no se aumenta a ciegas.
- `--max-num-seqs` mayor: aumenta concurrencia potencial, no reserva más
  contexto para una sesión. Debe seguir siendo una decisión por perfil y
  memoria disponible.
- `--max-num-batched-tokens` o `--long-prefill-token-threshold` en GGUF/NInfer:
  no tienen la semántica de vLLM y no se copian.

## Plan reutilizable si se vuelve a probar SOL

Cuando LlamaCode vuelva a iniciar SOL en vLLM, el protocolo correcto es:

1. Mantener una corrida control con el mismo modelo, TP2/P2P, MTP4, KV FP8,
   contexto y harness.
2. Recopilar `/metrics` durante 30 s con una sesión y luego con dos/tres
   sesiones, registrando TTFT, TPOT, preemptions, cola, uso de KV, hits de
   prefix-cache, PP, TG y BCB/tool-use.
3. Diagnosticar sólo si hay tráfico suficiente. Una ventana idle no demuestra
   que el servidor esté bien ni mal.
4. Si el diagnóstico indica presión real, probar una única receta candidata
   en un perfil separado y repetir HE0 → HE20 → BCB.
5. Promover sólo si mejora TTFT/TG bajo la misma carga sin perder BCB 8/8,
   tool-use, visión ni el contexto operativo de 200K.

El punto pendiente es una adaptación multi-GPU propia o soporte TP2 upstream;
hasta entonces, `profile` se considera una referencia metodológica, no una
dependencia ni un perfil seleccionable de LlamaCode.

## Decisión final

- **Default:** SOL permanece sin cambios.
- **Tabla de modelos:** no se agrega una fila; la herramienta no es un modelo.
- **Perfiles secundarios:** QWEN35-A3B y los GGUF/NInfer no cambian.
- **Implementación:** no se agrega cargo, binario externo ni daemon persistente.
- **Repetición futura:** usar este documento como registro para no volver a
  repetir la revisión estática, el chequeo de compatibilidad TP2 ni el A/B de
  prefix-cache 2048/4096 ya cerrado.

