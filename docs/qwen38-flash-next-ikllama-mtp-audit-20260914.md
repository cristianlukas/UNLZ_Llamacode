# Auditoría: MTP de Qwen3.8 Flash-Next en ik_llama.cpp — 2026-09-14

## Resultado ejecutivo

El reporte describe el PR #2369 de `ik_llama.cpp`, que agrega soporte MTP
NextN nativo para `qwen4exp` y permite encadenarlo con `ngram-mod`. El PR fue
fusionado en `ik_llama.cpp` y reporta mejoras grandes en una RTX 5090:
aproximadamente 45 → 90 tok/s en código, con aceptación MTP de 93–99%.

La idea es relevante, pero **no es actualmente un reemplazo de SOL en
LlamaCode**. El reporte aclara que el soporte multi-GPU todavía no está
resuelto. Además, el PR limita la especulación a un solo slot y tiene gates
pendientes para multimodalidad.

## Qué se verificó

La revisión del PR confirma:

- soporte MTP para la arquitectura `qwen4exp`;
- cabezal NextN de 2,6B, integrado o cargado mediante `--model-draft`;
- encadenamiento `ngram-mod + mtp`;
- validación publicada de salida equivalente al modelo sin MTP;
- aceptación aproximada de 93–99% en código y ~63% en narrativa;
- limitación explícita a un solo slot (`-np > 1` rechazado);
- el gate de multimodalidad con projector todavía existe.

Fuente primaria: [PR #2369 de ik_llama.cpp](https://github.com/ikawrakow/ik_llama.cpp/pull/2369).

## Cruce con nuestro setup

| Variante | Resultado | Decisión |
| --- | --- | --- |
| ik_llama.cpp MTP publicado | 45 → 90 tok/s en 5090, principalmente una GPU | Referencia externa |
| ik_llama.cpp con nuestro dual 3090 | No validado: el soporte multi-GPU no está resuelto | No promover |
| llama.cpp Flash-Next + cache + MTP | Acceso ilegal CUDA/corrupción en pruebas previas | No activar |
| llama.cpp MTP sin cache | Arranca, pero más lento que cache188 | Experimental |
| SOL TP2/P2P + MTP4 | 74 narrativo / 102 código; BCB 8/8 | Default |

La build local de `ik_llama.cpp` disponible en la caché es anterior al PR
#2369 y no expone soporte usable para nuestro flujo `qwen4exp`/MTP. No se
reemplazó el binario oficial de LlamaCode ni se descargaron los quants
específicos de ik_llama.

## Diferencias que impiden promoverlo

- El benchmark del reporte es de una sola GPU; nuestro beneficio principal
  depende de repartir el modelo entre dos 3090.
- La variante usa un quant y una disposición de expertos diferentes de nuestro
  ASTRA UD-Q4_K_XL con expertos host/cache MoE.
- El PR exige `-np 1`, mientras que LlamaCode necesita conservar un contrato
  de servidor compatible con sus sesiones y agentes.
- La aceptación alta en código no demuestra tool-use correcto, BCB ni ausencia
  de contaminación de estado en nuestro runtime.
- La rama alternativa sigue siendo otro backend; no se puede insertar sólo
  cambiando argumentos de los perfiles existentes.

## Qué sí conviene conservar

1. Seguir la evolución de `ik_llama.cpp` como candidato de backend separado.
2. Probarlo sólo cuando exista soporte TP/split multi-GPU estable para
   `qwen4exp` y un GGUF MTP compatible con la disposición local.
3. Exigir comparación A/B con SOL: HE0, HE20, BCB, tool-call, 131K/262K y
   sesiones largas con thinking y sin thinking.
4. Mantener KV Q8 como máximo para cualquier variante promovible.

## Decisión

- **SOL** sigue siendo el default.
- **ASTRA** permanece experimental y sin MTP.
- No se agrega un perfil `IK-MTP` al dropdown.
- No se cambia el runtime estable ni se descargan nuevos modelos.

La conclusión es que el PR puede ser una futura ruta de aceleración para
Flash-Next, pero hoy no demuestra una mejora reproducible sobre SOL en las dos
RTX 3090 de LlamaCode.
