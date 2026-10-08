# Auditoría Qwen3.8 Flash-Next EXL3 + YaRN — 2026-09-18

## Resultado

La receta publicada de YaRN permite reservar 512K en ExLlamaV3, pero no produce un perfil superior a SOL en esta máquina. La variante de 1M falla de forma reproducible durante la medición de autosplit en el kernel Triton de atención dispersa QSA. No se cambia el default de LlamaCode ni se agrega este modelo al grupo prioritario.

La mejor configuración local encontrada es experimental: reparto por capas entre las dos RTX 3090, `cpu_moe_split_experts=256`, 262K, visión habilitada y pesos de visión en RAM. Cargó correctamente, utilizó ambas GPU y respondió a una prueba de imagen, pero quedó muy por debajo de SOL y no tiene MTP disponible en el artefacto descargado.

## Artefacto y variantes

Modelo descargado en la partición de modelos:

`/media/cristian/7CFE1E0FFE1DC1F6/models/Qwen3.8-Flash-Next-EXL3-4.05bpw-h6-ng6`

- Revisión EXL3 `4.05bpw_h6_ng6`; 9/9 shards presentes.
- Tamaño del conjunto descargado: aproximadamente 101 GiB (`107,463,600,896` bytes declarados por el índice remoto).
- Incluye `ngram_embedding.safetensors` (~39 GB) y `vision_k6.safetensors` (~561 MB).
- No incluye un archivo MTP/draft utilizable; no se pudo probar speculative decoding con este artefacto.
- Las variantes `Qwen3.8-Flash-Next-EXL3-4.05bpw-h6-ng6-yarn-512k` y `...-yarn-1m` sólo contienen enlaces a los pesos base y un `config.json` independiente; no duplican los 101 GiB.

Configuración aplicada:

```json
{
  "text_config": {
    "max_position_embeddings": 524288,
    "rope_parameters": {
      "rope_type": "yarn",
      "factor": 2.0,
      "original_max_position_embeddings": 262144
    }
  }
}
```

Para 1M se usó `max_position_embeddings=1048576` y `factor=4.0`.

## Pruebas ejecutadas

Stack: ExLlamaV3 1.5.0, TabbyAPI local, PyTorch 2.9.0+cu128, Linux, driver P2P activo, Ryzen 9 9950X3D, 2× RTX 3090, 123 GiB de RAM.

| Prueba | Resultado |
| --- | --- |
| YaRN factor 2 / ventana 512K | La configuración fue aceptada y cargó a 524.288 tokens. Sin TP, todos los expertos quedaron en CPU y sólo se utilizó una GPU. |
| YaRN factor 4 / ventana 1M | Falló dos veces durante autosplit, también con `CUDA_LAUNCH_BLOCKING=1`, en `qsa_sparse_attend_rows` / `qsa_triton.py:313` con `CUDA illegal memory access`. |
| Tensor-parallel TP2 | No inicia: ExLlamaV3 lanza `NotImplementedError: Tensor-parallel is not currently implemented for Qwen4ExpForConditionalGeneration`. |
| Layer split, una GPU, 262K | Carga; 9,8 tok/s en smoke de 64 tokens. GPU1 queda sin uso. |
| Layer split, dos GPU, `cpu_moe_split_experts=256`, 8K | Carga con ambas GPU; 13,5 tok/s en smoke de 64 tokens. |
| Layer split, dos GPU, `cpu_moe_split_experts=256`, 262K | Carga y reserva 262K; GPU0 ~22,8 GiB y GPU1 ~18,3 GiB durante la prueba. Smoke JSON: 35,4 tok/s, 1,28 s de prefill para 62 tokens. |
| Misma receta con visión | Carga a 262K. Imagen redimensionada de prueba descrita y transcripta correctamente; 34,7 tok/s de decode, 13 tok/s de prefill de imagen, 23,0 s de prefill para 288 tokens visuales. |

La prueba de texto fue funcional pero mostró razonamiento interno dentro del campo de contenido cuando se pidió “sólo código/JSON”; por eso esos números son smoke de runtime, no una validación agentiva.

## Comparación contra SOL

| Perfil | Velocidad local | Calidad/agentividad | Contexto | Visión | Decisión |
| --- | ---: | --- | --- | --- | --- |
| SOL | 74 narrativo / 102 código tok/s | BCB 8/8, tool-use estable | 262K validado | Validada 4/4 | Default |
| Flash-Next EXL3, layer split + CPU experts | 35,4 tok/s texto; 34,7 tok/s con visión | Sin BCB comparable en esta receta; no MTP en el artefacto | 262K funcional; 512K sólo reservado | Funcional en prueba de imagen | Experimental, no reemplaza SOL |

El resultado de 512K demuestra que YaRN puede ampliar la reserva de contexto en este backend, no que el modelo conserve calidad o velocidad a 512K. El coste real es la caché y el tiempo de prefill; además, la configuración dual usa CPU para una parte sustancial de los expertos. El intento de 1M no es utilizable con la versión actual por el fallo QSA/Triton.

## Decisión para LlamaCode

- No reemplazar SOL ni modificar su configuración.
- No agregar Flash-Next EXL3/YaRN al grupo de perfiles principales.
- Conservar el artefacto sólo como laboratorio de contexto largo/visión, si el espacio de disco lo permite.
- No repetir estas combinaciones exactas: TP2 Qwen4Exp, 1M YaRN con autosplit y layer split con `cpu_moe_split_experts=256` a 262K ya están registrados aquí.

La implementación de YaRN no se integró en LlamaCode porque el backend que usa este artefacto es TabbyAPI/ExLlamaV3 separado y no supera la ruta SOL integrada. Todas las instancias TabbyAPI de estas pruebas fueron detenidas; no queda proceso de inferencia activo.

## Referencias

- [ExLlamaV3 `config.py`](https://github.com/turboderp-org/exllamav3/blob/master/exllamav3/model/config.py), lectura de `rope_parameters` y longitud dinámica.
- [TabbyAPI `config_models.py`](https://github.com/theroyallab/tabbyAPI/blob/main/common/config_models.py), opciones de `max_seq_len`, `cache_size` y reparto de GPU.
- [TabbyAPI usage](https://github.com/theroyallab/tabbyAPI/wiki/03.-Usage), carga y configuración de contexto.
- [Checkpoint Qwen3.8 Flash-Next EXL3](https://huggingface.co/turboderp/Qwen3.8-Flash-Next-exl3).
