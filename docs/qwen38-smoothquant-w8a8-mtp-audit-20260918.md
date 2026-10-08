# Qwen3.8 SmoothQuant W8A8 + DFlash2 — auditoría 2026-09-18

## Resultado ejecutivo

El hallazgo sí es relevante para LlamaCode, pero todavía no reemplaza a SOL.
El candidato prioritario para una prueba futura es:

```text
Freaksterz/Qwen3.8-27B-SmoothQuant-W8A8-INT8
```

La revisión `main` declara una receta mixta W8A8/W8A16, head MTP BF16 y
compatibilidad con DFlash2. El model card publica más prefill que su referencia
W8A16 y, con DFlash2, 82 tok/s narrativos y 232 tok/s de código en 2× RTX 3090.
Son cifras del autor, no una medición de LlamaCode.

La publicación que motivó esta auditoría usa otro candidato relacionado:
`lued/Qwen3.8-27B-huihui-abliterated-INT8-W8A16-MTP`, con 70,4 tok/s de una
sesión, 67,8 tok/s a unos 32,5K y 136,1 tok/s agregados con tres streams. Ese
modelo es abliterated/uncensored y no debe mezclarse con SOL ni con el
SmoothQuant v3.

## Evidencia externa revisada

### SmoothQuant v3

El model card de `Freaksterz` declara:

- KLD medio frente a BF16: `0,00556`.
- 96,9 % de coincidencia top-1 en su suite teacher-forced.
- 288 módulos con INT8×INT8 y 112 módulos W8A16.
- MTP BF16 incluido; la revisión v3 conserva la compatibilidad con DFlash2.
- DFlash2 con longitud de aceptación `4,34`.
- prefill de `2.820 / 2.846 / 2.747 tok/s` para 2K/8K/16K.
- decode externo de `82 / 232 tok/s` para narrativa/código con DFlash2.
- un soak de prefijos de 9/9 casos correctos y 67 % de hit-rate.

El mismo card advierte que W8A16 es aproximadamente 13 % más rápido en decode
de una sola sesión, mientras que W8A8 favorece prefill y throughput batched.
Esto es importante para LlamaCode: la posible ventaja no es universal; depende
de si la carga es una sesión de coding larga, muchos agentes o prompts grandes.

### INT8 W8A16 abliterated

El modelo `lued/Qwen3.8-27B-huihui-abliterated-INT8-W8A16-MTP` declara 29,44
GiB, MTP BF16 byte-preservado, torre de visión y contexto nativo. Su KLD
publicado es `0,000705`, pero el propio card aclara que KLD no es una evaluación
de calidad agentiva, tool-use, coding, multimodalidad ni contexto largo.

Además, cambia el modelo base mediante abliteration. Por lo tanto, aunque el
checkpoint sea técnicamente atractivo, no es una comparación limpia contra SOL:
puede cambiar rechazos, cautelas y comportamiento de seguridad además de la
cuantización.

## Comparación con la referencia local

| Perfil | PP / TG local o publicado | Calidad LlamaCode | Contexto | Visión | Decisión |
| --- | --- | --- | --- | --- | --- |
| **SOL** | **2.287 PP a 10K; 74 narrativo / 102 código TG** | **BCB 8/8, HE válido, tool-use estable** | **262K validado; 200K recomendado** | **4/4 validada** | **Default** |
| SmoothQuant v3 + DFlash2 | 2.820–2.846 PP publicado; 82 narrativo / 232 código publicado | Sin BCB8/HE20/tool-use de LlamaCode | 131K en la receta publicada; 262K no demostrado en esta campaña | Declarada, pendiente de nuestra prueba | **Candidato de alto interés, no promovido** |
| huihui INT8 W8A16 + MTP | 70,4 TG aislado; 136,1 agregado/3 streams publicado | KLD 0,000705; BCB8 pendiente | 262K configurado, no validado por nuestro harness | Declarada; usa shim CPU en el reporte | **Candidato experimental separado** |

La cifra `232 tok/s` de SmoothQuant sería superior a SOL en código si se
reprodujera bajo el mismo harness, pero hoy no es comparable: usa otro engine,
otra revisión de vLLM, otro drafter, otra metodología y prompts distintos. La
ventaja publicada de prefill sí resulta especialmente interesante para el
harness, mientras que la ventaja de decode debe confirmarse con tareas reales.

## Verificación realizada en esta máquina

- Las dos GPU son RTX 3090, P2P `OK`, conexión `PHB`, sin NVLink.
- CPU: Ryzen 9 9950X3D; RAM disponible observada: aproximadamente 114 GiB.
- LlamaCode sí tiene integración vLLM administrada: resuelve perfiles
  OpenAI-compatible/loopback, conserva la configuración TP2/P2P de SOL y
  controla el ciclo de vida para que el servicio no quede residente cuando la
  aplicación está cerrada. El hecho de que `python3` del host no pueda hacer
  `import vllm` no invalida esa integración.
- La receta local validada de SOL usa vLLM 0.27.1. La receta SmoothQuant v3
  declara vLLM `>=0.28`, por lo que el trabajo pendiente es agregar/verificar
  esa imagen o runtime administrado dentro del flujo de LlamaCode, no instalar
  vLLM globalmente a mano.
- No se encontró el checkpoint SmoothQuant ni su drafter completo bajo
  `/media/cristian/7CFE1E0FFE1DC1F6/models`.
- El target relacionado INT8/W8A16 de `lued` quedó previamente incompleto y
  fuera del root activo por falta de espacio. No se inició ningún servidor con
  este candidato; eso es una falta de artefacto, no una falta de integración
  vLLM en LlamaCode.
- SOL sigue gestionado por LlamaCode con `restart=no`; no se adopta un servicio
  persistente de vLLM, porque contradice el requisito operativo de que vLLM no
  quede arrancado cuando LlamaCode está cerrado.

## Qué se debe probar antes de promoverlo

La descarga debe hacerse sólo cuando haya espacio suficiente en el root de
modelos. El target SmoothQuant ocupa aproximadamente 31,3 GB; además se
necesitan el head MTP y el drafter DFlash2. No se debe llenar el volumen C para
hacer la prueba.

La matriz mínima, usando la misma imagen y el mismo endpoint administrado por
LlamaCode, es:

1. SOL autoregresivo, SOL MTP4 y SmoothQuant autoregresivo como controles.
2. SmoothQuant con MTP3 y con DFlash2 K=7, usando BF16 de activaciones y FP8
   KV, tal como exige la receta.
3. Contextos de 8K, 32K, 131K y 262K; medir PP, TG, TTFT, VRAM, aceptación y
   errores del EngineCore.
4. Una sesión y dos sesiones; después tres streams sólo como throughput
   agregado, sin confundirlo con TG de una sesión.
5. HE0, HE20 y BCB8 completos con el harness de LlamaCode; tool-use real,
   JSON estricto y multi-turno con schemas MCP estabilizados.
6. Visión con la misma imagen, incluyendo captura grande preprocesada a 768 px,
   y una prueba con el encoder en GPU y otra con el encoder en CPU.
7. Equivalencia greedy corta frente a SOL sin thinking y con thinking. Si
   DFlash2 cambia la salida base de forma material, queda como acelerador
   experimental aunque sea más rápido.
8. Prefix cache con schemas de tools en el mismo orden y después con una
   permutación deliberada, para comprobar que el hit-rate no dependa del
   gateway.

## Decisión para la tabla y los perfiles

No se modifica SOL, el dropdown ni el perfil predeterminado. Se registra
SmoothQuant v3 como **candidato externo de alta prioridad para prefill y
throughput**, y el huihui W8A16 como **candidato separado, abliterated y no
comparable limpiamente**.

Para promover SmoothQuant por encima de SOL exigiría, como mínimo:

- BCB `8/8` y HE20 válido bajo LlamaCode;
- tool-use y visión funcionales;
- no más errores CUDA/DFlash2 durante 262K;
- TG de código superior a 102 tok/s en la misma modalidad y, de ser posible,
  PP superior en 32K/131K;
- estabilidad de dos sesiones y prefix-cache reproducible.

### Fuentes

- [Freaksterz/Qwen3.8-27B-SmoothQuant-W8A8-INT8](https://huggingface.co/Freaksterz/Qwen3.8-27B-SmoothQuant-W8A8-INT8)
- [lued/Qwen3.8-27B-huihui-abliterated-INT8-W8A16-MTP](https://huggingface.co/lued/Qwen3.8-27B-huihui-abliterated-INT8-W8A16-MTP)
- [Auditoría local de SOL vLLM TP2/P2P](vllm-qwen38-p2p-sol-20260908.md)
- [Auditoría previa INT8 W8A16 + DFlash2](qwen38-int8-dflash2-vllm-audit-20260918.md)
