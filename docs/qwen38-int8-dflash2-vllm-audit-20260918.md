# Qwen3.8 INT8 W8A16 + DFlash2 para 2× RTX 3090 — auditoría 2026-09-18

## Resultado

Este es el candidato DFlash2 más prometedor encontrado hasta ahora, pero todavía
no está validado localmente ni debe reemplazar SOL.

El repositorio publica un target Qwen3.8-27B INT8 W8A16 y un drafter DFlash2 W8
separado, con receta específica para Ampere/2× RTX 3090:

- target: aproximadamente 28 GiB;
- drafter: aproximadamente 2,2 GiB;
- contexto configurado: 262.144 tokens;
- KV: `fp8_e4m3`;
- TP=2;
- DFlash2: 7 tokens especulativos;
- visión y tool-calling declarados funcionales.

Fuente: [model card de lued/Qwen3.8-27B-INT8-W8A16-DFlash2](https://huggingface.co/lued/Qwen3.8-27B-INT8-W8A16-DFlash2)
y [notas técnicas](https://huggingface.co/lued/Qwen3.8-27B-INT8-W8A16-DFlash2/blob/main/TECHNICAL.md).

## Métricas externas publicadas

La tabla declara una comparación en el mismo engine, con el contexto máximo
configurado y una única sesión:

| Prompt | Autoregresivo | MTP4 | DFlash2 |
| ---: | ---: | ---: | ---: |
| 128 tokens | 47 | 77 | **117 tok/s** |
| 2.048 tokens | 47 | 73 | **103 tok/s** |
| 8.192 tokens | 47 | 75 | **102 tok/s** |

También declara 98,1% de coincidencia top-1 y KLD medio 0,0007 frente al
modelo BF16. Estas son cifras del autor, no resultados LlamaCode. “262K” es el
límite configurado; la tabla no demuestra que se haya llenado un prompt de
262K durante el decode.

## Comparación con SOL

| Perfil | Velocidad local | Calidad/agentividad | Contexto | Estado |
| --- | ---: | --- | --- | --- |
| SOL | 74 narrativo / 102 código | BCB 8/8, tool-use estable | 262K validado | Default |
| INT8 W8A16 + DFlash2 externo | 102–117 publicados | KLD/top-1 publicados; BCB8 y harness pendientes | 262K configurado | Candidato fuerte |

Si se reproduce, podría superar a SOL en decode corto y mantener un rendimiento
parecido en prompts de 8K. Todavía no demuestra superioridad en calidad agentiva,
tool-use real, BCB8, HE20, visión ni en contexto efectivamente lleno.

## Intento local de descarga

El target pesa 29,6 GB y el drafter 2,2 GB. El volumen donde deben residir los
modelos (`/media/cristian/7CFE1E0FFE1DC1F6/models`) tenía inicialmente unos
32 GB libres, sin margen operativo suficiente.

Se intentó descargar el target directamente allí. Cuatro de seis shards llegaron
a completarse, pero la reconstrucción Xet falló sobre NTFS con `IO Error:
Invalid argument`. La reanudación por HTTP también quedó incompleta cuando C
alcanzó sólo unos 5 GB libres. No se inició el drafter ni se arrancó un servidor.

La descarga incompleta, de aproximadamente 27 GB, se movió de forma recuperable
a:

```text
/media/cristian/Disco local/.llamacode-staging/Qwen3.8-27B-INT8-W8A16-DFlash2-partial
```

C recuperó espacio; no hay un perfil activo apuntando a esa carpeta.

## Diferencia con el DFlash2 rechazado anteriormente

No es la misma ruta que el candidato que produjo `CUDA device-side assert`:

- el fallo previo era SOL + DFlash2 con target AutoRound INT4 y KV FP8;
- esta propuesta usa target INT8 W8A16, drafter W8 y parches específicos de vLLM;
- el model card requiere una imagen nightly y backports de DFlash2 todavía no
  integrados en una versión estable.

Por eso el fallo anterior no permite descartar automáticamente este candidato,
pero tampoco permite asumir que funcionará.

## Protocolo de promoción

Para probarlo sin mezclar resultados:

1. Completar target y drafter en el volumen de modelos con al menos 40 GB libres.
2. Ejecutar el target autoregresivo y DFlash2 con la misma imagen nightly,
   patches, TP, contexto, sampling y endpoint.
3. Medir 8K, 32K, 131K y 262K configurados; incluir PP, TG, TTFT, VRAM y
   aceptación DFlash2.
4. Ejecutar HE0, HE20, BCB8, tool-use y visión.
5. Probar un prompt realmente cercano al límite antes de declarar “262K
   validado”.

Hasta completar esa matriz, queda como **experimental fuerte, pendiente de
espacio y validación**, sin reemplazar SOL.
