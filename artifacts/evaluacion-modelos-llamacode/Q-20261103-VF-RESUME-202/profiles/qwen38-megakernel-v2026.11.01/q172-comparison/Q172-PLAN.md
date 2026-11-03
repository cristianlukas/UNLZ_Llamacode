# Q172 por perfil: Qwen3.8-27B UD-Q4_K_XL, single PNY

## Motivo y alcance

Las filas Q173 de `Modelos locales por peso` tienen medidas de velocidad, pero
Q172 vacío. Completar una evaluación independiente por perfil, sin transferir
el 79/100 del perfil dual con mmproj ni los puntajes de otros runtimes.

## Perfiles preregistrados

| ID | Perfil | Runtime | GPU | KV / decodificación |
|---|---|---|---|---|
| Q205.01 | A-control | llama.cpp CUDA b67849b | PNY RTX 3090 GPU1 | q8_0 K/V, MTP apagado |
| Q205.02 | B | Megakernel v2026.11.01 | PNY RTX 3090 GPU1 | q8 KV, `--no-mtp` |
| Q205.03 | C | Megakernel v2026.11.01 | PNY RTX 3090 GPU1 | q8 KV, `--draft 7` |

Mismo GGUF UD-Q4_K_XL (17,559,178,144 bytes; SHA-256
`3f227079003add2511437e5b1e94812e363385225bf6a9b47b0054a72bc8b01e`), misma
GPU física, plantilla con `enable_thinking=false`, contexto 65,792 y suite
Tool-Eval Hard Mode 2.8.0. ASUS GPU0 queda excluida por la cuarentena de VRAM.
No se apaga la GUI; la actividad gráfica se registra como covariable.

## Harness y parámetros

Tool-Eval Hard Mode 2.8.0 (`tool-eval-bench` SHA-256
`31e3c8f5fa9140738cde4e1cecc909f5335cf928a90fbdd062ec7935e0526472`), escenarios
TC-70..TC-97 (28), seed 42, variant-seed 20261010, 1 trial, serial (`parallel=1`),
`max_turns=8`, `timeout=120`, `--fail-on-safety`; temperatura 0.6, top-p 0.95,
top-k 20, min-p 0, repeat penalty 1.0, presence penalty 0.0 y reasoning effort
medium, igual que el Q172 previo de Qwen3.8. El servidor conserva
`enable_thinking=false`. Modelo servido se toma de `/v1/models`; argumentos,
hardware, hashes y salida completa quedan en el recibo.

## Criterios

- Puntaje válido sólo si el JSON termina `completed`, informa 28/28 escenarios y
  máximo 56 puntos. Si no, Q172 queda N/D, con bloqueo/error concreto.
- Reportar puntaje/100, puntos, estados de escenario y gates críticos por perfil.
- Un fallo crítico de seguridad mantiene el puntaje de screening pero impide
  adopción autónoma; no ejecutar semillas adicionales para ese perfil.
- Esta primera pasada es n=1 por perfil. No afirma superioridad estadística ni
  reemplaza la evaluación de tareas agénticas largas con el harness de LlamaCode.
- Ejecutar A, B y C en serie. Repetir preflight y actualizar/leer la hoja después
  de cada perfil. No tocar pesos ni perfiles productivos.

## Preflight y abortos

Antes de cada perfil: lock Q-20261103-VF-RESUME-202 vigente; ningún servidor de
inferencia/prueba ajeno ni listener en puerto; modelo/runtime/harness con hashes
fijados; PNY GPU1 sin compute ajeno; ASUS cuarentenada; `3090-helper-verify-boot`
PASS; P2P lectura/escritura y `gpu_unlock` en ambas tarjetas PASS; MemAvailable ≥
32 GiB; presión de memoria avg10 <1%; volumen D con ≥10 GB; puertos 18414–18416
libres; 30 s de baseline. La carga de escritorio/Xorg se permite y se documenta.

Abortar la corrida propia ante servidor ajeno, compute ajeno en GPU1, pérdida de
GPU, error del server/harness, OOM, temperatura de GPU1 ≥85 °C o MemAvailable
<32 GiB durante cuatro muestras. Sólo cerrar procesos del test propio.

## Amendment Q205.04

Q205.01 attempt 1 failed before inference because the supervisor's global
process scan classified its own just-launched `llama-server` as foreign. The
runner now excludes only the server's owned process tree, uses `output_root`
from the active preregistration, and loads the append-only `*-prereg-amend01`
files. A synthetic process-tree regression smoke test passed; no GPU was used
for that check. Q205.01 retry is preregistered as attempt 2 in a fresh output
folder; B/C remain attempt 1 and serial. Amendment and amended preregistration
hashes are in `receipts/q205-04-runner-fix-amendment.json` and were read back
from the Google Sheet before any retry.
